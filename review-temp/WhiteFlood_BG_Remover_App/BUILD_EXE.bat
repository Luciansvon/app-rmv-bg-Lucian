@echo off
cd /d "%~dp0"

echo ========================================
echo   WhiteFlood BG Remover - Build EXE
echo   Built by Bima Chakti
echo ========================================
echo.

:: Cek Python tersedia
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python tidak ditemukan.
  echo Install Python 3.11+ dari python.org lalu centang "Add Python to PATH".
  pause
  exit /b 1
)

:: Install dependencies
echo [1/3] Menginstall dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Gagal menginstall dependencies dari requirements.txt.
  echo Pastikan koneksi internet stabil dan pip berfungsi.
  pause
  exit /b 1
)

:: Install PyInstaller
echo.
echo [2/3] Menginstall PyInstaller...
python -m pip install "pyinstaller>=6.0"
if errorlevel 1 (
  echo.
  echo [ERROR] Gagal menginstall PyInstaller.
  pause
  exit /b 1
)

:: Bersihkan cache build lama tanpa menghapus asset lain di folder dist
if exist build rmdir /s /q build
if exist WhiteFlood_BG_Remover.spec del /f /q WhiteFlood_BG_Remover.spec

:: Build EXE via build_exe.py
echo.
echo [3/3] Membuat EXE... (ini bisa butuh waktu beberapa menit)
echo.
python build_exe.py

if errorlevel 1 (
  echo.
  echo [ERROR] PyInstaller gagal membuat EXE.
  echo Baca error di atas untuk detail penyebabnya.
  pause
  exit /b 1
)

pause
