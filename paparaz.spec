# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PapaRaZ — onedir mode
#
# onedir is used instead of onefile because python313.dll (Microsoft Store
# Python) cannot be loaded via LoadLibrary when extracted to a _MEI temp
# directory.  Installing as a folder lets Windows find all DLL dependencies
# from the application directory directly.

block_cipher = None

a = Analysis(
    ['src/paparaz/__main__.py'],
    pathex=['src'],
    binaries=[
        # python313.dll lives inside the protected WindowsApps directory on
        # Microsoft Store Python installs — bundle it explicitly.
        ('python313.dll', '.'),
    ],
    datas=[
        ('assets/paparaz.ico', 'assets'),
    ],
    hiddenimports=[
        # PySide6 SVG support
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        # winrt OCR packages
        'winrt.windows.media.ocr',
        'winrt.windows.graphics.imaging',
        'winrt.windows.storage',
        'winrt.windows.storage.streams',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt.windows.globalization',
        # Windows utilities
        'winreg',
        'ctypes',
        'ctypes.wintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],                    # empty in onedir — files go into COLLECT below
    exclude_binaries=True,
    name='PapaRaZ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    icon='assets/paparaz.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PapaRaZ',
)
