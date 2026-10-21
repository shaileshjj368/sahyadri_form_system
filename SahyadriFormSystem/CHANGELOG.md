# Changelog

## v0.2.3 Handwritten PDF, precise मंगळ notation, online speech
- **मंगळ (M) notation rebuilt from the handwritten forms.** The previous version
  computed the superscript/subscript offsets in points but applied them to pixel
  coordinates, so the अंश sat almost on the baseline. Now: `M` right after the
  लग्न label; अंश raised at its top-right; कला smaller and a step higher; भाव at the
  M's foot.
- **लग्न value written between the printed slashes** (`8 / 5 / —`) instead of over
  them; a lone `-` is written as a pen dash.
- **Handwriting font:** values use Kalam (SIL Open Font License), a Devanagari
  ballpoint-style font, in blue ink, at the same sizes as before. The conjuncts
  त्न, ग्न, स्न are forced to their usual half-letter forms (Kalam stacks
  them so रत्न looks like "रन्न").
- **More natural placement:** values sit on the ruled lines; नाव and सूचना 6 hang
  from their printed lines; the Date year follows the printed `/20` (`/2026`); the
  weight ends just before `Kgs`; पत्रिकेतील दोष, उपाय, शारीरिक पात्रता and विवाह दिशा
  wrap from line to line (typed line breaks still start a new line). दोष uses its
  four rows and उपाय starts on its label row, as in the handwritten forms.
- New `src/pdf/layout.py` holds all positions (template points) and is shared by the
  Qt renderer and a Pillow preview renderer, so the preview checks the exact layout
  the app prints. `src/pdf/template_fields.py` removed.
- **Online speech-to-text (default):** Google speech recognition (`mr-IN`) via
  SpeechRecognition; optional Google Cloud Speech-to-Text API key in
  `settings.json`. Offline faster-whisper is now optional (`requirements-offline.txt`,
  `build_windows.ps1 -WithOfflineSpeech`), which also makes the package ~500 MB
  smaller. The audio library now loads only when the microphone is used, so a
  driver problem can't stop the app from starting.
- Spoken राशी/नक्षत्र now match the nearest option (e.g. "मृग" → मृगशिरा).
- `settings.json` beside the app: handwriting on/off, pen weight, ink colour,
  speech engine, Cloud key.
- Re-applied the v0.2.1 मंगळ input rules that were missing from v0.2.2: अंश 0-29,
  कला 0-59 (optional), भाव 1-12.
- `run_windows.bat` sets up `.venv` on first run; new `build_windows.bat`.
- Removed the unused `indic-transliteration` dependency.
- Tests: layout rules, speech request/response handling, settings; on Windows,
  Qt-vs-layout measurement checks.

## v0.2.2 Speech accuracy, transliteration correctness, Manglik fine-tune
- **Speech-to-text accuracy overhaul** (`src/speech/manager.py`):
  - Switched the offline model from `faster-whisper-base` to
    `faster-whisper-small`, which recognizes Marathi noticeably more
    accurately while still running quickly on CPU for a short clip.
    `installer/prepare_offline_stt.ps1`, `build_windows.ps1` and
    `src/ui/main_window.py` were all updated to look for/download
    `models\whisper-small` (older `whisper-base` folders still work as a
    fallback so nothing breaks if you've already prepared one).
  - Decoding now uses `beam_size=5, best_of=5` instead of greedy
    (`beam_size=1`) decoding, and passes a Marathi `initial_prompt` built
    from this form's own field/राशी/नक्षत्र vocabulary, which measurably
    improves recognition of the words this app is actually used for.
  - Recording was re-tuned: more realistic time to start speaking after
    clicking the microphone (`start_timeout` 1.5s → 3.0s), natural
    mid-sentence pauses no longer end the recording early
    (`silence_after_speech` 0.55s → 1.0s), a longer capture ceiling for
    longer answers (`max_seconds` 7s → 14s), a short pre-roll buffer so the
    first syllable is no longer clipped, and a lower "keep listening"
    threshold once speech has started so quieter trailing sounds aren't
    mistaken for silence.
  - `installer/prepare_offline_stt.ps1` now verifies the downloaded model
    actually loads and runs a real test transcription (previously it only
    checked that `config.json` existed), and documents the Python
    3.14/ctranslate2-wheel fallback if no prebuilt wheel exists yet for a
    very new Python release.
- **Fixed Marathi transliteration for multi-sentence / mixed text**
  (`src/transliteration/marathi.py`):
  - Previously, converting text with commas or full stops only transliterated
    up to the FIRST one — the code read only the first "chunk" Google's Input
    Tools API returns and silently dropped everything after it. The
    converter now walks the whole string token by token and converts every
    Latin word in it, regardless of punctuation.
  - Previously, if the text already contained ANY Devanagari character
    anywhere (even one Marathi word at the start of a sentence), the entire
    conversion was skipped and the rest of the sentence was never
    converted. Devanagari words, punctuation, digits and whitespace are now
    each preserved as-is while every Latin word is independently converted,
    so mixed Marathi/English text converts correctly throughout.
  - Added regression tests for both bugs in `tests/test_transliteration.py`.
- **Manglik (मंगळ) लग्न position fine-tune** (`src/pdf/renderer.py`): the
  degree superscript on "M" (मंगळ अंश/कला) is now drawn higher, sitting at
  the top of the M as in the handwritten reference forms, instead of near
  its middle. The bhava (भाव) subscript at the foot of the M — already
  correctly placed — is unchanged.

## v0.2.0 PDF alignment refinement
- Increased entered-value font size slightly above the printed field labels.
- Rendered entered values in bold using a bundled Noto Sans Devanagari Bold font.
- Re-mapped the form fields from the original 594x936pt template geometry so values start inside the actual blank value cells.
- Corrected the vertical positions of the large sections and lower table rows.
- Kept the existing v0.2.0 UI, SQLite workflow, Save Form / Generate PDF buttons, search, transliteration and speech behavior unchanged.

## v0.2.0 PDF micro-alignment refinement
- Corrected only the fields identified by the client's purple circles in the latest output PDF.
- Repositioned name, वर्ण, स्वभाव, शिक्षण, आर्थिक परिस्थिती, नोकरी/व्यवसाय, विवाह प्रकार, वैवाहिक जीवन and विवाह तारीख to the highlighted writing areas.
- Fine-tuned the top Date and Lagna date-component boxes against the printed `/` and `/20` separators.
- No UI or workflow changes.

## v0.2.0 date/period refinement
- Lagna and marriage-period dates now render four-digit years.
- Improved lagna date box positioning and sizing for 2030-style years.
- `विवाह योग्य कालावधी` accepts two dates followed by optional text; the trailing sentence is printed on the highlighted line below row 13.
- No database schema change required.

## v0.2.0 client refinements - Lagna/Manglik and printed-20 date handling
- Kept `लग्न` as an independent editable field; it may contain text or numbers.
- Added separate `मंगळ` / `मंगळ नाही` selection.
- When `मंगळ` is selected, added numeric `मंगळ अंश`, `मंगळ कला`, and `मंगळ भाव` inputs and render them as `M 09 / 00 / 4` in the calibrated Lagna area.
- When `मंगळ नाही` is selected, no M/value overlay is rendered.
- Fixed the top Date template: for `26/09/2023`, only `26`, `09`, and `23` are overlaid because the template already prints `/20`.
- Fixed frozen/PyInstaller resource lookup so bundled templates, fonts, and offline Whisper models are read from the packaged resource directory while SQLite/PDF output remains beside the EXE.
- Improved offline speech-model diagnostics.
