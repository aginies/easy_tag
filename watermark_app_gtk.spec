# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Watermark App (GTK version)
Author: antoine@ginies.org

Usage:
    # Standard build (release mode, no console)
    pyinstaller watermark_app_gtk.spec
    
    # Debug build (with console for error messages)
    # Edit DEBUG_MODE = True below, then run:
    pyinstaller watermark_app_gtk.spec

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

# GTK/GObject data files
datas += collect_data_files('gi')

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
    'pyi_splash',  # For splash screen support
]

# Collect all gi.repository submodules
hiddenimports += collect_submodules('gi.repository')

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
