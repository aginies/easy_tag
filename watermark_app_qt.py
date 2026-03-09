#!/usr/bin/python3
import sys
import os
import random
import time
import gettext
import platform
import subprocess
import re
import pathlib
import uuid
import shutil
import tempfile
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Check for PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QFileDialog,
        QProgressBar,
        QDialog,
        QMessageBox,
        QLineEdit,
        QSlider,
        QColorDialog,
        QCheckBox,
        QComboBox,
        QGroupBox,
        QMenuBar,
        QMenu,
        QScrollArea,
        QSizePolicy,
    )
    from PyQt6.QtGui import QAction, QPixmap, QImage, QColor, QFont, QIcon
    from PyQt6.QtCore import Qt, QSize, QTimer
except ImportError:
    print("PyQt6 is not installed. Please install it using: pip install PyQt6")
    sys.exit(1)

from PIL import Image, ImageDraw, ImageFont

# Windows Registry for font detection
if platform.system() == "Windows":
    import winreg

    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
        except ImportError:
            pass

# Localization setup (simplified for now)
try:
    _ = gettext.gettext
except:

    def _(s):
        return s


def get_xdg_pictures_dir():
    """
    Returns the path to the user's XDG Pictures directory.
    """
    try:
        if platform.system() == "Windows":
            return os.path.join(os.environ["USERPROFILE"], "Pictures")

        result = subprocess.run(
            ["xdg-user-dir", "PICTURES"], capture_output=True, text=True, check=True
        )
        path = result.stdout.strip()
        if path:
            pictures_dir = pathlib.Path(path)
            if pictures_dir.is_absolute():
                return str(pictures_dir)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return os.path.expanduser("~")


class ProgressDialog(QDialog):
    def __init__(self, parent, title, max_value):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)
        self.setModal(True)

        layout = QVBoxLayout()
        self.label = QLabel("Processing...")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, max_value)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.setLayout(layout)
        self.show()
        QApplication.processEvents()

    def update_progress(self, value):
        self.progress.setValue(value)
        self.label.setText(f"{value}/{self.progress.maximum()}")
        QApplication.processEvents()

    def set_status(self, text):
        self.label.setText(text)
        QApplication.processEvents()

    def pulse(self):
        # QProgressBar doesn't have a direct "pulse" in determinate mode,
        # but we can just process events to keep UI alive
        QApplication.processEvents()


class ImageViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Viewer")
        self.resize(800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # File label
        self.file_label = QLabel()
        self.main_layout.addWidget(self.file_label)

        # Image area (ScrollArea for large images or scalable label)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.main_layout.addWidget(self.scroll_area)

        # Navigation
        self.nav_layout = QHBoxLayout()
        self.prev_button = QPushButton(_("Previous"))
        self.prev_button.clicked.connect(self.on_previous_clicked)
        self.nav_layout.addWidget(self.prev_button)

        self.index_label = QLabel()
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nav_layout.addWidget(self.index_label)

        self.next_button = QPushButton(_("Next"))
        self.next_button.clicked.connect(self.on_next_clicked)
        self.nav_layout.addWidget(self.next_button)

        self.main_layout.addLayout(self.nav_layout)

        self.images = []
        self.current_index = -1

    def load_images(self, image_paths):
        self.images = image_paths
        self.current_index = 0 if len(image_paths) > 0 else -1
        self.update_buttons_state()
        self.update_index_label()
        if len(self.images) > 0:
            self.display_single_image(self.images[self.current_index])

    def display_single_image(self, image_path):
        self.file_label.setText(image_path)

        # Check if it's a PDF file
        if image_path.lower().endswith(".pdf"):
            # Convert first page of PDF to image for display
            try:
                images = convert_from_path(
                    image_path, dpi=150, first_page=1, last_page=1
                )
                if images:
                    # Save to temporary file
                    temp_dir = os.path.join(tempfile.gettempdir(), "watermark_app")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_image_path = os.path.join(
                        temp_dir, f"pdf_view_{os.path.basename(image_path)}.jpg"
                    )
                    images[0].save(temp_image_path, "JPEG")
                    # Load the temporary image
                    pixmap = QPixmap(temp_image_path)
                else:
                    self.image_label.setText("Could not render PDF page")
                    return
            except Exception as pdf_err:
                self.image_label.setText(f"Error loading PDF: {pdf_err}")
                return
        else:
            # Load regular image
            pixmap = QPixmap(image_path)

        if not pixmap.isNull():
            # Scale if too big
            view_size = self.scroll_area.size()
            if (
                pixmap.width() > view_size.width()
                or pixmap.height() > view_size.height()
            ):
                pixmap = pixmap.scaled(
                    view_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("Could not load image")

    def update_buttons_state(self):
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.images) - 1)

    def update_index_label(self):
        total = len(self.images)
        if total > 0:
            self.index_label.setText(f"{self.current_index + 1}/{total}")
        else:
            self.index_label.setText("0/0")

    def on_previous_clicked(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.display_single_image(self.images[self.current_index])
            self.update_buttons_state()
            self.update_index_label()

    def on_next_clicked(self):
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.display_single_image(self.images[self.current_index])
            self.update_buttons_state()
            self.update_index_label()


def get_style_string(style):
    # Mapping might not be needed if we rely on simple string matching
    return str(style)


def get_ttf_fonts():
    """Scans the system for all TTF fonts using the 'fc-list' command-line tool (Linux)."""
    ttf_fonts_data = []
    if platform.system() == "Windows":
        return []  # Windows uses registry

    if not os.path.exists("/usr/bin/fc-list"):
        print("Warning: 'fc-list' command not found.")
        return ttf_fonts_data

    try:
        command = ["fc-list", "-f", "%{file}|%{family}|%{style}\n"]
        output = subprocess.check_output(command).decode("utf-8")
        for line in output.strip().split("\n"):
            try:
                parts = line.split("|")
                if len(parts) == 3:
                    filepath, family, style = parts

                if filepath.lower().endswith(".ttf") or filepath.lower().endswith(
                    ".otf"
                ):
                    cleaned_family = family.split(",")[0].strip()
                    ttf_fonts_data.append(
                        {
                            "file": filepath,
                            "family": cleaned_family,
                            "style": style.strip(),
                        }
                    )
            except ValueError:
                continue
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        print(f"Error executing 'fc-list': {err}")

    return ttf_fonts_data


class WatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Watermark App (Qt)"))
        self.resize(500, 700)

        self.output_folder_path = ""
        self.compression_rate = 75
        self.selected_resize = "1280"
        self.font_size = 32
        self.font_base_name = None
        self.watermak_prefix = ""
        self.fili_density = 70
        self.rotation_angle = 30
        self.selected_files_path = []
        self.all_images = []
        self.current_image_index = 0
        self.image_paths = ""
        self.font_color = (0, 0, 0, 255)  # RGBA tuple
        self.font_color_choosen = False
        self.font_transparency = 25
        self.pdf_choosen = False
        self.init_real_size = 32
        self.real_fsize = None
        self.pdf_original_dirname = None
        self.preview_window = None

        self.ALL_LINUX_TTF_FONT_DATA = get_ttf_fonts()

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.set_default_font()

        if platform.system() == "Windows":
            if getattr(sys, "frozen", False) and "pyi_splash" in sys.modules:
                pass  # pyi_splash handling

    def setup_ui(self):
        # Menu Bar
        menubar = self.menuBar()

        # Preferences Menu
        pref_menu = menubar.addMenu(_("Preferences"))
        self.expert_options_action = QAction(_("Show Expert Options"), self)
        self.expert_options_action.setCheckable(True)
        self.expert_options_action.setChecked(False)
        self.expert_options_action.toggled.connect(self.on_expert_toggle)
        pref_menu.addAction(self.expert_options_action)

        # Help/About Menu
        help_menu = menubar.addMenu(_("Help"))
        about_action = QAction(_("About Watermark App"), self)
        about_action.triggered.connect(self.about_dialog)
        help_menu.addAction(about_action)

        # File Selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel(_("Select Image or PDF File(s)")))
        self.file_chooser_btn = QPushButton(_("Choose Files"))
        self.file_chooser_btn.clicked.connect(self.on_files_clicked)
        file_layout.addWidget(self.file_chooser_btn)
        self.main_layout.addLayout(file_layout)

        self.files_label = QLabel(_("No files selected"))
        self.files_label.setWordWrap(True)
        self.main_layout.addWidget(self.files_label)

        # Watermark Text
        wm_layout = QHBoxLayout()
        wm_layout.addWidget(QLabel(_("Watermark Text")))
        self.watermark_entry = QLineEdit()
        self.watermark_entry.setPlaceholderText(_("Watermark Text"))
        wm_layout.addWidget(self.watermark_entry)
        self.main_layout.addLayout(wm_layout)

        # Font Chooser
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(_("TTF Font chooser")))
        self.font_chooser_btn = QPushButton(_("No font selected"))
        self.font_chooser_btn.clicked.connect(self.on_font_selected)
        font_layout.addWidget(self.font_chooser_btn)
        self.main_layout.addLayout(font_layout)

        # Output Folder
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel(_("Select Output Folder")))
        self.output_btn = QPushButton(_("Select Folder"))
        self.output_btn.clicked.connect(self.on_output_clicked)
        out_layout.addWidget(self.output_btn)
        self.main_layout.addLayout(out_layout)
        self.output_label = QLabel("")
        self.main_layout.addWidget(self.output_label)

        # Expert Options Group
        self.expert_group = QGroupBox(_("Expert Options"))
        self.expert_layout = QVBoxLayout()
        self.expert_group.setLayout(self.expert_layout)

        # Rotation
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel(_("Angle (degrees)")))
        self.rotation_scale = QSlider(Qt.Orientation.Horizontal)
        self.rotation_scale.setRange(0, 90)
        self.rotation_scale.setValue(self.rotation_angle)
        self.rotation_scale.valueChanged.connect(self.on_rotation_angle_changed)
        rot_layout.addWidget(self.rotation_scale)
        self.rot_value_label = QLabel(str(self.rotation_angle))
        rot_layout.addWidget(self.rot_value_label)
        self.expert_layout.addLayout(rot_layout)

        # Transparency
        trans_layout = QHBoxLayout()
        trans_layout.addWidget(QLabel(_("Transparency (%)")))
        self.transparency_scale = QSlider(Qt.Orientation.Horizontal)
        self.transparency_scale.setRange(0, 100)
        self.transparency_scale.setValue(self.font_transparency)
        self.transparency_scale.valueChanged.connect(self.on_transparency_changed)
        trans_layout.addWidget(self.transparency_scale)
        self.trans_value_label = QLabel(str(self.font_transparency))
        trans_layout.addWidget(self.trans_value_label)
        self.expert_layout.addLayout(trans_layout)

        # Density
        dens_layout = QHBoxLayout()
        dens_layout.addWidget(QLabel(_("Density (%)")))
        self.density_scale = QSlider(Qt.Orientation.Horizontal)
        self.density_scale.setRange(1, 100)
        self.density_scale.setValue(self.fili_density)
        self.density_scale.valueChanged.connect(self.on_rotation_density_changed)
        dens_layout.addWidget(self.density_scale)
        self.dens_value_label = QLabel(str(self.fili_density))
        dens_layout.addWidget(self.dens_value_label)
        self.expert_layout.addLayout(dens_layout)

        # Color
        color_layout = QHBoxLayout()
        self.random_color_check = QCheckBox(_("Random Colors"))
        self.random_color_check.setChecked(True)
        self.random_color_check.toggled.connect(self.on_random_color_toggled)
        color_layout.addWidget(self.random_color_check)
        self.color_btn = QPushButton("")
        self.color_btn.setStyleSheet("background-color: green")
        self.color_btn.setEnabled(False)
        self.color_btn.clicked.connect(self.on_color_button_set)
        color_layout.addWidget(self.color_btn)
        self.expert_layout.addLayout(color_layout)

        # Filename Prefix
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel(_("Filename Prefix")))
        self.prefix_entry = QLineEdit()
        prefix_layout.addWidget(self.prefix_entry)
        self.expert_layout.addLayout(prefix_layout)

        # Date Check
        self.date_check = QCheckBox(_("Include Date + Hour"))
        self.date_check.setChecked(True)
        self.expert_layout.addWidget(self.date_check)

        # Resize
        resize_layout = QHBoxLayout()
        resize_layout.addWidget(QLabel(_("Resize to")))
        self.resize_combo = QComboBox()
        self.resize_combo.addItems(
            ["None", "320", "640", "800", "1024", "1280", "1600", "2048"]
        )
        self.resize_combo.currentTextChanged.connect(self.on_resize_changed)
        resize_layout.addWidget(self.resize_combo)
        self.expert_layout.addLayout(resize_layout)

        # PDF / Compression
        pdf_layout = QHBoxLayout()
        self.pdf_check = QCheckBox(_("PDF"))
        self.pdf_check.toggled.connect(self.on_pdf_toggled)
        pdf_layout.addWidget(self.pdf_check)

        self.comp_label = QLabel(_("JPEG (%)"))
        pdf_layout.addWidget(self.comp_label)
        self.compression_scale = QSlider(Qt.Orientation.Horizontal)
        self.compression_scale.setRange(0, 100)
        self.compression_scale.setValue(self.compression_rate)
        self.compression_scale.valueChanged.connect(self.on_compression_changed)
        pdf_layout.addWidget(self.compression_scale)
        self.comp_val_label = QLabel(str(self.compression_rate))
        pdf_layout.addWidget(self.comp_val_label)

        self.expert_layout.addLayout(pdf_layout)

        self.main_layout.addWidget(self.expert_group)
        self.expert_group.setVisible(False)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton(_("Preview"))
        self.preview_btn.clicked.connect(self.on_preview_clicked)
        btn_layout.addWidget(self.preview_btn)

        self.apply_btn = QPushButton(_("Add Watermark"))
        self.apply_btn.clicked.connect(self.on_add_watermark_clicked)
        btn_layout.addWidget(self.apply_btn)

        self.main_layout.addLayout(btn_layout)

    def on_expert_toggle(self, checked):
        self.expert_group.setVisible(checked)
        self.resize(self.width(), self.minimumSizeHint().height())

    def about_dialog(self):
        QMessageBox.about(
            self,
            _("About Watermark App"),
            _(
                "This app add a Watermark to images or PDF\n"
                "Open Source Project\nLicence GPL2\n\n"
                "https://github.com/aginies/watermark"
            ),
        )

    def on_files_clicked(self):
        files, _filter = QFileDialog.getOpenFileNames(
            self,
            _("Please choose files"),
            "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp *.pdf);;PDF Files (*.pdf);;All Files (*)",
        )
        if files:
            self.selected_files_path = files
            self.update_file_button_text()
            if any(f.lower().endswith(".pdf") for f in files):
                self.pdf_check.setChecked(True)

    def update_file_button_text(self):
        count = len(self.selected_files_path)
        if count > 3:
            text = "\n".join(os.path.basename(p) for p in self.selected_files_path[:3])
            text += f"\n... and {count - 3} more files."
        else:
            text = "\n".join(os.path.basename(p) for p in self.selected_files_path)
        self.files_label.setText(text)

    def on_output_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, _("Select Output Folder"))
        if folder:
            self.output_folder_path = folder
            self.output_label.setText(folder)

    def on_rotation_angle_changed(self, value):
        self.rotation_angle = value
        self.rot_value_label.setText(str(value))

    def on_transparency_changed(self, value):
        self.font_transparency = value
        self.trans_value_label.setText(str(value))

    def on_rotation_density_changed(self, value):
        self.fili_density = value
        self.dens_value_label.setText(str(value))

    def on_random_color_toggled(self, checked):
        self.color_btn.setEnabled(not checked)
        self.font_color_choosen = not checked

    def on_color_button_set(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.font_color = color.getRgb()  # Returns (r, g, b, a)
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")

    def on_resize_changed(self, text):
        self.selected_resize = text

    def on_compression_changed(self, value):
        self.compression_rate = value
        self.comp_val_label.setText(str(value))

    def on_pdf_toggled(self, checked):
        self.pdf_choosen = checked
        self.compression_scale.setEnabled(not checked)
        self.resize_combo.setEnabled(not checked)

    def check_if_pdf(self, file_path_str: str) -> bool:
        return file_path_str.lower().endswith(".pdf")

    def set_default_font(self):
        if platform.system() == "Windows":
            self.font_base_name = "arial.ttf"
            self.font_chooser_btn.setText("Arial")
        else:
            # Default Linux
            self.font_base_name = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            # Fallback if specific file not found, try to find one
            if not os.path.exists(str(self.font_base_name)):
                if self.ALL_LINUX_TTF_FONT_DATA:
                    self.font_base_name = self.ALL_LINUX_TTF_FONT_DATA[0]["file"]
            self.font_chooser_btn.setText(os.path.basename(str(self.font_base_name)))

    def on_font_selected(self):
        # QT Font Dialog
        from PyQt6.QtWidgets import QFontDialog

        ok, font = QFontDialog.getFont(QFont("Arial", 12), self)
        if ok:
            font_family = font.family()
            font_style = font.styleName()
            self.font_size = font.pointSize()

            # Find the actual TTF file
            font_path = self.find_font_file(font_family, font_style)

            if font_path:
                self.font_base_name = font_path
                self.font_chooser_btn.setText(f"{font_family} {self.font_size}")
                print(f"Selected Font Path: {font_path}")
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    _("Could not find the font file on disk. Using default."),
                )

    def find_font_file(self, family, style=""):
        if platform.system() == "Windows":
            return self.find_font_file_windows(family)
        return self.find_font_file_unix(family, style)

    def find_font_file_windows(self, family):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
            )
            for i in range(winreg.QueryInfoKey(key)[1]):
                value_name, value_data, _ = winreg.EnumValue(key, i)
                if family.lower() in value_name.lower():
                    # Handle basic path or registry value
                    if os.path.isabs(value_data):
                        return value_data
                    return os.path.join(os.environ["WINDIR"], "Fonts", value_data)
        except Exception as e:
            print(f"Windows Font Error: {e}")
        return None

    def find_font_file_unix(self, family, style):
        # Basic matching against self.ALL_LINUX_TTF_FONT_DATA
        # Prioritize exact match
        for font in self.ALL_LINUX_TTF_FONT_DATA:
            if font["family"].lower() == family.lower():
                return font["file"]

        # Fuzzy match
        for font in self.ALL_LINUX_TTF_FONT_DATA:
            if family.lower() in font["family"].lower():
                return font["file"]
        return None

    def get_current_time_ces(self):
        now = time.time()
        # Simple approximation, not handling DST perfectly but matches original
        return time.localtime(now + 3600)

    def on_add_watermark_clicked(self):
        if not self.selected_files_path:
            QMessageBox.warning(self, "Warning", _("Please select an image"))
            return

        watermark_text = self.watermark_entry.text()
        if not watermark_text:
            QMessageBox.warning(self, "Warning", _("Please enter a watermark text"))
            return

        if not self.font_base_name:
            QMessageBox.warning(self, "Warning", _("Please Select a Font"))
            return

        # Output Dir Logic
        if not self.output_folder_path:
            if self.selected_files_path:
                self.default_output_dir = os.path.dirname(self.selected_files_path[0])
            else:
                self.default_output_dir = get_xdg_pictures_dir()
        else:
            self.default_output_dir = self.output_folder_path

        p_dialog = ProgressDialog(
            self, _("Adding Watermark"), len(self.selected_files_path)
        )

        self.all_images = []
        try:
            for ind, image_path in enumerate(self.selected_files_path):
                p_dialog.set_status(f"Processing: {os.path.basename(image_path)}")

                output_file = None
                if self.check_if_pdf(image_path):
                    output_file = self.add_watermark_to_pdf(
                        image_path, self.default_output_dir, watermark_text, p_dialog
                    )
                else:
                    output_file = self.add_watermark_to_image(
                        image_path, self.default_output_dir, watermark_text, p_dialog
                    )

                if output_file:
                    self.all_images.append(output_file)

                p_dialog.update_progress(ind + 1)

            p_dialog.close()

            # Display all results (images and PDFs)
            if self.all_images:
                self.main_display_images(self.all_images)
                self.all_images = []

        except Exception as e:
            print(e)
            QMessageBox.critical(self, "Error", str(e))

    def main_display_images(self, image_paths):
        self.viewer = ImageViewerWindow()
        self.viewer.load_images(image_paths)
        self.viewer.show()

    def create_watermark_layer(
        self, width, height, text, progress_dialog=None, scale_factor=1.0
    ):
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cest_time = self.get_current_time_ces()

        try:
            scaled_font_size = int(self.font_size * scale_factor)
            if scaled_font_size < 1:
                scaled_font_size = 1
            font = ImageFont.truetype(self.font_base_name, scaled_font_size)
        except IOError:
            font = ImageFont.load_default()

        timestamp_str_text = time.strftime("%d %B %Y_%Hh%M", cest_time)
        full_watermark_text = (
            f"{text} {timestamp_str_text}" if self.date_check.isChecked() else text
        )

        dummy_draw = ImageDraw.Draw(layer)
        bbox = dummy_draw.textbbox((0, 0), full_watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        dpi_from_box = self.fili_density
        dpi = (201 - dpi_from_box * 2) * scale_factor
        if dpi < 1:
            dpi = 1
        interval_pixels_y = int(dpi)
        used_positions = set()

        for ydata in range(interval_pixels_y, height, interval_pixels_y):
            if progress_dialog:
                progress_dialog.pulse()
            x_positions = [
                (xdata % width)
                for xdata in range(0, width, int(text_width) if text_width > 0 else 100)
            ]

            for xdata in x_positions:
                if (xdata, ydata) not in used_positions:
                    angle = random.uniform(-self.rotation_angle, self.rotation_angle)
                    transp = int(
                        (100 - self.font_transparency) * 2.55
                    )  # Map 0-100 to 0-255

                    if not self.font_color_choosen:
                        color = (
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                            transp,
                        )
                    else:
                        color = (
                            self.font_color[0],
                            self.font_color[1],
                            self.font_color[2],
                            transp,
                        )

                    # Draw single text to temp image to rotate it
                    # We need a large enough canvas for rotation
                    temp_w = int(text_width * 3)
                    temp_h = int(text_height * 3)
                    temp_image = Image.new("RGBA", (temp_w, temp_h), (0, 0, 0, 0))
                    temp_draw = ImageDraw.Draw(temp_image)
                    # Center text
                    temp_draw.text(
                        ((temp_w - text_width) / 2, (temp_h - text_height) / 2),
                        full_watermark_text,
                        font=font,
                        fill=color,
                    )

                    rotated_text = temp_image.rotate(
                        angle, expand=False, resample=Image.BICUBIC
                    )

                    paste_x = int(xdata - rotated_text.width / 2)
                    paste_y = int(ydata - rotated_text.height / 2)

                    layer.paste(rotated_text, (paste_x, paste_y), mask=rotated_text)
                    used_positions.add((xdata, ydata))
        return layer

    def add_watermark_to_pdf(
        self, pdf_path, decided_output_path, text, progress_dialog=None
    ):
        try:
            # Validate file exists and is readable
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            if not os.access(pdf_path, os.R_OK):
                raise PermissionError(f"Cannot read PDF file: {pdf_path}")

            # Check file size
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                raise ValueError(f"PDF file is empty: {pdf_path}")

            # Convert PDF to images using Poppler
            # DPI 300 is a good balance between quality and processing speed
            if progress_dialog:
                progress_dialog.set_status("Converting PDF pages...")

            try:
                images = convert_from_path(pdf_path, dpi=300)
            except Exception as convert_err:
                raise ValueError(
                    f"Cannot parse PDF file (possibly corrupted or invalid format): {convert_err}"
                )

            # Validate the PDF has pages
            if len(images) == 0:
                raise ValueError("PDF has no pages")

            original_filename = os.path.basename(pdf_path)
            name_without_ext = os.path.splitext(original_filename)[0]

            cest_time = self.get_current_time_ces()
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", cest_time)

            fprefix = self.prefix_entry.text() + "_" if self.prefix_entry.text() else ""

            if self.date_check.isChecked():
                final_filename = (
                    f"{fprefix}{text}_{timestamp_str}_{name_without_ext}.pdf"
                )
            else:
                final_filename = f"{fprefix}{text}_{name_without_ext}.pdf"

            output_path = os.path.join(decided_output_path, final_filename)

            # Create temporary directory for processed images
            temp_img_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
            os.makedirs(temp_img_dir, exist_ok=True)

            watermarked_images = []

            # Process each page
            for i, page_image in enumerate(images):
                if progress_dialog:
                    progress_dialog.set_status(f"Processing page {i + 1}...")

                # Convert PIL Image to RGBA
                page_image = page_image.convert("RGBA")
                width, height = page_image.size

                # Create watermark layer
                watermark_layer = self.create_watermark_layer(
                    width, height, text, progress_dialog
                )

                # Composite watermark onto page
                watermarked_page = Image.alpha_composite(page_image, watermark_layer)

                # Convert back to RGB for PDF (PDF doesn't support transparency in same way)
                watermarked_page_rgb = watermarked_page.convert("RGB")
                watermarked_images.append(watermarked_page_rgb)

            # Create PDF from watermarked images using reportlab
            if progress_dialog:
                progress_dialog.set_status("Creating output PDF...")

            # Use first image to get dimensions
            first_img = watermarked_images[0]
            img_width, img_height = first_img.size
            # Convert pixels to points (72 points = 1 inch, 300 DPI)
            page_width = (img_width / 300.0) * 72
            page_height = (img_height / 300.0) * 72

            c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

            for idx, img in enumerate(watermarked_images):
                if progress_dialog:
                    progress_dialog.set_status(f"Writing page {idx + 1}...")

                # Save image temporarily
                temp_img_path = os.path.join(temp_img_dir, f"page_{idx}.jpg")
                img.save(temp_img_path, "JPEG", quality=95)

                # Draw image on PDF page
                c.drawImage(temp_img_path, 0, 0, width=page_width, height=page_height)
                c.showPage()

            c.save()

            # Cleanup temporary directory
            shutil.rmtree(temp_img_dir)

            return output_path
        except FileNotFoundError as e:
            error_msg = f"File not found: {e}"
            print(f"PDF Error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
            return None
        except PermissionError as e:
            error_msg = f"Permission denied: {e}"
            print(f"PDF Error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
            return None
        except ValueError as e:
            error_msg = str(e)
            print(f"PDF Error: {error_msg}")
            QMessageBox.critical(self, "Error", f"PDF Error: {error_msg}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"PDF Error: {error_msg}")
            QMessageBox.critical(
                self, "Error", f"An error occurred while processing PDF: {e}"
            )
            return None

    def add_watermark_to_image(
        self, image_path, decided_output_path, text, progress_dialog=None
    ):
        try:
            with Image.open(image_path).convert("RGBA") as img:
                if self.resize_combo.currentText() != "None":
                    target_w = int(self.resize_combo.currentText())
                    if img.width > target_w:
                        ratio = target_w / float(img.width)
                        new_h = int(img.height * ratio)
                        img = img.resize((target_w, new_h), Image.LANCZOS)

                layer = self.create_watermark_layer(
                    img.width, img.height, text, progress_dialog
                )
                img.alpha_composite(layer)

                cest_time = self.get_current_time_ces()
                timestamp_str = time.strftime("%Y%m%d_%H%M%S", cest_time)
                name_without_ext = os.path.splitext(os.path.basename(image_path))[0]

                fprefix = (
                    self.prefix_entry.text() + "_" if self.prefix_entry.text() else ""
                )

                if self.date_check.isChecked():
                    fname = f"{fprefix}{text}_{timestamp_str}_{name_without_ext}"
                else:
                    fname = f"{fprefix}{text}_{name_without_ext}"

                full_path = os.path.join(decided_output_path, fname)

                if self.pdf_choosen:
                    out = full_path + ".pdf"
                    img.convert("RGB").save(out, "PDF")
                else:
                    out = full_path + ".jpg"
                    img.convert("RGB").save(out, "JPEG", quality=self.compression_rate)
                return out
        except Exception as e:
            print(f"Image Error: {e}")
            return None

    def on_preview_clicked(self):
        if not self.selected_files_path:
            QMessageBox.warning(self, "Warning", _("Please select an image first"))
            return

        file_path = self.selected_files_path[0]

        try:
            PREVIEW_MAX = 800

            # Handle PDF files
            if self.check_if_pdf(file_path):
                # Convert first page of PDF to image for preview
                try:
                    images = convert_from_path(
                        file_path, dpi=150, first_page=1, last_page=1
                    )
                    if images:
                        img = images[0].convert("RGBA")
                    else:
                        raise ValueError("Could not render PDF page")
                except Exception as pdf_err:
                    QMessageBox.warning(
                        self, "Warning", f"Could not preview PDF: {pdf_err}"
                    )
                    return
            else:
                # Handle regular image files
                img = Image.open(file_path).convert("RGBA")

            width, height = img.size
            scale = 1.0
            if max(width, height) > PREVIEW_MAX:
                scale = PREVIEW_MAX / max(width, height)
                img = img.resize(
                    (int(width * scale), int(height * scale)), Image.LANCZOS
                )

            text = self.watermark_entry.text() or "Preview"
            layer = self.create_watermark_layer(
                img.width, img.height, text, scale_factor=scale
            )
            img.alpha_composite(layer)

            temp_dir = os.path.join(tempfile.gettempdir(), "watermark_app")
            os.makedirs(temp_dir, exist_ok=True)
            preview_path = os.path.join(temp_dir, "preview.jpg")
            img.convert("RGB").save(preview_path, "JPEG")

            if not self.preview_window:
                self.preview_window = ImageViewerWindow()
            self.preview_window.load_images([preview_path])
            self.preview_window.show()

        except Exception as e:
            QMessageBox.critical(self, "Preview Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec())
