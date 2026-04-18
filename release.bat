@echo off
setlocal EnableDelayedExpansion

:: ── Read version from pyproject.toml so it's always in sync ──────────────────
for /f "tokens=2 delims== " %%V in ('findstr /r "^version" pyproject.toml') do (
    set RAW=%%V
)
:: Strip surrounding quotes if any
set VERSION=%RAW:"=%
set VERSION=%VERSION: =%
if "%VERSION%"=="" (
    echo ERROR: Could not read version from pyproject.toml
    exit /b 1
)

echo =========================================
echo  PapaRaZ Release Builder v%VERSION%
echo =========================================
echo.

:: Step 1: Clean old artefacts
echo [1/6] Cleaning previous build...
if exist dist\PapaRaZ.exe del /f /q dist\PapaRaZ.exe
if exist dist\PapaRaZ rmdir /s /q dist\PapaRaZ
if exist build rmdir /s /q build
echo Done.
echo.

:: Step 2: Generate assets
echo [2/6] Generating assets...
python scripts\make_icon.py
if errorlevel 1 echo WARNING: Icon generation failed, using existing
python scripts\make_installer_images.py %VERSION%
if errorlevel 1 echo WARNING: Installer image generation failed, using existing
echo.

:: Step 3: Build exe with PyInstaller
echo [3/6] Building executable...
pip install pyinstaller --quiet
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)
pyinstaller paparaz.spec --clean --noconfirm
if errorlevel 1 (echo ERROR: PyInstaller build failed & exit /b 1)
echo.

if not exist "dist\PapaRaZ\PapaRaZ.exe" (
    echo ERROR: dist\PapaRaZ\PapaRaZ.exe not found after build
    exit /b 1
)

:: Step 4: Find Inno Setup
echo [4/6] Locating Inno Setup...
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
if exist "C:\Program Files\Inno Setup 6\iscc.exe"       set "ISCC=C:\Program Files\Inno Setup 6\iscc.exe"

if "%ISCC%"=="" (
    echo ERROR: Inno Setup 6 not found.
    echo Download from: https://jrsoftware.org/isdl.php
    exit /b 1
)
echo Found: %ISCC%
echo.

:: Step 5: Compile installer
echo [5/6] Building installer...
"%ISCC%" installer\paparaz_setup.iss
if errorlevel 1 (echo ERROR: Inno Setup compilation failed & exit /b 1)

set INSTALLER=dist\PapaRaZ_Setup_%VERSION%.exe
if not exist "%INSTALLER%" (
    echo ERROR: Expected installer not found: %INSTALLER%
    exit /b 1
)
echo.

:: Step 6: Upload to GitHub release (requires GH_TOKEN in env or .env)
echo [6/6] Uploading to GitHub release v%VERSION%...

:: Load .env if GH_TOKEN not already set
if "%GH_TOKEN%"=="" (
    if exist .env (
        for /f "tokens=1,2 delims==" %%A in (.env) do (
            if "%%A"=="GH_TOKEN" set GH_TOKEN=%%B
        )
    )
)

:: Find gh CLI
set GH=
if exist "C:\Program Files\GitHub CLI\gh.exe" set "GH=C:\Program Files\GitHub CLI\gh.exe"
if exist "C:\Program Files (x86)\GitHub CLI\gh.exe" set "GH=C:\Program Files (x86)\GitHub CLI\gh.exe"

if "%GH%"=="" (
    echo WARNING: GitHub CLI not found — skipping upload.
    echo Install from: https://cli.github.com
    goto done
)

if "%GH_TOKEN%"=="" (
    echo WARNING: GH_TOKEN not set — skipping upload.
    echo Add GH_TOKEN=your_token to .env or set it in environment.
    goto done
)

:: Create or update the release and upload installer
set TAG=v%VERSION%
"%GH%" release view %TAG% --repo aleled/paparaz >nul 2>&1
if errorlevel 1 (
    echo   Creating release %TAG%...
    "%GH%" release create %TAG% "%INSTALLER%" --repo aleled/paparaz --title "v%VERSION%" --generate-notes
) else (
    echo   Uploading %INSTALLER% to existing release %TAG%...
    "%GH%" release upload %TAG% "%INSTALLER%" --repo aleled/paparaz --clobber
)
if errorlevel 1 (
    echo ERROR: GitHub upload failed
    exit /b 1
)
echo   Upload complete.

:done
echo.
echo =========================================
echo  Release complete!
echo  Exe:       dist\PapaRaZ.exe
echo  Installer: %INSTALLER%
echo  Release:   https://github.com/aleled/paparaz/releases/tag/v%VERSION%
echo =========================================
echo.
pause
