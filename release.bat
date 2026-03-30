@echo off
setlocal

echo =========================================
echo  PapaRaZ Release Builder v0.9.1
echo =========================================
echo.

:: Step 1: Clean old artefacts
echo [1/5] Cleaning previous build...
if exist dist\PapaRaZ.exe del /f /q dist\PapaRaZ.exe
if exist build rmdir /s /q build
echo Done.
echo.

:: Step 2: Generate icon + installer images
echo [2/5] Generating assets...
python scripts\make_icon.py
if errorlevel 1 (echo WARNING: Icon generation failed, using existing & echo.)
python scripts\make_installer_images.py 0.9.1
if errorlevel 1 (echo WARNING: Installer image generation failed, using existing & echo.)

:: Step 3: Build exe with PyInstaller
echo [3/5] Building executable...
pip install pyinstaller --quiet
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)
pyinstaller paparaz.spec --clean --noconfirm
if errorlevel 1 (echo ERROR: PyInstaller build failed & exit /b 1)
echo.

if not exist "dist\PapaRaZ.exe" (
    echo ERROR: dist\PapaRaZ.exe not found after build
    exit /b 1
)

:: Step 4: Find Inno Setup
echo [4/5] Locating Inno Setup...
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

:: Step 5: Compile installer
echo [5/5] Building installer...
"%ISCC%" installer\paparaz_setup.iss
if errorlevel 1 (echo ERROR: Inno Setup compilation failed & exit /b 1)

echo.
echo =========================================
echo  Release complete!
echo  Exe:       dist\PapaRaZ.exe
echo  Installer: dist\PapaRaZ_Setup_0.9.1.exe
echo =========================================
echo.
pause
