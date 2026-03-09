@echo off
REM Build script for Watermark App using Nuitka (Windows)
REM Creates a standalone .exe for watermark_app_gtk.py

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "APP_NAME=watermark_app_gtk"
set "MAIN_SCRIPT=%SCRIPT_DIR%%APP_NAME%.py"
set "OUTPUT_DIR=%SCRIPT_DIR%dist"
set "ICON_FILE=%SCRIPT_DIR%io.github.aginies.watermark.ico"

echo ============================================
echo  Watermark App - Nuitka Build Script
echo ============================================
echo.

REM Parse arguments
if "%1"=="--help" goto :usage
if "%1"=="-h" goto :usage
if "%1"=="--clean" goto :clean
if "%1"=="--folder" goto :build_folder

REM Default: build onefile
goto :build_onefile

:check_nuitka
echo [INFO] Checking for Nuitka...
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Nuitka is not installed!
    echo [INFO] Install it with: pip install nuitka
    exit /b 1
)
echo [INFO] Nuitka found
goto :eof

:check_dependencies
echo [INFO] Checking dependencies...
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo [ERROR] Pillow not installed ^(pip install pillow^)
    exit /b 1
)
python -c "import PyPDF2" 2>nul
if errorlevel 1 (
    echo [ERROR] PyPDF2 not installed ^(pip install PyPDF2^)
    exit /b 1
)
python -c "import gi" 2>nul
if errorlevel 1 (
    echo [ERROR] PyGObject not installed. Install GTK3 runtime and PyGObject
    echo [INFO] Download from: https://github.com/nickvidal/pyobject-gtk3-windows
    echo [INFO] Or use MSYS2: pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python-gobject
    exit /b 1
)
echo [INFO] All Python dependencies are available
goto :eof

:clean
echo [INFO] Cleaning previous build artifacts...
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
if exist "%SCRIPT_DIR%%APP_NAME%.build" rmdir /s /q "%SCRIPT_DIR%%APP_NAME%.build"
if exist "%SCRIPT_DIR%%APP_NAME%.dist" rmdir /s /q "%SCRIPT_DIR%%APP_NAME%.dist"
if exist "%SCRIPT_DIR%%APP_NAME%.onefile-build" rmdir /s /q "%SCRIPT_DIR%%APP_NAME%.onefile-build"
echo [INFO] Clean completed
goto :end

:build_onefile
call :check_nuitka
if errorlevel 1 exit /b 1
call :check_dependencies
if errorlevel 1 exit /b 1

echo [INFO] Building standalone .exe with Nuitka...
echo [INFO] This may take several minutes...

python -m nuitka ^
    --standalone ^
    --onefile ^
    --assume-yes-for-downloads ^
    --output-dir="%OUTPUT_DIR%" ^
    --output-filename="%APP_NAME%.exe" ^
    --enable-plugin=gi ^
    --include-data-dir="%SCRIPT_DIR%locale=locale" ^
    --include-data-file="%ICON_FILE%=io.github.aginies.watermark.ico" ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    --windows-icon-from-ico="%ICON_FILE%" ^
    --windows-console-mode=disable ^
    --product-name="Watermark App" ^
    --product-version="3.0.0.0" ^
    --file-description="Watermark application for images and PDFs" ^
    --copyright="antoine@ginies.org" ^
    --company-name="Antoine Ginies" ^
    "%MAIN_SCRIPT%"

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

echo.
echo [INFO] Build completed!
echo [INFO] Executable created: %OUTPUT_DIR%\%APP_NAME%.exe
goto :end

:build_folder
call :check_nuitka
if errorlevel 1 exit /b 1
call :check_dependencies
if errorlevel 1 exit /b 1

echo [INFO] Building standalone folder with Nuitka...
echo [INFO] This may take several minutes...

python -m nuitka ^
    --standalone ^
    --assume-yes-for-downloads ^
    --output-dir="%OUTPUT_DIR%" ^
    --enable-plugin=gi ^
    --include-data-dir="%SCRIPT_DIR%locale=locale" ^
    --include-data-file="%ICON_FILE%=io.github.aginies.watermark.ico" ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    --windows-icon-from-ico="%ICON_FILE%" ^
    --windows-console-mode=disable ^
    --product-name="Watermark App" ^
    --product-version="3.0.0.0" ^
    --file-description="Watermark application for images and PDFs" ^
    --copyright="antoine@ginies.org" ^
    --company-name="Antoine Ginies" ^
    "%MAIN_SCRIPT%"

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

echo.
echo [INFO] Build completed!
echo [INFO] Folder created: %OUTPUT_DIR%\%APP_NAME%.dist\
goto :end

:usage
echo Usage: %~nx0 [OPTIONS]
echo.
echo Build Watermark App using Nuitka for Windows
echo.
echo Options:
echo   --onefile     Build single .exe file (default)
echo   --folder      Build standalone folder (easier to debug)
echo   --clean       Clean build artifacts only
echo   --help        Show this help message
echo.
echo Examples:
echo   %~nx0             # Build single .exe
echo   %~nx0 --folder    # Build standalone folder
echo   %~nx0 --clean     # Clean previous builds
echo.
echo Prerequisites:
echo   1. Python 3.x with pip
echo   2. Nuitka: pip install nuitka
echo   3. Dependencies: pip install pillow PyPDF2
echo   4. GTK3 Runtime + PyGObject for Windows
goto :end

:end
endlocal
