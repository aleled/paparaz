@echo off
setlocal EnableDelayedExpansion

:: Read version from pyproject.toml
for /f "tokens=2 delims== " %%V in ('findstr /r "^version" pyproject.toml') do set RAW=%%V
set VERSION=%RAW:"=%
set VERSION=%VERSION: =%

echo =========================================
echo  PapaRaZ Build Script v%VERSION%
echo =========================================
echo.

:: Wipe previous build artefacts so nothing stale carries over
echo [1/4] Cleaning previous build...
if exist dist\PapaRaZ.exe del /f /q dist\PapaRaZ.exe
if exist build rmdir /s /q build
echo Done.
echo.

:: Ensure icon is up to date
echo [2/4] Generating icon...
python scripts\make_icon.py
if errorlevel 1 (echo WARNING: Icon generation failed, using existing & echo.)

:: Install/upgrade PyInstaller
echo [3/4] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)

:: Build
echo [4/4] Building executable...
pyinstaller paparaz.spec --clean --noconfirm
if errorlevel 1 (echo ERROR: Build failed & exit /b 1)

echo.
echo =========================================
echo  Build complete!
echo  Output: dist\PapaRaZ.exe
echo =========================================
echo.
:: Only pause when run interactively (double-clicked), not when called from scripts.
:: Check if stdin is a console (interactive) vs redirected (script/CI).
set "INTERACTIVE=0"
for /f "tokens=2" %%I in ('mode con 2^>nul ^| findstr "Columns"') do set "INTERACTIVE=1"
if "%INTERACTIVE%"=="1" pause
