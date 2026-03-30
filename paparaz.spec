# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PapaRaZ v0.8.0

block_cipher = None

a = Analysis(
    ['src/paparaz/__main__.py'],
    pathex=['src'],
    binaries=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PapaRaZ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    icon='assets/paparaz.ico',
    version='version_info.txt',
)
