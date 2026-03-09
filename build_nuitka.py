#!/usr/bin/env python3
"""
Cross-platform Nuitka build script for Watermark App
Works on both Linux and Windows
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse

# Configuration
APP_NAME = "watermark_app_gtk"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, f"{APP_NAME}.py")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "dist")
LOCALE_DIR = os.path.join(SCRIPT_DIR, "locale")

# Platform-specific settings
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MACOS = platform.system() == "Darwin"

if IS_WINDOWS:
    ICON_FILE = os.path.join(SCRIPT_DIR, "io.github.aginies.watermark.ico")
    EXE_NAME = f"{APP_NAME}.exe"
else:
    ICON_FILE = os.path.join(SCRIPT_DIR, "io.github.aginies.watermark.png")
    EXE_NAME = APP_NAME


class Colors:
    """ANSI color codes for terminal output"""

    if IS_WINDOWS:
        # Enable ANSI on Windows
        os.system("")
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color


def echo_info(msg):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {msg}")


def echo_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")


def echo_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


def check_nuitka():
    """Check if Nuitka is installed"""
    try:
        subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True,
            check=True,
        )
        echo_info("Nuitka found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        echo_error("Nuitka is not installed!")
        echo_info("Install it with: pip install nuitka")
        if IS_LINUX:
            echo_info("Or on openSUSE: sudo zypper install python3-Nuitka")
        return False


def check_dependencies():
    """Check for required Python dependencies"""
    echo_info("Checking dependencies...")

    missing = []

    # Check Pillow
    try:
        import PIL
    except ImportError:
        missing.append("pillow")

    # Check PyPDF2
    try:
        import PyPDF2
    except ImportError:
        missing.append("PyPDF2")

    # Check PyGObject/GTK
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
    except (ImportError, ValueError) as e:
        if IS_WINDOWS:
            echo_error("PyGObject/GTK3 not available")
            echo_info("For Windows, install GTK3 runtime and PyGObject:")
            echo_info(
                "  - Use MSYS2: pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python-gobject"
            )
            echo_info(
                "  - Or download from: https://github.com/nickvidal/pyobject-gtk3-windows"
            )
        else:
            echo_error(f"PyGObject/GTK3 not available: {e}")
            echo_info("Install with: pip install PyGObject")
        return False

    if missing:
        echo_error(f"Missing packages: {', '.join(missing)}")
        echo_info(f"Install with: pip install {' '.join(missing)}")
        return False

    echo_info("All Python dependencies are available")
    return True


def clean_build():
    """Remove previous build artifacts"""
    echo_info("Cleaning previous build artifacts...")

    dirs_to_remove = [
        OUTPUT_DIR,
        os.path.join(SCRIPT_DIR, f"{APP_NAME}.build"),
        os.path.join(SCRIPT_DIR, f"{APP_NAME}.dist"),
        os.path.join(SCRIPT_DIR, f"{APP_NAME}.onefile-build"),
    ]

    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            echo_info(f"Removed: {d}")


def build(onefile=True):
    """Build the application with Nuitka"""
    mode = "onefile" if onefile else "folder"
    echo_info(f"Building standalone {mode} with Nuitka...")
    echo_info("This may take several minutes...")

    # Base Nuitka command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        f"--output-dir={OUTPUT_DIR}",
        "--enable-plugin=gi",
        f"--include-data-dir={LOCALE_DIR}=locale",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=unittest",
        "--nofollow-import-to=test",
        "--product-name=Watermark App",
        "--product-version=3.0.0.0",
        "--file-description=Watermark application for images and PDFs",
        "--copyright=antoine@ginies.org",
    ]

    # Add onefile option
    if onefile:
        cmd.append("--onefile")
        cmd.append(f"--output-filename={EXE_NAME}")

    # Platform-specific options
    if IS_WINDOWS:
        cmd.extend(
            [
                f"--windows-icon-from-ico={ICON_FILE}",
                "--windows-console-mode=disable",
                "--company-name=Antoine Ginies",
            ]
        )
        if os.path.exists(ICON_FILE):
            cmd.append(
                f"--include-data-file={ICON_FILE}=io.github.aginies.watermark.ico"
            )
    else:
        cmd.append(f"--linux-icon={ICON_FILE}")
        if os.path.exists(ICON_FILE):
            cmd.append(
                f"--include-data-file={ICON_FILE}=io.github.aginies.watermark.png"
            )

    # Add main script
    cmd.append(MAIN_SCRIPT)

    # Run Nuitka
    echo_info(f"Running: {' '.join(cmd[:5])}...")

    try:
        subprocess.run(cmd, check=True)
        echo_info("Build completed!")
        return True
    except subprocess.CalledProcessError as e:
        echo_error(f"Build failed with error code: {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build Watermark App using Nuitka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_nuitka.py              # Build single executable
  python build_nuitka.py --folder     # Build standalone folder
  python build_nuitka.py --clean      # Clean previous builds

Platform: {platform}
Output will be in: dist/
        """.format(platform=platform.system()),
    )

    parser.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Build single executable file (default)",
    )
    parser.add_argument(
        "--folder",
        action="store_true",
        help="Build standalone folder (easier to debug)",
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean build artifacts only"
    )

    args = parser.parse_args()

    os.chdir(SCRIPT_DIR)

    print("=" * 50)
    print(f"  Watermark App - Nuitka Build Script")
    print(f"  Platform: {platform.system()}")
    print("=" * 50)
    print()

    if args.clean:
        clean_build()
        echo_info("Clean completed")
        return 0

    if not check_nuitka():
        return 1

    if not check_dependencies():
        return 1

    clean_build()

    onefile = not args.folder

    if build(onefile=onefile):
        print()
        if onefile:
            output_path = os.path.join(OUTPUT_DIR, EXE_NAME)
            echo_info(f"Executable created: {output_path}")
        else:
            output_path = os.path.join(OUTPUT_DIR, f"{APP_NAME}.dist")
            echo_info(f"Folder created: {output_path}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
