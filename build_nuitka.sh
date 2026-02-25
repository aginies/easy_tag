#!/bin/bash
# Build script for Watermark App using Nuitka
# Creates a standalone binary for watermark_app_gtk.py

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="watermark_app_gtk"
MAIN_SCRIPT="${SCRIPT_DIR}/${APP_NAME}.py"
OUTPUT_DIR="${SCRIPT_DIR}/dist"
BUILD_DIR="${SCRIPT_DIR}/build"
ICON_FILE="${SCRIPT_DIR}/io.github.aginies.watermark.png"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Nuitka is installed
check_nuitka() {
    if ! command -v nuitka &> /dev/null && ! python3 -m nuitka --version &> /dev/null 2>&1; then
        echo_error "Nuitka is not installed!"
        echo_info "Install it with: pip install nuitka"
        echo_info "Or on openSUSE: sudo zypper install python3-Nuitka"
        exit 1
    fi
    echo_info "Nuitka found"
}

# Check for required dependencies
check_dependencies() {
    echo_info "Checking dependencies..."
    
    # Check for Python packages
    python3 -c "import PIL" 2>/dev/null || { echo_error "Pillow not installed (pip install pillow)"; exit 1; }
    python3 -c "import PyPDF2" 2>/dev/null || { echo_error "PyPDF2 not installed (pip install PyPDF2)"; exit 1; }
    python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null || { echo_error "PyGObject/GTK3 not available"; exit 1; }
    
    echo_info "All Python dependencies are available"
}

# Clean previous builds
clean_build() {
    echo_info "Cleaning previous build artifacts..."
    rm -rf "${OUTPUT_DIR}" "${BUILD_DIR}"
    rm -rf "${SCRIPT_DIR}/${APP_NAME}.build"
    rm -rf "${SCRIPT_DIR}/${APP_NAME}.dist"
    rm -rf "${SCRIPT_DIR}/${APP_NAME}.onefile-build"
}

# Build with Nuitka
build_standalone() {
    echo_info "Building standalone binary with Nuitka..."
    echo_info "This may take several minutes..."
    
    python3 -m nuitka \
        --standalone \
        --onefile \
        --assume-yes-for-downloads \
        --output-dir="${OUTPUT_DIR}" \
        --output-filename="${APP_NAME}" \
        --enable-plugin=gi \
        --include-data-dir="${SCRIPT_DIR}/locale=locale" \
        --include-data-file="${ICON_FILE}=io.github.aginies.watermark.png" \
        --nofollow-import-to=tkinter \
        --nofollow-import-to=unittest \
        --nofollow-import-to=test \
        --linux-icon="${ICON_FILE}" \
        --product-name="Watermark App" \
        --product-version="3.0" \
        --file-description="Watermark application for images and PDFs" \
        --copyright="antoine@ginies.org" \
        "${MAIN_SCRIPT}"
    
    echo_info "Build completed!"
}

# Build folder mode (not onefile, useful for debugging)
build_folder() {
    echo_info "Building standalone folder with Nuitka..."
    echo_info "This may take several minutes..."
    
    python3 -m nuitka \
        --standalone \
        --assume-yes-for-downloads \
        --output-dir="${OUTPUT_DIR}" \
        --enable-plugin=gi \
        --include-data-dir="${SCRIPT_DIR}/locale=locale" \
        --include-data-file="${ICON_FILE}=io.github.aginies.watermark.png" \
        --nofollow-import-to=tkinter \
        --nofollow-import-to=unittest \
        --nofollow-import-to=test \
        --linux-icon="${ICON_FILE}" \
        --product-name="Watermark App" \
        --product-version="3.0" \
        --file-description="Watermark application for images and PDFs" \
        --copyright="antoine@ginies.org" \
        "${MAIN_SCRIPT}"
    
    echo_info "Build completed!"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build Watermark App using Nuitka"
    echo ""
    echo "Options:"
    echo "  --onefile     Build single executable file (default)"
    echo "  --folder      Build standalone folder (easier to debug)"
    echo "  --clean       Clean build artifacts only"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0             # Build single executable"
    echo "  $0 --folder    # Build standalone folder"
    echo "  $0 --clean     # Clean previous builds"
}

# Main
main() {
    cd "${SCRIPT_DIR}"
    
    case "${1:-}" in
        --help|-h)
            usage
            exit 0
            ;;
        --clean)
            clean_build
            echo_info "Clean completed"
            exit 0
            ;;
        --folder)
            check_nuitka
            check_dependencies
            clean_build
            build_folder
            echo ""
            echo_info "Standalone folder created in: ${OUTPUT_DIR}/${APP_NAME}.dist/"
            echo_info "Run with: ${OUTPUT_DIR}/${APP_NAME}.dist/${APP_NAME}"
            ;;
        --onefile|"")
            check_nuitka
            check_dependencies
            clean_build
            build_standalone
            echo ""
            echo_info "Single executable created: ${OUTPUT_DIR}/${APP_NAME}"
            echo_info "Run with: ${OUTPUT_DIR}/${APP_NAME}"
            ;;
        *)
            echo_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
