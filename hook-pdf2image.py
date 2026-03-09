"""
PyInstaller runtime hook for pdf2image
Helps pdf2image locate poppler binaries in the frozen application
"""

import os
import sys

# When frozen by PyInstaller, add poppler/bin to PATH
if getattr(sys, "frozen", False):
    # Get the bundle directory
    if hasattr(sys, "_MEIPASS"):
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.dirname(sys.executable)

    # Add poppler bin directory to PATH
    poppler_bin = os.path.join(bundle_dir, "poppler", "bin")

    if os.path.exists(poppler_bin):
        # Prepend to PATH so it's found first
        os.environ["PATH"] = poppler_bin + os.pathsep + os.environ.get("PATH", "")
        print(f"PDF2IMAGE: Added poppler path: {poppler_bin}")
    else:
        print(f"WARNING: Poppler binaries not found at {poppler_bin}")
        print(
            "PDF functionality may not work. Ensure poppler is bundled with the application."
        )
