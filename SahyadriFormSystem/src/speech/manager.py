"""Marathi speech-to-text.

Default engine is ONLINE (Google speech recognition, language mr-IN): fast
and accurate, needs an internet connection. Two online options:

* Free Google web speech service (default, no setup) via the
  SpeechRecognition package.
* Official Google Cloud Speech-to-Text, used automatically when a
  `google_cloud_api_key` is set in settings.json (more robust for heavy use).

An offline faster-whisper model is still supported as an optional fallback
(`speech_engine: "auto"` or `"offline"` in settings.json) if the model folder
and the `faster-whisper` package are installed (requirements-offline.txt).
"""
from __future__ import annotations

import base64
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from src.settings import Settings

GOOGLE_CLOUD_URL = 'https://speech.googleapis.com/v1/speech:recognize'

# Biases the offline model toward this form's vocabulary (offline engine only).
DOMAIN_PROMPT = (
    "जन्म तारीख, जन्म वेळ, जन्म स्थळ, जन्मराशी, नक्षत्र, जन्मनाव, लग्न, दशा, मंगळ, "
    "मेष, वृषभ, मिथुन, कर्क, सिंह, कन्या, तूळ, वृश्चिक, धनु, मकर, कुंभ, मीन, "
    "पत्रिकेतील दोष, उपाय, वर्ण, उंची, वजन, शारीरिक पात्रता, स्वभाव, शिक्षण, "
    "आर्थिक परिस्थिती, नोकरी, व्यवसाय, विवाह दिशा, विवाह प्रकार, वैवाहिक जीवन, "
    "विवाह तारीख, नोंदी."
)


class SpeechUnavailable(RuntimeError):
    """The online service could not be reached (no internet, timeout...)."""


