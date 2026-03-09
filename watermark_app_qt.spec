# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Watermark App (Qt/PyQt6 version)
Author: antoine@ginies.org

Usage:
    pyinstaller watermark_app_qt.spec

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
APP_NAME = 'WatermarkApp_Qt'
APP_VERSION = '5.0.0.0'
APP_DESCRIPTION = 'Watermark application for images and PDFs (Qt version)'
APP_COPYRIGHT = 'Copyright (C) 2025 Antoine Ginies'
APP_AUTHOR = 'Antoine Ginies'

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(SPEC))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, 'watermark_app_qt.py')
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

# PyQt6 data files (includes Qt plugins and resources)
try:
    datas += collect_data_files('PyQt6')
except Exception:
    pass  # PyQt6 may not be installed on build system

# ============================================================================
# HIDDEN IMPORTS
# ============================================================================

hiddenimports = [
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    
    # PIL/Pillow
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL._imaging',
    
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
]

# Collect PyQt6 submodules
try:
    hiddenimports += collect_submodules('PyQt6')
except Exception:
    pass

# ============================================================================
# BINARIES
# ============================================================================

binaries = []

# PyQt6 platform plugins are usually collected automatically, but can be added manually:
# if sys.platform == 'win32':
#     QT_PLUGINS_DIR = r'C:\Python\Lib\site-packages\PyQt6\Qt6\plugins'
#     if os.path.exists(QT_PLUGINS_DIR):
#         binaries += [(os.path.join(QT_PLUGINS_DIR, 'platforms', '*.dll'), 'platforms')]

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
    'PySide2',
    'PySide6',
    'gi',  # GTK not needed for Qt version
    'gi.repository',
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
                        StringStruct('ProductName', 'Watermark App Qt'),
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

1. PyQt6 Installation:
   pip install PyQt6

2. Poppler (for PDF support):
   - Download from: https://github.com/oschwartz10612/poppler-windows/releases
   - Extract poppler/Library/bin to same folder as executable
   - Or set POPPLER_PATH environment variable

3. Dependencies:
   pip install pillow pdf2image reportlab PyQt6

4. Build command:
   pyinstaller watermark_app_qt.spec

5. Qt Platform Plugin:
   - PyInstaller should automatically include Qt platform plugins
   - If "Could not find Qt platform plugin" error occurs:
     * Ensure platforms/ folder is in same directory as .exe
     * Set QT_QPA_PLATFORM_PLUGIN_PATH environment variable

6. Testing:
   - Test the executable on a clean Windows system
   - Verify all Qt DLLs are included
   - Check that locale files load correctly
   - Verify PDF functionality (requires poppler)

7. Troubleshooting:
   - If executable fails, rebuild with console=True to see errors
   - Check for missing DLLs using Dependency Walker
   - Verify Qt plugins are in the correct location
   - Use --debug=all flag when running pyinstaller for verbose output

8. Size Optimization:
   - The Qt version typically produces larger executables than GTK
   - Consider folder mode for better startup performance
   - Disable UPX if size is not a concern (faster build, no compression issues)

9. Advantages of Qt version:
   - Better Windows integration
   - More consistent cross-platform look
   - Easier dependency management on Windows
   - No need for GTK runtime installation
"""
