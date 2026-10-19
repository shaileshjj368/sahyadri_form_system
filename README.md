# Sahyadri Form System

A Windows desktop app that digitizes the handwritten Marathi astrology form **"Shri Sahyadri"**. Enter a record once, save it, and print it onto the original form template as a PDF that looks filled in by hand.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20(64--bit)-blue)
![Python](https://img.shields.io/badge/python-3.14-blue)
![GUI](https://img.shields.io/badge/GUI-PySide6-green)
![Version](https://img.shields.io/badge/version-0.2.4-orange)

## Features

- **Record management:** enter, save, search and edit records (local SQLite database).
- **Exact PDF output:** values are placed on the untouched vector form template (A4), with every field positioned from measurements of the original form.
- **Handwritten look:** text is written in the Kalam Devanagari handwriting font, in ballpoint blue, with tiny natural per-word baseline variation. It can be switched off in settings.
- **मंगळ (Manglik) notation:** for a Manglik form, the लग्न field gets an `M` with the अंश (degree) raised at its top-right, the कला (minute) smaller and higher, and the भाव (house) at its foot, as in the handwritten forms. Non-मंगळ forms get no M.
- **Voice input (Marathi):** online speech-to-text using Google (`mr-IN`). An optional Google Cloud Speech-to-Text API key and an optional offline Whisper fallback are supported.
- **English → Marathi button (अ):** converts whole multi-sentence text, including mixed Marathi/English, word by word, with an offline fallback.
- **Smart matching:** spoken राशी and नक्षत्र are matched to the nearest valid option (for example "मृग" becomes मृगशिरा).
- **Easy delivery:** builds to a self-contained folder, a zip, and an optional Setup.exe. The client does not need Python.

## What needs internet

| Feature | Internet |
|---|---|
| Entering, saving and searching records | Not needed |
| Generating PDFs | Not needed |
| 🎤 Speech-to-text | **Needed** |
| **अ** English-to-Marathi conversion | Better online, simple offline fallback |

## Quick start (developers)

Requirements: Windows 10 1809 or newer (64-bit) and Python 3.14.

```bat
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
run_windows.bat
```

`run_windows.bat` creates a `.venv` on first run, installs `requirements.txt` and starts the app.

Manual setup:

```bat
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

Optional offline speech (adds roughly 500 MB): `pip install -r requirements-offline.txt`

## Building for the client

1. Install [Inno Setup](https://jrsoftware.org/isdl.php) 6.3 or newer (optional, only for the Setup.exe).
2. Double-click `build_windows.bat` (or run `installer\build_windows.ps1`).
3. Deliver `dist\SahyadriFormSystem-Setup.exe`, or the zip.

Build options:

| Option | Effect |
|---|---|
| `-WithOfflineSpeech` | Bundles the offline Whisper model (larger package) |
| `-Console` | Debug build with a console window |

The build finishes with an automatic **self-test of the finished EXE with Python hidden from PATH**. It stops if the package would only work where Python is installed.

The Setup.exe installs per user (no admin rights), adds desktop and Start-menu shortcuts, and never deletes records on upgrade or uninstall.

See [SETUP_AND_DELIVERY.md](SETUP_AND_DELIVERY.md) for full steps and the troubleshooting table.

## Troubleshooting

- If the app does not open, check `error.log` in the app folder. Startup errors are logged there and also shown in a message box.
- Run `Check_Installation.bat` (or `SahyadriFormSystem.exe --selftest`) to test files, the data folder, PDF generation, the speech encoder and the microphone. The report is saved as `selftest-report.txt`.
- Common causes on a clean PC:
  - running the app from inside the zip without extracting it
  - copying only the `.exe` without the `_internal` folder
  - antivirus quarantining the EXE
  - a missing Microsoft C++ runtime (install `vc_redist.x64.exe`)
  - Windows older than 10 1809, or 32-bit Windows

## Settings

`settings.json` is created beside the app on first run.

| Key | Default | Meaning |
|---|---|---|
| `handwriting` | `true` | `false` gives the printed (Noto Sans) look |
| `handwriting_weight` | `"regular"` | `"bold"` for a thicker pen |
| `ink_color` | `"#1c3096"` | Pen colour |
| `handwriting_wobble` | `true` | Small natural baseline variation per word |
| `speech_engine` | `"online"` | `"auto"` falls back to offline; `"offline"` |
| `speech_language` | `"mr-IN"` | Google language code |
| `google_cloud_api_key` | `""` | Optional Google Cloud Speech-to-Text key |

If the app folder is read-only (for example `C:\Program Files`), data is saved to `Documents\SahyadriFormSystem` instead.

## Project structure

```
src/
  main.py            entry point, error log, --selftest
  selftest.py        installation check
  settings.py        settings.json handling
  pdf/
    layout.py        all field geometry, in template points
    renderer.py      Qt renderer (app) and Pillow renderer (preview)
  speech/            online/offline speech-to-text
  transliteration/   English to Marathi conversion
  ui/                PySide6 main window
templates/           Shri_Sahyadri.pdf (blank form)
fonts/               Kalam, Noto Sans Devanagari
installer/           PowerShell build script, Inno Setup script, client README
tools/preview_pdf.py render sample forms without the GUI
tests/               pytest suite
docs/field_map.md    field positions reference
```

## How the PDF is made

`layout.py` converts a record into a list of text operations (text, x, baseline, size, font) in the template's own coordinate system (594 × 936 pt, placed on A4). Both the Qt renderer used by the app and the Pillow renderer used for previews draw that same layout, so layout changes can be checked without the GUI. The text is drawn as an overlay and merged onto the original vector template with `pypdf`.

## Development

```bat
pip install -r requirements-dev.txt
pytest
python -m tools.preview_pdf          :: renders sample forms to generated_pdfs\preview_*.pdf
python -m tools.preview_pdf --pil    :: same, using Pillow instead of Qt
```

## Tech stack

PySide6 (Qt), SQLite, pypdf, reportlab, Pillow, SpeechRecognition, sounddevice, PyInstaller, Inno Setup. Optional: faster-whisper.

## Privacy and data

Records contain personal data and are stored locally in `data\sahyadri.db`. Do not commit the `data/`, `generated_pdfs/`, `settings.json`, `error.log` or `.venv/` folders. A suggested `.gitignore`:

```
.venv/
data/
generated_pdfs/
settings.json
error.log
selftest-report.txt
build/
dist/
__pycache__/
*.pyc
```

Online speech-to-text sends the recorded audio to Google. Tell users before enabling it.

## License

Add your license here. The bundled **Kalam** font is licensed under the SIL Open Font License (see `fonts/Kalam-OFL.txt`). Noto Sans Devanagari is also OFL-licensed.

The form template `Shri_Sahyadri.pdf` belongs to the client. Confirm you may publish it before making the repository public.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
