# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Watermark App (GTK version)
Author: antoine@ginies.org

Usage:
    pyinstaller watermark_app_gtk.spec

Build modes:
    - Edit ONEFILE variable below to switch between onefile and folder mode
    - Onefile: Single executable (slower startup, easier distribution)
    - Folder: Multiple files (faster startup, larger distribution)
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ============================================================================
# CONFIGURATION
# ============================================================================

# Build mode: True for single executable, False for folder with multiple files
ONEFILE = True

# Enable UPX compression (set to False if antivirus issues occur)
USE_UPX = True

# Application metadata
APP_NAME = 'WatermarkApp_GTK'
APP_VERSION = '5.0.0.0'
APP_DESCRIPTION = 'Watermark application for images and PDFs'
APP_COPYRIGHT = 'Copyright (C) 2025 Antoine Ginies'
APP_AUTHOR = 'Antoine Ginies'

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(SPEC))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, 'watermark_app_gtk.py')
LOCALE_DIR = os.path.join(SCRIPT_DIR, 'locale')
ICON_ICO = os.path.join(SCRIPT_DIR, 'io.github.aginies.watermark.ico')
ICON_PNG = os.path.join(SCRIPT_DIR, 'io.github.aginies.watermark.png')

# ============================================================================
# DATA FILES
# ============================================================================

datas = []

# Locale files (translations)
if os.path.exists(LOCALE_DIR):
    datas.append((LOCALE_DIR, 'share/locale'))

# Application icons
if os.path.exists(ICON_ICO):
    datas.append((ICON_ICO, '.'))
if os.path.exists(ICON_PNG):
    datas.append((ICON_PNG, '.'))

# GTK/GObject data files
datas += collect_data_files('gi')

# ============================================================================
# HIDDEN IMPORTS
# ============================================================================

hiddenimports = [
    # GTK and GObject introspection
    'gi',
    'gi.repository',
    'gi.repository.Gtk',
    'gi.repository.GdkPixbuf',
    'gi.repository.Gio',
    'gi.repository.Pango',
    'gi.repository.GLib',
    'gi.repository.Gdk',
    'gi._gi',
    'gi._gi_cairo',
    
    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL._imaging',
    'PIL._imagingtk',
    
    # PDF handling
    'pdf2image',
    'pdf2image.exceptions',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.utils',
    'reportlab.lib.colors',
    'reportlab.platypus',
    
    # Standard library modules
    'tempfile',
    'pathlib',
    'uuid',
    'shutil',
    'subprocess',
    'gettext',
    'locale',
    
    # Windows-specific
    'winreg',  # Only used on Windows, ignored on other platforms
    'pyi_splash',  # For splash screen support
]

# Collect all gi.repository submodules
hiddenimports += collect_submodules('gi.repository')

# ============================================================================
# BINARIES
# ============================================================================

binaries = []

# On Windows, you may need to add GTK runtime DLLs manually
# Example:
# if sys.platform == 'win32':
#     GTK_RUNTIME = r'C:\gtk-runtime\bin'
#     if os.path.exists(GTK_RUNTIME):
#         binaries += [(os.path.join(GTK_RUNTIME, '*.dll'), '.')]

# ============================================================================
# EXCLUSIONS (to reduce size)
# ============================================================================

excludes = [
    'tkinter',
    'unittest',
    'test',
    'pytest',
    'numpy.tests',
    'matplotlib',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    '_pytest',
    'distutils',
]

# ============================================================================
# ANALYSIS
# ============================================================================

block_cipher = None

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[SCRIPT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# PYZ (Python Bytecode Archive)
# ============================================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ============================================================================
# EXE (Executable)
# ============================================================================

exe_kwargs = {
    'name': APP_NAME,
    'debug': False,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': USE_UPX,
    'upx_exclude': [],
    'runtime_tmpdir': None,
    'console': False,  # Set to True for debugging
    'disable_windowed_traceback': False,
    'target_arch': None,
    'codesign_identity': None,
    'entitlements_file': None,
}

# Add icon based on platform
if sys.platform == 'win32' and os.path.exists(ICON_ICO):
    exe_kwargs['icon'] = ICON_ICO
elif os.path.exists(ICON_PNG):
    exe_kwargs['icon'] = ICON_PNG

# Windows-specific version info
if sys.platform == 'win32':
    exe_kwargs['version'] = 'version_info.txt'  # Optional: create this file separately
    # Alternative: inline version info
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
        StringStruct, VarFileInfo, VarStruct
    )
    
    version_tuple = tuple(map(int, APP_VERSION.split('.')))
    
    exe_kwargs['version'] = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version_tuple,
            prodvers=version_tuple,
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0)
        ),
        kids=[
            StringFileInfo([
                StringTable(
                    '040904B0',  # English (US)
                    [
                        StringStruct('CompanyName', APP_AUTHOR),
                        StringStruct('FileDescription', APP_DESCRIPTION),
                        StringStruct('FileVersion', APP_VERSION),
                        StringStruct('InternalName', APP_NAME),
                        StringStruct('LegalCopyright', APP_COPYRIGHT),
                        StringStruct('OriginalFilename', f'{APP_NAME}.exe'),
                        StringStruct('ProductName', 'Watermark App GTK'),
                        StringStruct('ProductVersion', APP_VERSION),
                    ]
                )
            ]),
            VarFileInfo([VarStruct('Translation', [1033, 1200])])
        ]
    )

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        **exe_kwargs
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **exe_kwargs
    )
    
    # ============================================================================
    # COLLECT (Folder Mode)
    # ============================================================================
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=USE_UPX,
        upx_exclude=[],
        name=APP_NAME
    )

# ============================================================================
# NOTES FOR WINDOWS BUILD
# ============================================================================
"""
IMPORTANT NOTES FOR WINDOWS:

1. GTK Runtime:
   - Install GTK3 runtime from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
   - Or use MSYS2: pacman -S mingw-w64-x86_64-gtk3
   - GTK DLLs must be in PATH or bundled with the executable

2. Poppler (for PDF support):
   - Download from: https://github.com/oschwartz10612/poppler-windows/releases
   - Extract poppler/Library/bin to same folder as executable
   - Or set POPPLER_PATH environment variable

3. Dependencies:
   pip install pillow pdf2image reportlab PyGObject

4. Build command:
   pyinstaller watermark_app_gtk.spec

5. Testing:
   - Test the executable on a clean Windows system
   - Ensure all DLLs are included or in PATH
   - Check that locale files load correctly
   - Verify PDF functionality (requires poppler)

6. Troubleshooting:
   - If executable fails, rebuild with console=True to see errors
   - Use Dependency Walker to check missing DLLs
   - Check Windows Event Viewer for crash details
"""
