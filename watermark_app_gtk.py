#!/usr/bin/python3
# antoine@ginies.org
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
import PyPDF2
import gi

if platform.system() == 'Windows':
    import winreg
    if getattr(sys, 'frozen', False):
        import pyi_splash

from PIL import Image, ImageDraw, ImageFont
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, Gio, Pango, GLib, Gdk

def is_running_under_flatpak():
    return 'FLATPAK_ID' in os.environ

if platform.system() == 'Windows':
    key_path = r"Control Panel\International"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        locale_name, reg_type = winreg.QueryValueEx(key, "LocaleName")
        lang_code = locale_name.split('-')[0].lower()
        print(f"Windows: Detected language from registry: {lang_code} (full tag: {locale_name})")
        ldir = sys._MEIPASS + "/share/locale"
elif is_running_under_flatpak():
    ldir = "/app/share/locale"
else:
    if not os.path.exists("locale"):
        # Installed on the system
        ldir = "/usr/share/locale"
    else:
        # Devel version from git
        ldir = "locale"

if platform.system() == 'Windows':
    # For Windows operating system do the translation based on the system registry
    trans = gettext.translation("watermark_app_gtk", ldir, languages=[lang_code], fallback=True)
    trans.install()
else:
    gettext.install('watermark_app_gtk', localedir=ldir)

def get_xdg_pictures_dir():
    """
    Returns the path to the user's XDG Pictures directory.
    This works correctly within a Flatpak with --filesystem=xdg-pictures
    """
    try:
        result = subprocess.run(
            ["xdg-user-dir", "PICTURES"],
            capture_output=True,
            text=True,
            check=True
        )
        path = result.stdout.strip()
        if path:
            pictures_dir = pathlib.Path(path)
            if pictures_dir.is_absolute():
                return pictures_dir
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

class ProgressDialog(Gtk.Dialog):
    def __init__(self, parent, title, max_value):
        Gtk.Dialog.__init__(self, title, parent, 0)
        self.set_default_size(300, 100)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        text_p = _("Processing...")
        self.progress.set_text(text_p)
        self.progress.set_fraction(0.0)
        self.label = Gtk.Label(label=text_p)
        box = self.get_content_area()
        box.add(self.progress)
        box.add(self.label)
        self.show_all()
        self.max_value = max_value

    def update_progress(self, value):
        self.current_value = value
        fraction = self.current_value / self.max_value
        self.progress.set_fraction(fraction)
        self.progress.set_text(f"{self.current_value}/{self.max_value}")
        while Gtk.events_pending():
            Gtk.main_iteration()

    def set_status(self, text):
        self.label.set_text(text)
        while Gtk.events_pending():
            Gtk.main_iteration()

    def pulse(self):
        self.progress.pulse()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def close(self):
        self.destroy()

class WarningDialog:
    def __init__(self, title=None, message="", parent=None):
        self.title = title or "Warning"
        self.message = message
        self.parent = parent
        self.dialog = None

    def show(self):
        """ Create the warning dialog if it doesn't exist yet"""
        if not self.dialog:
            self.dialog = Gtk.MessageDialog(
                transient_for=self.parent,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=self.title
            )
            self.dialog.format_secondary_text(self.message)
            self.dialog.set_default_size(400, 200)

        # Show the dialog and wait for response
        response = self.dialog.run()

        if response == Gtk.ResponseType.OK:
            self.hide()

    def hide(self):
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None

class ImageViewerWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Image Viewer")
        self.set_default_size(800, 600)
        self.image_widget = None

        # Create a vertical box to hold widgets
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.vbox)

        # Create a label for displaying the file path
        self.file_label = Gtk.Label()
        self.vbox.pack_start(self.file_label, False, False, 0)

        # Initialize image_label as None (will be created when an image is loaded)
        self.image_label = None

        # Track images and current index
        self.images = []
        self.current_index = -1

        # Create a horizontal box for navigation controls
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.vbox.pack_start(self.hbox, False, False, 0)

        # Previous button
        self.prev_button = Gtk.Button(label=_("Previous"))
        self.prev_button.connect("clicked", self.on_previous_clicked)
        self.hbox.pack_start(self.prev_button, True, True, 6)

        # Index label
        self.index_label = Gtk.Label()
        self.hbox.pack_start(self.index_label, False, False, 6)

        # Next button
        self.next_button = Gtk.Button(label=_("Next"))
        self.next_button.connect("clicked", self.on_next_clicked)
        self.hbox.pack_start(self.next_button, True, True, 6)

    def load_images(self, image_paths):
        """Load a list of images to view"""
        self.images = image_paths
        self.current_index = 0 if len(image_paths) > 0 else -1

        # Update buttons state and index label
        self.update_buttons_state()
        self.update_index_label()

        # Display the first image if available
        if len(self.images) > 0:
            self.display_single_image(self.images[self.current_index])

    def display_single_image(self, image_path):
        """Display a single image in the window"""
        # Load the image using GdkPixbuf
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        except GdkPixbuf.PixbufError as err:
            print(f"Error loading image {image_path}: {err}")
            return

        window_width, window_height = self.get_size()
        img_width = pixbuf.get_width()
        img_height = pixbuf.get_height()
        width_ratio = window_width / img_width
        height_ratio = window_height / img_height
        scale_factor = min(width_ratio, height_ratio)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.HYPER)

        if hasattr(self, 'image_widget') and self.image_widget is not None:
            # Remove the old image widget from its container
            self.vbox.remove(self.image_widget)
            self.image_widget = None

        if hasattr(self, 'image_label') and self.image_label is not None:
            # Remove the old image label from its container
            self.vbox.remove(self.image_label)
            self.image_label = None

        # Create a new GTK Image widget with the scaled pixbuf
        self.image_widget = Gtk.EventBox()
        self.image_label = Gtk.Image.new_from_pixbuf(scaled_pixbuf)

        # Add image label to event box (to catch events on it)
        self.image_widget.add(self.image_label)

        # Connect right-click event to show context menu
        self.image_widget.connect("button-press-event", self.on_image_right_click)

        self.file_label.set_text(image_path)
        self.vbox.pack_start(self.image_widget, True, True, 0)
        self.show_all()

    def update_buttons_state(self):
        """Enable or disable navigation buttons based on current index"""
        if self.current_index == 0:
            self.prev_button.set_sensitive(False)
        else:
            self.prev_button.set_sensitive(True)

        if self.current_index == len(self.images) - 1:
            self.next_button.set_sensitive(False)
        else:
            self.next_button.set_sensitive(True)

    def update_index_label(self):
        """Update the index label to show current image number and total images"""
        total_images = len(self.images)
        if total_images > 0:
            self.index_label.set_text(f"{self.current_index + 1}/{total_images}")
        else:
            self.index_label.set_text("0/0")

    def on_previous_clicked(self, widget):
        """Handle Previous button click"""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_single_image(self.images[self.current_index])
            self.update_buttons_state()
            self.update_index_label()

    def on_next_clicked(self, widget):
        """Handle Next button click"""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.display_single_image(self.images[self.current_index])
            self.update_buttons_state()
            self.update_index_label()

    def on_image_right_click(self, widget, event):
        """Handle right-click event on the image"""
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            # Create context menu
            menu = Gtk.Menu()

            # Add "Save" option to menu
            save_item = Gtk.MenuItem(label="Save Image as")
            save_item.connect("activate", self.on_save_activated)
            menu.append(save_item)

            # Show the menu
            menu.show_all()
            menu.popup_at_pointer(event)

    def on_save_activated(self, widget):
        """Handle the Save option selection"""
        current_image_path = self.images[self.current_index]
        dialog = Gtk.FileChooserDialog(
            title="Save Image As",
            action=Gtk.FileChooserAction.SAVE,
        )

        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Save", Gtk.ResponseType.ACCEPT)

        # Set the default file name to the current image name
        dialog.set_current_name(Gio.file_new_for_path(current_image_path).get_basename())
        dialog.set_current_folder(os.path.dirname(current_image_path))
        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                # Copy the current image to the selected location
                source_file = Gio.File.new_for_path(current_image_path)
                destination_file = Gio.File.new_for_path(dialog.get_filename())
                source_file.copy(
                    destination_file,
                    Gio.FileCopyFlags.OVERWRITE,
                    None,
                    None
                )
                print("Image saved to:", dialog.get_filename())
            except Exception as err:
                print(f"Error saving image: {err}")

        dialog.destroy()

