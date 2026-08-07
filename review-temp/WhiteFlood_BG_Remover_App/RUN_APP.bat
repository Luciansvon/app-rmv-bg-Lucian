@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python tidak ditemukan.
  echo Install Python 3.11+ dari python.org lalu centang "Add Python to PATH".
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
python whiteflood_app.py
pause
