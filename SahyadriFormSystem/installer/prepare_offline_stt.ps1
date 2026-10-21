$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $projectRoot
Write-Host 'OPTIONAL: preparing the offline speech model (only needed for build_windows.ps1 -WithOfflineSpeech).'
Write-Host 'This preparation step requires internet ONCE on the development/build computer.'

$majorMinor = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($majorMinor -ne '3.14') {
    throw "This project is configured for Python 3.14.x. Detected Python $majorMinor."
}

Write-Host '[0/4] Installing the optional offline speech packages...'
python -m pip install -r requirements-offline.txt
Write-Host '[1/4] Checking that faster-whisper/ctranslate2 import correctly on this Python...'
try {
    python -c "import ctranslate2, faster_whisper; print('ctranslate2', ctranslate2.__version__); print('faster_whisper', faster_whisper.__version__)"
    if ($LASTEXITCODE -ne 0) { throw 'import failed' }
} catch {
    throw @"
faster-whisper / ctranslate2 could not be imported on this Python version.
ctranslate2 ships pre-built binary wheels only for specific Python versions, and a
very new Python release (such as 3.14) may not yet have one available on PyPI.

Fix options:
  1) Run 'python -m pip install --upgrade faster-whisper ctranslate2' again in case a
     new wheel was published, then re-run this script.
  2) If no wheel exists yet for Python 3.14, create the BUILD-ONLY virtual environment
     with Python 3.12 or 3.13 instead just for this script (the downloaded model files
     are plain data and don't care which Python downloaded them). The customer-facing
     EXE built in step 3 still runs standalone via PyInstaller.
"@
}

# 'small' gives meaningfully better Marathi accuracy than 'base' while still
# running comfortably on CPU (int8) for the short clips this app records.
Write-Host '[2/4] Downloading Systran/faster-whisper-small (CTranslate2 format, multilingual incl. Marathi)...'
python -m pip install --upgrade huggingface_hub
New-Item -ItemType Directory -Force -Path 'models\whisper-small' | Out-Null
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-small', local_dir='models/whisper-small')"
if (-not (Test-Path 'models\whisper-small\config.json')) { throw 'Model download completed but config.json was not found.' }

Write-Host '[3/4] Verifying the downloaded model actually loads and transcribes offline...'
python -c @"
import numpy as np
from faster_whisper import WhisperModel
model = WhisperModel('models/whisper-small', device='cpu', compute_type='int8')
silence = np.zeros(16000, dtype=np.float32)
segments, info = model.transcribe(silence, language='mr', vad_filter=False)
list(segments)
print('Model loaded and ran a test transcription successfully. Detected language:', info.language)
"@
if ($LASTEXITCODE -ne 0) { throw 'The model was downloaded but failed to load/run with faster-whisper. See the error above.' }

Write-Host '[4/4] Offline STT model prepared and verified in models\whisper-small' -ForegroundColor Green
Write-Host ''
Write-Host 'Tip: if recognition still needs to be more accurate for your users, you can' -ForegroundColor Yellow
Write-Host 'switch to the larger "medium" model instead: edit this script (and' -ForegroundColor Yellow
Write-Host 'src/ui/main_window.py) to use "Systran/faster-whisper-medium" / "whisper-medium".' -ForegroundColor Yellow
Write-Host 'It is slower per click but more accurate; try "small" first.' -ForegroundColor Yellow
