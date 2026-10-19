# Setup, Build & Delivery — Sahyadri Form System v0.2.3

Everything below is on **Windows** with **Python 3.14.7**.

## 1. Install Python (once)

Install Python 3.14.7 from python.org and tick **"Add python.exe to PATH"** in the
installer. Check in a new Command Prompt: `python --version` → `Python 3.14.7`.

## 2. Run the app from source (your machine)

Extract this zip, open the `SahyadriFormSystem` folder and double-click
**`run_windows.bat`**.

The first run creates a `.venv` folder and installs the packages (needs internet,
a few minutes). Later runs start straight away.

Prefer the command line? Same thing:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m pip install -r requirements.txt
python -m src.main
```

## 3. Check it before building

- [ ] **PDF**: open the form, fill one record with मंगळ (e.g. लग्न `8/5/-`, अंश `15`,
      कला `00`, भाव `7`) and one with मंगळ नाही, then **Generate PDF**. Compare the
      लग्न cell with your handwritten forms.
- [ ] **Speech** (needs internet): click 🎤 on a few fields and speak Marathi.
- [ ] **अ conversion**: type `mumbai la ja, ani parat ye.` and a sentence that starts
      with a Marathi word; both should convert completely.
- [ ] **Tests** (optional, recommended once):
      ```powershell
      .\.venv\Scripts\python -m pip install -r requirements-dev.txt
      .\.venv\Scripts\python -m pytest
      ```
      On Windows these include checks that run the real Qt renderer and confirm its
      measurements match the layout.
- [ ] Sample PDFs without the GUI: `.\.venv\Scripts\python -m tools.preview_pdf`
      writes `generated_pdfs\preview_*.pdf` from the four handwritten reference forms.

## 4. Build the customer package

Double-click **`build_windows.bat`** (or run `.\installer\build_windows.ps1`).

Result:

```
dist\SahyadriFormSystem-Windows.zip      <- give this to the customer
dist\SahyadriFormSystem\SahyadriFormSystem.exe
```

Before sending it, extract the zip into a fresh folder, run the EXE, make one PDF and
try the microphone once.

## 5. Customer installation

1. Extract `SahyadriFormSystem-Windows.zip` anywhere (e.g. `C:\Sahyadri`).
2. Double-click `SahyadriFormSystem.exe`.

No Python or setup needed. Records (`data\sahyadri.db`), PDFs (`generated_pdfs\`)
and `settings.json` are created next to the EXE. Records and PDFs work without
internet; the microphone needs internet.

If Windows asks, allow microphone access: **Settings → Privacy & security →
Microphone → Let desktop apps access your microphone**.

## Speech-to-text options

- **Default (no setup):** Google's free speech service, Marathi (`mr-IN`). Fast and
  accurate, but it is Google's public service with no guarantee; Google can
  rate-limit or change it.
- **More robust (recommended for daily business use):** a Google Cloud
  Speech-to-Text API key. Create a Google Cloud project, enable *Cloud
  Speech-to-Text API*, create an API key (restrict it to that API), and paste it into
  `settings.json` next to the EXE:
  ```json
  "google_cloud_api_key": "AIza...your key..."
  ```
  Google bills per minute of audio after a monthly free allowance; short form
  answers cost very little. Restart the app after editing the file.
- **Offline (optional, less accurate):** see `models/README.md`.

## Handwriting look

Edit `settings.json` next to the EXE (then restart the app):

- `"handwriting_weight": "bold"` for a thicker pen
- `"ink_color": "#1c3096"` pen colour (e.g. `"#10205a"` for darker blue)
- `"handwriting": false` to go back to the previous printed style
