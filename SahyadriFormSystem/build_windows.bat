@echo off
cd /d "%~dp0"
rem Builds dist\SahyadriFormSystem-Windows.zip for the customer.
rem Uses .venv if run_windows.bat created it. Add -WithOfflineSpeech to bundle the offline model.
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\build_windows.ps1" %*
pause
