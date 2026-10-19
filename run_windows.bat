@echo off
setlocal
cd /d "%~dp0"
rem Runs the app from source. First run creates .venv and installs everything.
where python >nul 2>nul || goto :nopython
python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,14) else 1)" || goto :wrongpython
if exist .venv\Scripts\python.exe goto :run
echo Creating virtual environment and installing packages - first run only...
python -m venv .venv || goto :failed
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel || goto :failed
.venv\Scripts\python -m pip install -r requirements.txt || goto :failed
:run
.venv\Scripts\python -m src.main
goto :eof
:nopython
echo Python was not found. Install Python 3.14.7 from python.org and tick "Add python.exe to PATH".
pause
exit /b 1
:wrongpython
echo This project needs Python 3.14.x. Found:
python --version
pause
exit /b 1
:failed
echo Setup failed. See the messages above.
if exist .venv rmdir /s /q .venv
pause
exit /b 1
