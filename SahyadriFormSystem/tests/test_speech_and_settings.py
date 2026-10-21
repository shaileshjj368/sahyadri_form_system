"""Speech and settings tests that need no microphone and no internet."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import pytest

import src.speech.manager as M
from src.settings import Settings


def _serve(handler):
    srv = HTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_settings_defaults_and_bad_values(tmp_path):
    path = tmp_path / 'settings.json'
    s = Settings.load(path)                     # creates the file with defaults
    assert path.exists() and s.speech_engine == 'online' and s.handwriting
    path.write_text(json.dumps({'speech_engine': 'nonsense', 'ink_color': '#102030',
                                'handwriting_weight': 'bold', 'unknown': 1}), encoding='utf-8')
    s = Settings.load(path)
    assert s.speech_engine == 'online'          # invalid value falls back
    assert s.ink_rgb() == (16, 32, 48)
    assert s.handwriting_weight == 'bold'


def test_google_cloud_request_and_parsing(monkeypatch):
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            seen.update(config=body['config'], n=len(base64.b64decode(body['audio']['content'])),
                        path=self.path)
            out = json.dumps({'results': [{'alternatives': [{'transcript': 'जोशी शैलेश'}]}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *args):
            pass

    srv = _serve(Handler)
    monkeypatch.setattr(M, 'GOOGLE_CLOUD_URL', f'http://127.0.0.1:{srv.server_port}/v1/speech:recognize')
    settings = Settings(google_cloud_api_key='KEY')
    audio = np.zeros(16000, dtype='int16')
    assert M.SpeechManager(settings)._online(audio) == 'जोशी शैलेश'
    assert seen['config'] == {'encoding': 'LINEAR16', 'sampleRateHertz': 16000, 'languageCode': 'mr-IN'}
    assert seen['n'] == 32000 and seen['path'].endswith('key=KEY')
    srv.shutdown()


def test_offline_engine_without_model_gives_clear_error():
    sm = M.SpeechManager(Settings(speech_engine='offline'))
    with pytest.raises(RuntimeError, match='Offline speech recognition is not installed'):
        sm._offline(np.zeros(16000, dtype='int16'))


def test_no_internet_is_reported_clearly(monkeypatch):
    sm = M.SpeechManager(Settings(google_cloud_api_key='KEY'))
    monkeypatch.setattr(M, 'GOOGLE_CLOUD_URL', 'http://127.0.0.1:9/nothing-listens-here')
    with pytest.raises(M.SpeechUnavailable, match='internet'):
        sm._online(np.zeros(16000, dtype='int16'))
