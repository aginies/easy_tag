# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Watermark App (Qt/PyQt6 version)
Author: antoine@ginies.org

Usage:
    # Standard build (release mode, no console)
    pyinstaller watermark_app_qt.spec
    
    # Debug build (with console for error messages)
    # Edit DEBUG_MODE = True below, then run:
    pyinstaller watermark_app_qt.spec

Build modes:
    - Edit ONEFILE variable below to switch between onefile and folder mode
    - Onefile: Single executable (slower startup, easier distribution)
    - Folder: Multiple files (faster startup, larger distribution)
    
    - Edit DEBUG_MODE to enable/disable console and debug output
    - Debug: Console window enabled, shows errors and warnings
    - Release: No console, GUI-only application
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

# Debug mode: Set to True to enable console output and debug logging
DEBUG_MODE = False

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

# Poppler path (for PDF support on Windows)
# Set this to your poppler installation path if you have it installed
# Example: POPPLER_PATH = r'C:\poppler-24.02.0\Library\bin'
POPPLER_PATH = os.environ.get('POPPLER_PATH', None)

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

# Manually include pdf2image and reportlab packages from site-packages
try:
    import pdf2image
    import reportlab
    
    pdf2image_path = os.path.dirname(pdf2image.__file__)
    reportlab_path = os.path.dirname(reportlab.__file__)
    
    # Add entire pdf2image package
    datas.append((pdf2image_path, 'pdf2image'))
    print(f"INFO: Manually bundling pdf2image from: {pdf2image_path}")
    
    # Add entire reportlab package
    datas.append((reportlab_path, 'reportlab'))
    print(f"INFO: Manually bundling reportlab from: {reportlab_path}")
    
except ImportError as e:
    print(f"WARNING: Could not locate packages for manual bundling: {e}")
    # Fallback to automatic collection
    try:
        datas += collect_data_files('pdf2image')
    except Exception as e2:
        print(f"Note: Could not collect pdf2image data files: {e2}")
    
    try:
        datas += collect_data_files('reportlab')
    except Exception as e2:
        print(f"Note: Could not collect reportlab data files: {e2}")

# Poppler binaries (for pdf2image on Windows)
if sys.platform == 'win32' and POPPLER_PATH and os.path.exists(POPPLER_PATH):
    import glob
    poppler_bins = glob.glob(os.path.join(POPPLER_PATH, '*.exe'))
    poppler_dlls = glob.glob(os.path.join(POPPLER_PATH, '*.dll'))
    for bin_file in poppler_bins + poppler_dlls:
        datas.append((bin_file, 'poppler/bin'))
    print(f"INFO: Found {len(poppler_bins)} poppler executables and {len(poppler_dlls)} DLLs")
elif sys.platform == 'win32':
    print("WARNING: POPPLER_PATH not set. PDF functionality may not work!")
    print("Set environment variable: set POPPLER_PATH=C:\\path\\to\\poppler\\bin")
    print("Or edit POPPLER_PATH in the spec file")

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
    
    # PDF handling - pdf2image and all its dependencies
    'pdf2image',
    'pdf2image.exceptions',
    'pdf2image.pdf2image',
    'pdf2image.parsers',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.utils',
    'reportlab.lib.colors',
    'reportlab.lib.pagesizes',
    'reportlab.platypus',
    'reportlab.rl_config',
    
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

# Try to collect pdf2image and reportlab submodules (may not be packages)
try:
    hiddenimports += collect_submodules('pdf2image')
except Exception as e:
    print(f"Note: Could not auto-collect pdf2image submodules: {e}")
    print("Using explicit imports instead (already defined above)")

try:
    hiddenimports += collect_submodules('reportlab')
except Exception as e:
    print(f"Note: Could not auto-collect reportlab submodules: {e}")
    print("Using explicit imports instead (already defined above)")

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
    hookspath=[SCRIPT_DIR],  # Look for hooks in script directory
    hooksconfig={},
    runtime_hooks=[os.path.join(SCRIPT_DIR, 'hook-pdf2image.py')] if os.path.exists(os.path.join(SCRIPT_DIR, 'hook-pdf2image.py')) else [],
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
    'debug': DEBUG_MODE,
    'bootloader_ignore_signals': False,
    'strip': False,
    'upx': USE_UPX,
    'upx_exclude': [],
    'runtime_tmpdir': None,
    'console': DEBUG_MODE,  # Enable console in debug mode
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
