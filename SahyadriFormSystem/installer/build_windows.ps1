# Build the customer package (Windows, Python 3.14.x).
#
#   .\installer\build_windows.ps1                      # online speech (default, recommended)
#   .\installer\build_windows.ps1 -WithOfflineSpeech   # also bundle the offline model (~500 MB)
#
param(
    [switch]$WithOfflineSpeech
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $projectRoot
Write-Host '========================================'
Write-Host ' Sahyadri Form System - Windows Build'
Write-Host ' Python 3.14.x / PyInstaller'
Write-Host '========================================'

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python was not found. Install Python 3.14.7 (or another Python 3.14.x release) and enable Add Python to PATH.'
}

$version = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')").Trim()
Write-Host "Python: $version"
$majorMinor = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($majorMinor -ne '3.14') {
    throw "This project is configured for Python 3.14.x. Detected Python $version."
}

Write-Host '[1/5] Upgrading packaging tools...'
python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }

Write-Host '[2/5] Installing dependencies...'
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installing requirements.txt failed.' }

$pyinstallerArgs = @(
    '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir',
    '--name', 'SahyadriFormSystem',
    '--add-data', 'templates;templates',
    '--add-data', 'fonts;fonts'
)

# Online speech: SpeechRecognition needs its bundled FLAC encoder and version.txt.
# (Its 38 MB of English offline models are deliberately NOT included.)
$srDir = (& python -c "import os, speech_recognition; print(os.path.dirname(speech_recognition.__file__))").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $srDir 'flac-win32.exe'))) {
    throw 'The SpeechRecognition package (with flac-win32.exe) was not found. Run: python -m pip install -r requirements.txt'
}
$pyinstallerArgs += @(
    '--add-binary', "$srDir\flac-win32.exe;speech_recognition",
    '--add-data', "$srDir\version.txt;speech_recognition",
    '--hidden-import', 'speech_recognition.recognizers.google'
)

if ($WithOfflineSpeech) {
    Write-Host '[STT] Including the optional offline speech model...' -ForegroundColor Yellow
    python -m pip install -r requirements-offline.txt
    if ($LASTEXITCODE -ne 0) { throw 'Installing requirements-offline.txt failed.' }
    $modelDir = Join-Path $projectRoot 'models\whisper-small'
    if (-not (Test-Path (Join-Path $modelDir 'config.json'))) {
        & (Join-Path $PSScriptRoot 'prepare_offline_stt.ps1')
        if ($LASTEXITCODE -ne 0) { throw 'Offline STT model preparation failed.' }
    }
    $pyinstallerArgs += @(
        '--add-data', 'models;models',
        '--collect-all', 'faster_whisper',
        '--collect-all', 'ctranslate2',
        '--collect-all', 'av'
    )
} else {
    # Keep the package small: never pull the offline engine in by accident.
    $pyinstallerArgs += @(
        '--exclude-module', 'faster_whisper', '--exclude-module', 'ctranslate2',
        '--exclude-module', 'av', '--exclude-module', 'onnxruntime'
    )
}

Write-Host '[3/5] Cleaning previous build...'
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

Write-Host '[4/5] Building with PyInstaller...'
$pyinstallerArgs += 'src/main.py'
& python @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

$exe = Join-Path $PWD 'dist\SahyadriFormSystem\SahyadriFormSystem.exe'
if (-not (Test-Path $exe)) {
    throw "Build finished but EXE was not found at $exe"
}

Write-Host '[5/5] Creating portable ZIP package...'
$zip = Join-Path $PWD 'dist\SahyadriFormSystem-Windows.zip'
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path 'dist\SahyadriFormSystem' -DestinationPath $zip -Force

Write-Host ''
Write-Host 'BUILD SUCCESSFUL' -ForegroundColor Green
Write-Host "EXE : $exe"
Write-Host "ZIP : $zip"
Write-Host ''
Write-Host 'The customer only needs to extract the ZIP and run SahyadriFormSystem.exe.'
Write-Host 'Speech-to-text needs an internet connection; records and PDFs work offline.'
