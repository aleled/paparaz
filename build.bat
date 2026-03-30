@echo off
setlocal

echo =========================================
echo  PapaRaZ Build Script v0.8.0
echo =========================================
echo.

:: Ensure icon is up to date
echo [1/3] Generating icon...
python scripts\make_icon.py
if errorlevel 1 (echo WARNING: Icon generation failed, using existing & echo.)

:: Install/upgrade PyInstaller
echo [2/3] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)

:: Build
echo [3/3] Building executable...
pyinstaller paparaz.spec --clean --noconfirm
if errorlevel 1 (echo ERROR: Build failed & exit /b 1)

echo.
echo =========================================
echo  Build complete!
echo  Output: dist\PapaRaZ.exe
echo =========================================
echo.
pause