class SpeechManager:
    def __init__(self, settings: Settings | None = None, model_path: str | None = None,
                 offline_only: bool = False):
        self.settings = settings or Settings()
        if offline_only:
            self.settings.speech_engine = 'offline'
        self.model_path = model_path or os.environ.get('SAHYADRI_WHISPER_MODEL', '')
        self.sample_rate = 16000
        self.blocksize = 1024
        # Recording: time to start speaking after the click, tolerance for a
        # natural pause mid-sentence, and a ceiling for long answers.
        self.max_seconds = 14.0
        self.start_timeout = 3.0
        self.silence_after_speech = 1.0
        self.min_speech_seconds = 0.20
        self._model = None

    # ------------------------------------------------------------------ public
    @property
    def engine_label(self) -> str:
        engine = self.settings.speech_engine
        if engine == 'offline':
            return 'offline speech'
        name = 'Google Cloud speech' if self.settings.google_cloud_api_key.strip() else 'Google speech'
        return f'online {name}' + (' (offline fallback)' if engine == 'auto' else '')

    def recognize(self) -> tuple[str, str]:
        recording = self._record()
        engine = self.settings.speech_engine
        if engine == 'offline':
            return self._offline(recording), 'offline'
        try:
            return self._online(recording), 'online'
        except SpeechUnavailable as exc:
            if engine == 'auto' and self.offline_available():
                return self._offline(recording), 'offline — no internet'
            raise RuntimeError(str(exc)) from exc

    def offline_available(self) -> bool:
        if not self.model_path or not (Path(self.model_path) / 'config.json').exists():
            return False
        try:
            import faster_whisper  # noqa: F401
        except Exception:
            return False
        return True

    # --------------------------------------------------------------- recording
    @staticmethod
    def _rms(block: np.ndarray) -> float:
        x = block.astype(np.float32)
        return float(np.sqrt(np.mean(np.square(x))) + 1e-9)

    def _record(self) -> np.ndarray:
        chunks: list[np.ndarray] = []
        # Short pre-roll so the first syllable (spoken while the level is still
        # rising past the threshold) is not clipped.
        preroll: list[np.ndarray] = []
        preroll_blocks = max(1, int(round(0.3 * self.sample_rate / self.blocksize)))
        speech_started = False
        speech_start = 0.0
        silence_started: float | None = None
        start = time.monotonic()
        ambient: list[float] = []
        try:
            # Imported here so a broken audio driver can never stop the app
            # from starting; it only affects the microphone button.
            import sounddevice as sd
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16',
                                blocksize=self.blocksize) as stream:
                while time.monotonic() - start < self.max_seconds:
                    block, _overflowed = stream.read(self.blocksize)
                    block = np.asarray(block).reshape(-1).copy()
                    level = self._rms(block)
                    elapsed = time.monotonic() - start
                    if not speech_started and elapsed < 0.5:
                        ambient.append(level)
                    baseline = float(np.median(ambient)) if ambient else 150.0
                    # Firmer threshold to START (ignores breathing/room noise),
                    # lower one to KEEP recording (keeps quiet word endings).
                    start_threshold = max(320.0, baseline * 2.2)
                    continue_threshold = max(220.0, baseline * 1.5)
                    is_speech = level >= (continue_threshold if speech_started else start_threshold)
                    if is_speech:
                        if not speech_started:
                            speech_started = True
                            speech_start = time.monotonic()
                            chunks.extend(preroll)
                        silence_started = None
                        chunks.append(block)
                    elif speech_started:
                        chunks.append(block)
                        if silence_started is None:
                            silence_started = time.monotonic()
                        elif (time.monotonic() - silence_started >= self.silence_after_speech
                              and time.monotonic() - speech_start >= self.min_speech_seconds):
                            break
                    else:
                        preroll.append(block)
                        if len(preroll) > preroll_blocks:
                            preroll.pop(0)
                        if elapsed >= self.start_timeout:
                            break
            if not speech_started or not chunks:
                raise RuntimeError(
                    'No speech detected. Click the microphone, wait a moment for it to '
                    'start listening, then speak clearly in Marathi.'
                )
            return np.concatenate(chunks).astype('int16')
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                'Microphone could not be opened. Check Windows microphone permissions and '
                'that a microphone is connected.\n\nDetails: ' + str(exc)
            ) from exc

    # ------------------------------------------------------------------ online
    def _online(self, recording: np.ndarray) -> str:
        raw = recording.astype('<i2').tobytes()      # 16-bit little-endian PCM, mono
        if self.settings.google_cloud_api_key.strip():
            return self._google_cloud(raw)
        return self._google_free(raw)

    def _google_free(self, raw: bytes) -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError(
                'Online speech recognition needs the "SpeechRecognition" package. '
                'Run: python -m pip install -r requirements.txt'
            ) from exc
        recognizer = sr.Recognizer()
        recognizer.operation_timeout = 12
        audio = sr.AudioData(raw, self.sample_rate, 2)
        try:
            text = recognizer.recognize_google(audio, language=self.settings.speech_language)
        except sr.UnknownValueError as exc:
            raise RuntimeError(
                'The speech was not clear enough to recognise. Please speak again, '
                'a little slower and closer to the microphone.'
            ) from exc
        except sr.RequestError as exc:
            raise SpeechUnavailable(
                'Online speech recognition could not be reached. Check the internet '
                f'connection and try again.\n\nDetails: {exc}\n\n'
                'If this keeps happening while the internet works, add a Google Cloud '
                'Speech-to-Text API key to settings.json (see SETUP_AND_DELIVERY.md).'
            ) from exc
        return str(text or '').strip()

    def _google_cloud(self, raw: bytes) -> str:
        body = {
            'config': {
                'encoding': 'LINEAR16',
                'sampleRateHertz': self.sample_rate,
                'languageCode': self.settings.speech_language,
            },
            'audio': {'content': base64.b64encode(raw).decode('ascii')},
        }
        url = GOOGLE_CLOUD_URL + '?key=' + urllib.parse.quote(self.settings.google_cloud_api_key.strip())
        request = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='ignore')[:400]
            raise RuntimeError(
                f'Google Cloud Speech-to-Text refused the request (HTTP {exc.code}). '
                f'Check the API key in settings.json.\n\n{detail}'
            ) from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            raise SpeechUnavailable(
                'Online speech recognition could not be reached. Check the internet '
                f'connection and try again.\n\nDetails: {exc}'
            ) from exc
        parts = [r['alternatives'][0].get('transcript', '').strip()
                 for r in payload.get('results', []) if r.get('alternatives')]
        text = ' '.join(p for p in parts if p).strip()
        if not text:
            raise RuntimeError(
                'The speech was not clear enough to recognise. Please speak again, '
                'a little slower and closer to the microphone.'
            )
        return text

    # ----------------------------------------------------------------- offline
    def _get_model(self):
        if self._model is not None:
            return self._model
        if not self.offline_available():
            raise RuntimeError(
                'Offline speech recognition is not installed on this computer.\n\n'
                'Set "speech_engine" to "online" in settings.json, or install the offline '
                'model as described in SETUP_AND_DELIVERY.md.'
            )
        from faster_whisper import WhisperModel
        self._model = WhisperModel(self.model_path, device='cpu', compute_type='int8')
        return self._model

    def _offline(self, recording: np.ndarray) -> str:
        model = self._get_model()
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = Path(f.name)
        try:
            import wave
            with wave.open(str(path), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(recording.astype('int16').tobytes())
            segments, _ = model.transcribe(
                str(path), language='mr', vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                beam_size=5, best_of=5, temperature=0,
                condition_on_previous_text=False,
                initial_prompt=DOMAIN_PROMPT,
            )
            return ' '.join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
        except Exception as exc:
            raise RuntimeError(f'Offline Marathi speech-to-text failed: {exc}') from exc
        finally:
            path.unlink(missing_ok=True)