class WatermarkApp(Gtk.Window):
    """  Main app"""
    def __init__(self):
        Gtk.Window.__init__(self, title=_("Watermark App"))
        self.set_default_size(450, 100)
        self.set_size_request(450, 100)
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
        self.default_font_description = Pango.FontDescription("Sans 32")
        self.font_color = Gdk.RGBA()
        self.font_color_choosen = False
        self.font_transparency = 25
        self.pdf_choosen = False
        self.init_real_size = 32
        self.real_fsize = None
        self.pdf_original_dirname = None
        self.preview_window = None
        #self.pdf_needs_merge = False

        # Create main vertical box container
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.add(self.vbox)

        # Setup menu bar
        menubar = Gtk.MenuBar()
        menubar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        menubar_box.pack_start(menubar, False, False, 0)
        self.vbox.pack_start(menubar_box, False, False, 0)

        # Create a "Pref" menu item
        pref_menu_item = Gtk.MenuItem(label=_("Preferences"))
        menubar.append(pref_menu_item)
        pref_menu = Gtk.Menu()

        # Create a check menu item to toggle expert options
        self.expert_options_check = Gtk.CheckMenuItem(label=_("Show Expert Options"))
        self.expert_options_check.connect("toggled", self.on_expert_toggle)
        self.expert_options_check.set_active(False)
        pref_menu.append(self.expert_options_check)

        # Create a check menu item to toggle Auto save Images options
        #self.autosave_options_check = Gtk.CheckMenuItem(label="Auto Save Images")
        #self.autosave_options_check.set_active(True)
        #pref_menu.append(self.autosave_options_check)
        pref_menu_item.set_submenu(pref_menu)

        # Create "Help" menu with cascading items
        help_menu_item = Gtk.MenuItem(label=_("Help"))
        help_menu = Gtk.Menu()
        help_menu_item.set_submenu(help_menu)
        menubar.append(help_menu_item)

        # Add "Help on Filigrane App" to the About menu
        help_filigrane_menu_item = Gtk.MenuItem(label=_("Online Help"))
        help_filigrane_menu_item.connect("activate", self.help_dialog)
        help_menu.append(help_filigrane_menu_item)

        # Create "About" menu with cascading items
        about_menu_item = Gtk.MenuItem(label=_("About App"))
        about_menu = Gtk.Menu()
        about_menu_item.set_submenu(about_menu)
        menubar.append(about_menu_item)

        # Add "About Filigrane App" to the About menu
        about_filigrane_menu_item = Gtk.MenuItem(label=_("About Watermark App"))
        about_filigrane_menu_item.connect("activate", self.about_dialog)
        about_menu.append(about_filigrane_menu_item)

        button_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        # File selection horizontal box (label + file chooser button)
        file_hbox = Gtk.Box(spacing=3)
        file_label_text = _("Select Image or PDF File(s)")
        file_label = Gtk.Label(label=file_label_text, halign=Gtk.Align.START)
        self.file_chooser_button = Gtk.Button(label=_("Choose Files"))
        self.file_chooser_button.connect("clicked", self.on_files_clicked)
        button_size_group.add_widget(self.file_chooser_button)
        file_hbox.pack_start(file_label, False, False, 12)
        file_hbox.pack_end(self.file_chooser_button, False, False, 12)
        self.vbox.pack_start(file_hbox, False, False, 3)

        self.files_selected_hbox = Gtk.Box(spacing=3)
        self.files_label = Gtk.Label()
        self.files_selected_hbox.pack_start(self.files_label, False, False, 12)
        self.vbox.pack_start(self.files_selected_hbox, False, False, 3)

        # Watermark text horizontal box (label + entry)
        watermark_hbox = Gtk.Box(spacing=3)
        watermark_text = _("Watermark Text")
        watermark_label = Gtk.Label(label=watermark_text)
        self.watermark_entry = Gtk.Entry()
        self.watermark_entry.set_placeholder_text(watermark_text)
        button_size_group.add_widget(self.watermark_entry)
        watermark_hbox.pack_start(watermark_label, False, False, 12)
        watermark_hbox.pack_end(self.watermark_entry, False, False, 12)
        self.vbox.pack_start(watermark_hbox, False, False, 3)

	# Font Chooser
        font_chooser_hbox = Gtk.Box(spacing=3)
        font_chooser_label = Gtk.Label(label=_("TTF Font chooser"))
        self.font_chooser_button = Gtk.Button()
        self.font_chooser_button.set_label(_("No font selected"))
        self.font_chooser_button.connect("clicked", self.on_font_selected)
        button_size_group.add_widget(self.font_chooser_button)
        font_chooser_hbox.pack_start(font_chooser_label, False, False, 12)
        font_chooser_hbox.pack_end(self.font_chooser_button, False, False, 12)
        self.vbox.pack_start(font_chooser_hbox, False, False, 3)

        # Output path selection horizontal box
        output_hbox = Gtk.Box(spacing=3)
        output_text = _("Select Output Folder")
        output_label = Gtk.Label(label=output_text)
        self.output_filechooser_button = Gtk.FileChooserButton()
        self.output_filechooser_button.set_title(output_text)
        self.output_filechooser_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        self.output_filechooser_button.set_current_folder(self.output_folder_path)
        button_size_group.add_widget(self.output_filechooser_button)
        output_hbox.pack_start(output_label, False, False, 12)
        output_hbox.pack_end(self.output_filechooser_button, False, False, 12)
        if is_running_under_flatpak():
            print("Runing under a flatpak sandbox environement")
            with open('DONT_SAVE_HERE', 'w') as f:
                f.write('This is a reminder not to save files here.')
        else:
            self.vbox.pack_start(output_hbox, False, False, 3)

        # Expert options section
        expert_text = _("Expert Options")
        self.expert_options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.expert_options_frame = Gtk.Frame(label="<b> "+expert_text+"</b>")
        self.expert_options_frame.get_label_widget().set_use_markup(True)
        self.expert_options_frame.set_margin_start(12)
        self.expert_options_frame.set_margin_end(12)
        #self.expert_options_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.expert_options_frame.add(self.expert_options_box)

        # Rotation angle
        rotation_hbox = Gtk.Box(spacing=3)
        rotation_label = Gtk.Label(label=_("Angle (degrees)"))
        adjustment_rotation = Gtk.Adjustment(value=self.rotation_angle,
                                             lower=0, upper=90, step_increment=1, page_increment=4)
        self.rotation_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                        adjustment=adjustment_rotation)
        self.rotation_scale.set_digits(0)
        self.rotation_scale.set_tooltip_text(_("Watermark Angle in the image (positive and negative)"))
        self.rotation_scale.connect("value-changed", self.on_rotation_angle_changed)
        button_size_group.add_widget(self.rotation_scale)
        rotation_hbox.pack_start(rotation_label, False, False, 12)
        rotation_hbox.pack_end(self.rotation_scale, False, False, 12)
        self.expert_options_box.pack_start(rotation_hbox, False, False, 3)

        # Font Transparency
        transparency_hbox = Gtk.Box(spacing=3)
        transparency_label = Gtk.Label(label=_("Transparency (%)"))
        adjustment_transparency = Gtk.Adjustment(value=self.font_transparency, lower=0,
                                                 upper=100, step_increment=1, page_increment=10)
        self.transparency_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                            adjustment=adjustment_transparency)
        self.transparency_scale.set_digits(0)
        self.transparency_scale.set_inverted(False)
        self.transparency_scale.set_tooltip_markup(_("Watermark transparency in the image\n<b>* 0:</b> No transparency\n<b>* 100:</b> Invisible"))
        self.transparency_scale.connect("value-changed", self.on_transparency_changed)
        button_size_group.add_widget(self.transparency_scale)
        transparency_hbox.pack_start(transparency_label, False, False, 12)
        transparency_hbox.pack_end(self.transparency_scale, False, False, 12)
        self.expert_options_box.pack_start(transparency_hbox, False, False, 3)

        # Font density
        density_hbox = Gtk.Box(spacing=3)
        density_label = Gtk.Label(label=_("Density (%)"))
        adjustment_density = Gtk.Adjustment(value=self.fili_density, lower=1,
                                            upper=100, step_increment=1, page_increment=10)
        self.text_density_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                            adjustment=adjustment_density)
        self.text_density_scale.set_digits(0)
        self.text_density_scale.set_tooltip_markup(_("How many watermark you want\n<b>* 0:</b> None\n<b>* 100:</b> Fill the image"))
        self.text_density_scale.set_inverted(False)
        self.text_density_scale.connect("value-changed", self.on_rotation_density_changed)
        button_size_group.add_widget(self.text_density_scale)
        density_hbox.pack_start(density_label, False, False, 12)
        density_hbox.pack_end(self.text_density_scale, False, False, 12)
        self.expert_options_box.pack_start(density_hbox, False, False, 3)

        # Font color chooser
        color_hbox = Gtk.Box(spacing=3)
        self.color_button = Gtk.ColorButton.new_with_rgba(Gdk.RGBA(0, 1, 0, 1))
        self.font_color = self.color_button.get_rgba()
        self.color_button.connect("color-set", self.on_color_button_set)
        self.random_color_check = Gtk.CheckButton(label=_("Random Colors"))
        self.random_color_check.connect("toggled", self.on_random_color_toggled)
        self.random_color_check.set_active(True)
        button_size_group.add_widget(self.color_button)
        color_hbox.pack_start(self.random_color_check, False, False, 12)
        color_hbox.pack_end(self.color_button, False, False, 12)
        self.expert_options_box.pack_start(color_hbox, False, False, 3)

        # Filename Prefix option
        prefix_filename_hbox = Gtk.Box(spacing=3)
        prefix_text = _("Filename Prefix")
        prefix_filename_label = Gtk.Label(label=prefix_text)
        self.watermark_prefix = Gtk.Entry()
        self.watermark_prefix.set_tooltip_markup(_("You can add an <b>Extra Prefix</b> to the final filename"))
        self.watermark_prefix.set_placeholder_text(prefix_text)
        button_size_group.add_widget(self.watermark_prefix)
        prefix_filename_hbox.pack_start(prefix_filename_label, False, False, 12)
        prefix_filename_hbox.pack_end(self.watermark_prefix, False, False, 12)
        self.expert_options_box.pack_start(prefix_filename_hbox, False, False, 3)

        # Filename Date option
        date_filename_hbox = Gtk.Box(spacing=3)
        date_filename_label = Gtk.Label(label=_("Include Date + Hour"))
        self.date_filename_check = Gtk.CheckButton()
        self.date_filename_check.set_active(True)
        self.date_filename_check.set_tooltip_text(_("Add the Date and the Hour in the watermark, include that into the filename"))
        button_size_group.add_widget(self.date_filename_check)
        date_filename_hbox.pack_start(date_filename_label, False, False, 12)
        date_filename_hbox.pack_end(self.date_filename_check, False, False, 12)
        self.expert_options_box.pack_start(date_filename_hbox, False, False, 3)

        # Select the size for resize the image
        self.resize_hbox = Gtk.Box(spacing=3)
        resize_label = Gtk.Label(label=_("Resize to"))
        self.list_size = Gtk.ComboBoxText()
        self.list_size.set_tooltip_markup(_("You can <b>resize</b> the original image to another size.\nThis option is not available if you choose PDF output format."))
        elements = ["None", "320", "640", "800", "1024", "1280", "1600", "2048",]
        for text in elements:
            self.list_size.append_text(text)
        self.list_size.set_active(0)
        self.list_size.connect("changed", self.on_resize_changed)
        button_size_group.add_widget(self.list_size)
        self.resize_hbox.pack_start(resize_label, False, False, 12)
        self.resize_hbox.pack_end(self.list_size, False, False, 12)
        self.expert_options_box.pack_start(self.resize_hbox, False, False, 3)

	# Output PDF or JPEG Compression level
        output_hbox = Gtk.Box(spacing=3)
        self.compression_rate_label = Gtk.Label(label=_("JPEG (%)"))
        adjustment_compression = Gtk.Adjustment(value=self.compression_rate,
                                                lower=0, upper=100, step_increment=1,
                                                page_increment=10)
        self.compression_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                           adjustment=adjustment_compression)
        self.compression_scale.set_digits(0)
        self.compression_scale.set_tooltip_markup(_("Compression ratio of the generated JPEG Image(s)\n<b>* 0:</b> None\n<b>* 100:</b> Full compression"))
        self.compression_scale.connect("value-changed", self.on_compression_changed)
        button_size_group.add_widget(self.compression_scale)
        self.pdf_check = Gtk.CheckButton(label=_("PDF"))
        self.pdf_check.set_tooltip_markup(_("Save the image into a <b>PDF</b> format instead of JPEG.\nThere is <b>No view</b> of the watermarked file <b>in PDF</b> format."))
        self.pdf_check.connect("toggled", self.on_pdf_toggled)
        self.pdf_check.set_active(False)
        self.compression_scale.set_sensitive(True)
        self.compression_rate_label.set_sensitive(True)
        output_hbox.pack_start(self.pdf_check, False, False, 12)
        output_hbox.pack_end(self.compression_scale, False, False, 12)
        output_hbox.pack_end(self.compression_rate_label, False, False, 12)
        self.expert_options_box.pack_start(output_hbox, False, False, 3)

        #self.vbox.pack_start(self.expert_options_box, False, False, 12)
        #self.expert_options_box.hide()

        # Add watermark button horizontal box
        self.watermarkb_hbox = Gtk.Box(spacing=3)
        add_watermark_button = Gtk.Button(label=_("Add Watermark"))
        add_watermark_button.set_hexpand(True)
        add_watermark_button.connect("clicked", self.on_add_watermark_clicked)

        self.preview_button = Gtk.Button(label=_("Preview"))
        self.preview_button.connect("clicked", self.on_preview_clicked)

        self.watermarkb_hbox.pack_start(self.preview_button, False, False, 12)
        self.watermarkb_hbox.pack_start(add_watermark_button, True, True, 12)
        self.vbox.pack_start(self.watermarkb_hbox, False, False, 3)

        # Se default Font
        if platform.system() != 'Windows':
             #print("populating ALL_LINUX_TTF_FONT_DATA")
            self.ALL_LINUX_TTF_FONT_DATA = self.get_ttf_fonts()
        self.set_default_font()

        if platform.system() == 'Windows':
            if getattr(sys, 'frozen', False) and 'pyi_splash' in sys.modules:
                if pyi_splash.is_alive():
                    pyi_splash.close()

    def check_if_pdf(self, file_path_str: str) -> bool:
        """ Checks if a file path has a '.pdf' extension using pathlib.Path.suffix."""
        file_path = pathlib.Path(file_path_str)
        return file_path.suffix.lower() == '.pdf'



    def on_pdf_toggled(self, button):
        if button.get_active():
            self.compression_scale.set_sensitive(False)
            self.compression_rate_label.set_sensitive(False)
            self.resize_hbox.set_sensitive(False)
            self.pdf_choosen = True
        else:
            self.compression_scale.set_sensitive(True)
            self.compression_rate_label.set_sensitive(True)
            self.resize_hbox.set_sensitive(True)
            self.pdf_choosen = False

    def on_random_color_toggled(self, button):
        if button.get_active():
            self.color_button.set_sensitive(False)
            self.font_color_choosen = False
        else:
            self.color_button.set_sensitive(True)
            self.font_color_choosen = True

    def on_color_button_set(self, button):
        self.font_color = button.get_rgba()
        print(f"Selected color: {self.font_color.red}, {self.font_color.green}, {self.font_color.blue}, {self.font_color.alpha}")
        self.font_color_choosen = True

    def set_default_font(self):
        if platform.system() == 'Windows':
            self.default_font_description = Pango.FontDescription("Arial 20")
            self.font_base_name = "arial.ttf"
            self.font_chooser_button.set_label("Arial 20")
            print("Default font set to Arial on Windows.")
        else:
            self.default_font_description = Pango.FontDescription("DejaVu Sans 20") #vtks Rude Metal shadow 12") #DejaVu Sans 20")
            font_desc_str = self.default_font_description.to_string()
            font_path = self.find_font_file(self.default_font_description)
            #if is_running_under_flatpak():
            #    # Dont select default font in sanbox env, force user select one
            #    print("Dont select default font in sanbox env, force user select one")
            #    self.font_chooser_button.set_label(_("No font selected"))
            #    return

            if font_path:
                self.font_base_name = font_path.split('.ttf')[0] + '.ttf'
                print(f"Font name: {self.font_base_name}")
                parts_desc = font_desc_str.split()
                self.font_size = int(parts_desc[-1]) if parts_desc else None
                temp_font = self.default_font_description
                temp_font.set_size(12* Pango.SCALE)
                temp_font_desc_str = temp_font.to_string()
                label = self.font_chooser_button.get_child()
                label.set_text(font_desc_str)
                label.override_font(temp_font)
                # Force default font Size to 20
                self.default_font_description.set_size(self.init_real_size * Pango.SCALE)
                #self.font_chooser_button.set_label(font_desc_str)
            else:
                print("Could not find the default font file.")
                warning_dialog = WarningDialog(
                    title="Error",
                    message=_("Could not find the default font file, choose another one."),
                    )
                warning_dialog.show()

    def get_style_string(self, style):
        """ Return readable style"""
        if style == Pango.Style.NORMAL:
            return "Regular"
        elif style == Pango.Style.ITALIC:
            return "Italic"
        elif style == Pango.Style.OBLIQUE:
            return "Oblique"
        else:
            return "Unknown"

    def get_ttf_fonts(self):
        """ Scans the system for all TTF fonts using the 'fc-list' command-line tool."""
        ttf_fonts_data = []
        if not os.path.exists('/usr/bin/fc-list'):
            print("Warning: 'fc-list' command not found. Font filtering will not work.")
            print("Please install the 'fontconfig' package.")
            return ttf_fonts_data

        try:
            # We ask fc-list for three fields for each font: file, family, and style.
            # The style from fc-list (e.g., "Bold", "Italic") corresponds to Pango's face name.
            command = ['fc-list', '-f', '%{file}|%{family}|%{style}\n']
            output = subprocess.check_output(command).decode('utf-8')
            for line in output.strip().split('\n'):
                try:
                    parts = line.split('|')
                    #print(parts)
                    if len(parts) == 3:
                        filepath, family, style = parts

                    if filepath.lower().endswith('.ttf'):
                        cleaned_family = family.split(',')[0].strip()
                        ttf_fonts_data.append({
                            'file': filepath,
                            'family': cleaned_family,
                            'style': style.strip()
                        })

                except ValueError:
                    continue

        except (subprocess.CalledProcessError, FileNotFoundError) as err:
            print(f"Error executing 'fc-list': {err}")

        return ttf_fonts_data

    def font_filter_func(self, family, face, data):
        """ The filter function passed to the Gtk.FontChooser. """
        family_name = family.get_name()
        face_name = face.get_face_name()
        for font_data in self.ALL_LINUX_TTF_FONT_DATA:
            if font_data['family'] == family_name and font_data['style'] == face_name:
                return True

        return False

    def on_font_selected(self, widget):
        dialog = Gtk.FontChooserDialog(title=_("Choose a TTF Font"), transient_for=self, flags=0)
        if self.real_fsize is not None:
            self.default_font_description.set_size(self.real_fsize)
        dialog.set_font_desc(self.default_font_description)
        if platform.system() != 'Windows':
            if self.ALL_LINUX_TTF_FONT_DATA:
                dialog.set_filter_func(self.font_filter_func, None)
            else:
                print("No TTF fonts found to filter by.")

        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                font_desc = dialog.get_font_desc()
                self.default_font_description = font_desc
                path_desc = "File path not found in our list."
                font_path = self.find_font_file(font_desc)
                self.real_fsize = font_desc.get_size()
                font_desc_str = font_desc.to_string()
                self.font_size = int(font_desc.get_size()/1024)
                print(f"Selected Font is: {font_desc_str}\nFile: {font_path}")

                if font_path:
                    self.font_base_name = font_path
                    # Temp font to display the font in the button
                    temp_font = font_desc
                    # Temp font size will be the same with a smaller size set to 12
                    temp_font.set_size(12* Pango.SCALE)
                    label = self.font_chooser_button.get_child()
                    # use the original font description string, so correct font size
                    label.set_text(font_desc_str)
                    # Display it using the temp font with lower font size (12)
                    label.override_font(temp_font)
                    print("Used for PIL: ", self.font_size)
                    dialog.destroy()
                    return self.font_base_name, self.font_size
                else:
                    print("Could not find the font file.")
                    warning_dialog = WarningDialog(
                        title="Error",
                        message=_("An error occurred, can't find the font path, please choose another one"),
                    )
                    warning_dialog.show()

            elif response == Gtk.ResponseType.CANCEL:
                print("Select font canceled.")
                dialog.destroy()
                return None

    def find_font_file(self, font_desc):
        """
        Try to find the font file for a given Pango font description.
        Uses `fc-list` on Unix-like systems and Windows Registry on Windows.
        """
        if platform.system() == 'Windows':
            return self.find_font_file_windows(font_desc)
        return self.find_font_file_unix(font_desc)

    def find_font_file_windows(self, font_desc):
        """
        Try to find the font file for a given font family on Windows.
        Uses Windows Registry to find installed fonts.
        """
        if font_desc:
            font_family = font_desc.get_family()
        try:
            # Open the Windows Registry key for installed fonts
            registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")

            # Iterate through the registry keys to find the font family
            for i in range(winreg.QueryInfoKey(registry_key)[1]):
                value_name, value_data, _ = winreg.EnumValue(registry_key, i)
                if font_family.lower() in value_name.lower():
                    font_file = value_data
                    font_path = f"C:\\Windows\\Fonts\\{font_file}"
                    return font_path
            return None

        except Exception as err:
            print(f"Error finding font file on Windows: {err}")
            return None

    def find_font_file_unix(self, font_desc):
        """
        Try to find the font file for a given Pango font description.
        Uses `fc-list` command line tool from fontconfig package.
        """
        if font_desc:
            family = font_desc.get_family()
            style = font_desc.get_style()
            style_str = self.get_style_string(style)
            description = font_desc.to_string()

            # List of All font We want, at the end will select the first of the list (should be only one...)
            list_all_font = []
            def find_family(family):
                """ Find all font with correct familly"""
                all_font_family = []
                for font_data in self.ALL_LINUX_TTF_FONT_DATA:
                    if font_data['family'] == family:
                        all_font_family.append(font_data)
                return all_font_family
     
            # List all font font with correct family
            all_font_family_selected = find_family(family)
            list_all_font = all_font_family_selected

            def find_bold_in(list):
                """ Find all font Bold from a list"""
                bold_font_list = []
                non_bold_font_list = []
                for font_data in list:
                    if re.search("Bold", font_data['style']):
                        bold_font_list.append(font_data)
                    else:
                        non_bold_font_list.append(font_data)
                return bold_font_list, non_bold_font_list

            def find_italic_in(list):
                """ Find all font italic from a list"""
                italic_font_list = []
                non_italic_font_list = []
                for font_data in list:
                    if re.search("Italic", font_data['style']):
                        italic_font_list.append(font_data)
                    else:
                        non_italic_font_list.append(font_data)
                return italic_font_list, non_italic_font_list

            bold_font_list, non_bold_font_list = find_bold_in(all_font_family_selected)
            if re.search("Bold", description):
                list_all_font = bold_font_list
            else:
                list_all_font = non_bold_font_list

            italic_font_list, non_italic_font_list = find_italic_in(list_all_font)
            if re.search("Italic", description):
                list_all_font = italic_font_list
            else:
                list_all_font = non_italic_font_list

            if list_all_font:
                font_path = list_all_font[0]['file']
                return font_path
            else:
                print("List empty... so it didnt find the font file!")

    def on_resize_changed(self, combo):
        self.selected_resize = combo.get_active_text()

    def on_rotation_angle_changed(self, widget):
        self.rotation_angle = int(widget.get_value())

    def on_transparency_changed(self, widget):
        self.font_transparency = int(widget.get_value())

    def on_rotation_density_changed(self, widget):
        self.fili_density = int(widget.get_value())

    def on_compression_changed(self, widget):
        self.compression_rate = int(widget.get_value())

    def on_expert_toggle(self, checkmenuitem):
        if self.expert_options_check.get_active():
            self.vbox.remove(self.watermarkb_hbox)
            self.vbox.pack_start(self.expert_options_frame, False, False, 12)
            self.expert_options_frame.show()
            self.vbox.pack_start(self.watermarkb_hbox, False, False, 3)
            self.expert_options_box.show_all()
        else:
            if self.expert_options_box.get_parent() is not None:
                self.expert_options_frame.hide()
                #self.vbox.pack_start(self.watermarkb_hbox, False, False, 3)
                self.vbox.remove(self.expert_options_frame)
                self.resize(210, 110)

    def about_dialog(self, widget):
        """ Create a custom dialog window for the About section with a clickable link"""
        about_window = Gtk.Window(title=_("Watermark App Version 5.0"))
        about_window.set_default_size(400, 200)
        about_window.set_position(Gtk.WindowPosition.CENTER)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        about_window.add(vbox)

        info_text = _(
            "This app add a Watermark to images or PDF\n"
            "Open Source Project\nLicence GPL2"
        )

        label = Gtk.Label(label=info_text)
        vbox.pack_start(label, True, True, 3)

        # Create a clickable hyperlink using GtkLinkButton
        github_link = Gtk.LinkButton.new_with_label("https://github.com/aginies/watermark",
                                                    "https://github.com/aginies/watermark")
        vbox.pack_start(github_link, False, False, 3)

        close_button = Gtk.Button(label=_("Close"))
        close_button.connect("clicked", lambda btn: about_window.destroy())
        vbox.pack_end(close_button, False, False, 3)
        about_window.show_all()

    def help_dialog(self, widget):
        """ Create a custom dialog window for the Help section with a clickable link"""
        help_window = Gtk.Window(title=_("help"))
        help_window.set_default_size(100, 100)
        help_window.set_position(Gtk.WindowPosition.CENTER)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        help_window.add(vbox)

        github_link = Gtk.LinkButton.new_with_label("https://github.com/aginies/watermark/blob/main/README.md",
                                                    "Online information")
        vbox.pack_start(github_link, False, False, 3)
        close_button = Gtk.Button(label=_("Close"))
        close_button.connect("clicked", lambda btn: help_window.destroy())
        vbox.pack_end(close_button, False, False, 3)
        help_window.show_all()        

    def main_display_images(self, image_path):
        app = ImageViewerWindow()
        app.load_images(image_path)

    def add_selection_filters(self):
        filter_img = Gtk.FileFilter()
        filter_img.set_name(_("Image Files"))
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/gif")
        filter_img.add_mime_type("image/bmp")
        filter_img.add_mime_type("image/tiff")
        filter_img.add_mime_type("image/webp")
        filter_img.add_pattern("*.png")
        filter_img.add_pattern("*.jpg")
        filter_img.add_pattern("*.jpeg")
        filter_img.add_pattern("*.gif")
        filter_img.add_pattern("*.bmp")
        filter_img.add_pattern("*.tiff")
        filter_img.add_pattern("*.tif")
        filter_img.add_pattern("*.webp")
        filter_img.add_pattern("*.pdf")
        return filter_img

    def on_files_clicked(self, widget):
        """ Create a file chooser dialog with multiple selection option"""
        dialog = Gtk.FileChooserNative.new(
            title=_("Please choose files"),
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )

        dialog.set_select_multiple(True)

        # Add filters (images and pdf)
        file_filter = self.add_selection_filters()
        print(f"Filter name: {file_filter.get_name()}")
        dialog.add_filter(file_filter)
        dialog.set_filter(file_filter)
        filters = dialog.list_filters()
        for lfil, fil in enumerate(filters):
            print(f"Listed Filter {lfil}: {fil.get_name()}")

        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            file_paths = dialog.get_files()
            self.selected_files_path = [file.get_path() for file in file_paths]
            self.update_file_button_text()
            print("Selected file(s):", self.selected_files_path)
            self.files_selected_hbox.show()
            for file in file_paths:
                print(file.get_path())

            # If we select a PDF, then the output will be automatically a PDF
            if any(self.check_if_pdf(f) for f in self.selected_files_path):
                 self.pdf_check.set_active(True)

        dialog.destroy()

    def update_file_button_text(self):
        how_many_files = len(self.selected_files_path)
        if how_many_files > 3:
            selected_files_str = "\n".join(os.path.basename(path) for path in self.selected_files_path[:3])
            selected_files_str += _(f"\n... and more files selected ({how_many_files}).")
            self.files_label.set_text(_(f"{selected_files_str}"))
        else:
            selected_files_str = "\n".join(os.path.basename(path) for path in self.selected_files_path)
            self.files_label.set_text(_(f"{selected_files_str}"))

    def on_add_watermark_clicked(self, widget):
        if not self.selected_files_path:
            warning_dialog = WarningDialog(
                title="Warning",
                message=_("Please select an image"),
            )
            warning_dialog.show()
            return

        watermark_text = self.watermark_entry.get_text()
        if not watermark_text:
            warning_dialog = WarningDialog(
                title="Warning",
                message=_("Please enter a watermark text"),
            )
            warning_dialog.show()
            return

        if self.font_base_name is None:
            warning_dialog = WarningDialog(
                title="Warning",
                message=_("Please Select a Font"),
            )
            warning_dialog.show()
            return

        if not self.output_folder_path:
            if self.pdf_original_dirname is not None:
                self.default_output_dir = self.pdf_original_dirname
            elif self.selected_files_path:
                self.default_output_dir = os.path.dirname(self.selected_files_path[0])
            else:
                 self.default_output_dir = get_xdg_pictures_dir()

            if is_running_under_flatpak():
                # flatpak cause issue to save files, so forcing it to dir xdg pictures
                self.default_output_dir = get_xdg_pictures_dir()
            if not is_running_under_flatpak():
                self.output_filechooser_button.set_current_folder(self.default_output_dir)
        else:
            self.default_output_dir = self.output_folder_path
            if not is_running_under_flatpak():
                self.output_filechooser_button.set_current_folder(self.output_folder_path)

        p_dialog = ProgressDialog(self, _("Adding Watermark"), len(self.selected_files_path))

        try:
            for ind, image_path in enumerate(self.selected_files_path):
                p_dialog.set_status(_(f"Processing: {os.path.basename(image_path)}"))
                if self.check_if_pdf(image_path):
                    output_file = self.add_watermark_to_pdf(image_path, self.default_output_dir, watermark_text, p_dialog)
                else:
                    output_file = self.add_watermark_to_image(image_path, self.default_output_dir, watermark_text, p_dialog)

                if output_file:
                    print("Success", f"Generated File: {os.path.basename(output_file)}")
                    self.all_images.append(output_file)
                p_dialog.update_progress(ind + 1)

            p_dialog.close()
            # If list contains PDFs show list of files
            # Check if any result is PDF
            has_pdf = any(f.lower().endswith('.pdf') for f in self.all_images)

            if has_pdf:
                # If we have PDFs, we can't display them in the image viewer (simple viewer)
                warning_dialog = WarningDialog(
                    title=_("Success"),
                    message=_(f"Generated file(s):\n{self.all_images}"),
                )
                warning_dialog.show()
                self.all_images = []
                return
            else:
                self.main_display_images(self.all_images)
                self.all_images = []

        except Exception as err:
            print(f"Error processing the image: {err}")
            warning_dialog = WarningDialog(
                title="Error",
                message=_(f"An error occurred during image processing: {err}"),
            )
            warning_dialog.show()

    def on_preview_clicked(self, widget):
        self.generate_preview()

    def on_preview_destroyed(self, widget):
        self.preview_window = None

    def generate_preview(self):
        if not self.selected_files_path:
            warning_dialog = WarningDialog(
               title="Warning",
               message=_("Please select an image first"),
            )
            warning_dialog.show()
            return

        file_path = self.selected_files_path[0]
        if self.check_if_pdf(file_path):
            # PDF preview not supported
            if not self.preview_window:
                warning_dialog = WarningDialog(
                   title="Warning",
                   message=_("Preview not supported for PDF files"),
                )
                warning_dialog.show()
            return

        try:
            # Use a fixed preview max dimension, e.g. 800
            PREVIEW_MAX = 800
            with Image.open(file_path).convert("RGBA") as img:
                width, height = img.size
                scale = 1.0
                if max(width, height) > PREVIEW_MAX:
                    scale = PREVIEW_MAX / max(width, height)
                    new_size = (int(width * scale), int(height * scale))
                    img = img.resize(new_size, Image.LANCZOS)
                else:
                    new_size = (width, height)

                # Prepare text
                watermark_text = self.watermark_entry.get_text()
                if not watermark_text: watermark_text = "Preview"

                # Create layer with scale
                layer = self.create_watermark_layer(img.width, img.height, watermark_text, scale_factor=scale)
                img.alpha_composite(layer)

                # Save to temp
                temp_dir = os.path.join(tempfile.gettempdir(), 'watermark_app')
                os.makedirs(temp_dir, exist_ok=True)
                self.preview_temp_path = os.path.join(temp_dir, 'preview.jpg')
                img.convert("RGB").save(self.preview_temp_path, "JPEG")

                # Create window if needed
                if not self.preview_window:
                     self.preview_window = ImageViewerWindow()
                     self.preview_window.connect("destroy", self.on_preview_destroyed)
                     self.preview_window.set_title(_("Preview") + " - " + os.path.basename(file_path))
                     self.preview_window.show_all()

                # Update window
                if self.preview_window:
                     # Update title in case file changed
                     self.preview_window.set_title(_("Preview") + " - " + os.path.basename(file_path))
                     self.preview_window.load_images([self.preview_temp_path])
                     self.preview_window.present()

        except Exception as e:
            print(f"Preview error: {e}")

    def get_current_time_ces(self):
        now = time.time()
        cest_time = time.localtime(now + 3600)
        return cest_time

    def create_watermark_layer(self, width, height, text, progress_dialog=None, scale_factor=1.0):
        """ Creates a transparent image with the watermark pattern. """
        layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        cest_time = self.get_current_time_ces()
        try:
            scaled_font_size = int(self.font_size * scale_factor)
            if scaled_font_size < 1:
                scaled_font_size = 1
            font = ImageFont.truetype(self.font_base_name, scaled_font_size)
        except IOError:
             font = ImageFont.load_default()

        timestamp_str_text = time.strftime('%d %B %Y_%Hh%M', cest_time)
        if self.date_filename_check.get_active():
            full_watermark_text = f"{text} {timestamp_str_text}"
        else:
            full_watermark_text = f"{text}"

        dummy_draw = ImageDraw.Draw(layer)
        bbox = dummy_draw.textbbox((0, 0), full_watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        dpi_from_box = int(self.text_density_scale.get_value())
        dpi = (201 - dpi_from_box * 2) * scale_factor
        if dpi < 1:
            dpi = 1
        interval_pixels_y = int(dpi)
        used_positions = set()

        for ydata in range(interval_pixels_y, height, interval_pixels_y):
            if progress_dialog:
                progress_dialog.pulse()
            x_positions = [(xdata % width) for xdata in range(0, width, text_width)]

            for xdata in x_positions:
                if (xdata, ydata) not in used_positions:
                    angle = random.uniform(- int(self.rotation_scale.get_value()),
                                           int(self.rotation_scale.get_value()))
                    self.font_transp = 100 - self.font_transparency
                    if self.font_color_choosen is False:
                        color = (
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                            self.font_transp
                        )
                    else:
                        color = (
                            int(self.font_color.red * 255),
                            int(self.font_color.green * 255),
                            int(self.font_color.blue * 255),
                            self.font_transp
                            )

                    temp_image = Image.new('RGBA', (int(text_width * 3), int(text_height * 3)), (0, 0, 0, 0))
                    temp_draw = ImageDraw.Draw(temp_image)
                    temp_draw.text((text_width, text_height),
                                   full_watermark_text, font=font, fill=color)
                    rotated_text = temp_image.rotate(angle, expand=True)
                    rotated_text_position = (
                        xdata + text_width / 2 - rotated_text.width / 2,
                        ydata + text_height / 2 - rotated_text.height / 2
                    )
                    layer.paste(rotated_text, (int(rotated_text_position[0]),
                                             int(rotated_text_position[1])),
                              mask=rotated_text)
                    used_positions.add((xdata, ydata))
        return layer

    def add_watermark_to_pdf(self, pdf_path, decided_output_path, text, progress_dialog=None):
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            writer = PyPDF2.PdfWriter()

            original_filename = os.path.basename(pdf_path)
            name_without_ext = os.path.splitext(original_filename)[0]

            cest_time = self.get_current_time_ces()
            timestamp_str = time.strftime('%Y%m%d_%H%M%S', cest_time)

            fprefix = ""
            if self.watermark_prefix.get_text() != "":
                fprefix = self.watermark_prefix.get_text() + "_"

            if self.date_filename_check.get_active():
                final_filename = f"{fprefix}{text}_{timestamp_str}_{name_without_ext}.pdf"
            else:
                final_filename = f"{fprefix}{text}_{name_without_ext}.pdf"

            output_path = os.path.join(decided_output_path, final_filename)

            temp_pdf_dir = os.path.join("/tmp", str(uuid.uuid4()))
            os.makedirs(temp_pdf_dir, exist_ok=True)

            for i, page in enumerate(reader.pages):
                if progress_dialog:
                    progress_dialog.set_status(_(f"Processing page {i+1}..."))
                    progress_dialog.pulse()

                # Get page size in points (1 point = 1/72 inch)
                # PIL usually assumes 72 DPI by default for PDF, or we can just map 1 pt = 1 px
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)

                # Generate watermark layer
                # We treat points as pixels for drawing
                layer_img = self.create_watermark_layer(int(width), int(height), text, progress_dialog)

                # Save layer as PDF
                temp_layer_path = os.path.join(temp_pdf_dir, f"watermark_{i}.pdf")
                layer_img.save(temp_layer_path, "PDF")

                # Merge
                watermark_reader = PyPDF2.PdfReader(temp_layer_path)
                watermark_page = watermark_reader.pages[0]

                page.merge_page(watermark_page)
                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            shutil.rmtree(temp_pdf_dir)
            return output_path

        except Exception as err:
            print(f"Error adding watermark to PDF: {err}")
            return None

    def add_watermark_to_image(self, image_path, decided_output_path, text, progress_dialog=None):
        try:
            with Image.open(image_path).convert("RGBA") as img:
                # Resize image if it's too large while preserving aspect ratio
                if self.list_size.get_active_text() != "None":
                    resize_selected = int(self.list_size.get_active_text())
                    width_percent = (resize_selected / float(img.width))
                    height_size = int((float(img.height) * float(width_percent)))

                    if max(img.size) > resize_selected:
                        img = img.resize((resize_selected, height_size), Image.LANCZOS)
                    else:
                        warning_dialog = WarningDialog(
                            title="Error",
                            message=_(f"Image size is  {img.size}, will not rescale it to {resize_selected}"),
                            )
                        warning_dialog.show()

                layer = self.create_watermark_layer(img.width, img.height, text, progress_dialog)
                img.alpha_composite(layer)

                cest_time = self.get_current_time_ces()
                timestamp_str = time.strftime('%Y%m%d_%H%M%S', cest_time)
                original_filename = os.path.basename(image_path)
                name_without_ext = os.path.splitext(original_filename)[0]
                fprefix = ""
                if self.watermark_prefix.get_text() != "":
                    fprefix = self.watermark_prefix.get_text() + "_"
                if self.date_filename_check.get_active():
                    final_filename = f"{fprefix}{text}_{timestamp_str}_{name_without_ext}"
                else:
                    final_filename = f"{fprefix}{text}_{name_without_ext}"

                full_output_filename = os.path.join(decided_output_path, final_filename)
                if self.pdf_choosen is False:
                    img.convert("RGB").save(full_output_filename+".jpg", "JPEG", quality=self.compression_rate)
                    extension = ".jpg"
                else:
                    img.convert("RGB").save(full_output_filename+".pdf", "PDF")
                    extension = ".pdf"
                return full_output_filename+extension

        except Exception as err:
            print(f"Error adding watermark: {err}")
            warning_dialog = WarningDialog(
                title="Error",
                message=_(f"An error occurred while adding the watermark: {err}"),
            )
            warning_dialog.show()
            return None

WIN = WatermarkApp()
WIN.connect("destroy", Gtk.main_quit)
WIN.show_all()
# Hide expert option per default
WIN.expert_options_frame.hide()
WIN.files_selected_hbox.hide()
Gtk.main()
