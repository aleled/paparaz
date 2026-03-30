@echo off
setlocal

echo =========================================
echo  PapaRaZ Release Builder v0.9.0
echo =========================================
echo.

:: Step 1: Generate icon
echo [1/4] Generating icon...
python scripts\make_icon.py
if errorlevel 1 (echo WARNING: Icon generation failed, using existing & echo.)

:: Step 2: Build exe with PyInstaller
echo [2/4] Building executable...
pip install pyinstaller --quiet
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)
pyinstaller paparaz.spec --clean --noconfirm
if errorlevel 1 (echo ERROR: PyInstaller build failed & exit /b 1)
echo.

:: Check the exe exists
if not exist "dist\PapaRaZ.exe" (
    echo ERROR: dist\PapaRaZ.exe not found after build
    exit /b 1
)

:: Step 3: Find Inno Setup
echo [3/4] Locating Inno Setup...
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\iscc.exe
if exist "C:\Program Files\Inno Setup 6\iscc.exe"       set ISCC=C:\Program Files\Inno Setup 6\iscc.exe

if "%ISCC%"=="" (
    echo ERROR: Inno Setup 6 not found.
    echo Download from: https://jrsoftware.org/isdl.php
    exit /b 1
)
echo Found: %ISCC%
echo.

:: Step 4: Compile installer
echo [4/4] Building installer...
"%ISCC%" installer\paparaz_setup.iss
if errorlevel 1 (echo ERROR: Inno Setup compilation failed & exit /b 1)

echo.
echo =========================================
echo  Release complete!
echo  Exe:       dist\PapaRaZ.exe
echo  Installer: dist\PapaRaZ_Setup_0.9.0.exe
echo =========================================
echo.
pause
