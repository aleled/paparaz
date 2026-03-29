@echo off
echo Building PapaRaZ...
pip install pyinstaller
pyinstaller paparaz.spec --clean
echo.
echo Build complete! Output: dist\PapaRaZ.exe
pause
