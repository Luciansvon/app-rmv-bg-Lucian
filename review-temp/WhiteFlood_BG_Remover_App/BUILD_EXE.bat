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
python -m pip install pyinstaller>=6.0

echo.
echo Membuat EXE... (ini bisa butuh waktu beberapa menit)
echo.

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --icon "logo.ico" ^
  --add-data "logo.ico;." ^
  --add-data "logo.png;." ^
  --collect-all customtkinter ^
  --hidden-import psutil ^
  --name "WhiteFlood_BG_Remover" ^
  whiteflood_app.py

echo.
echo ========================================
echo EXE selesai dibuat:
echo %CD%\dist\WhiteFlood_BG_Remover.exe
echo ========================================
echo.
echo CATATAN: File EXE besar (~300-500 MB) karena
echo berisi AI model dan semua library.
echo Ini normal, bukan virus.
echo ========================================
pause
