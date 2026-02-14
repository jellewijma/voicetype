#!/usr/bin/env python3
"""
GUI Configuration dialog for VoiceType.
"""

from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from ..core.config import Config  # noqa: E402


class ConfigDialog(Gtk.Dialog):
    def __init__(self, config: Config, parent: Optional[Gtk.Window] = None):
        super().__init__(
            title="VoiceType Configuration",
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                "Cancel",
                Gtk.ResponseType.CANCEL,
                "Save",
                Gtk.ResponseType.OK,
            ),
        )

        self.config = config
        self.original_config = config.to_dict()
        self.changed = False

        self.set_default_size(600, 500)
        self.set_border_width(10)

        # Create notebook with tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # Add tabs
        self._create_general_tab()
        self._create_audio_tab()
        self._create_model_tab()
        self._create_text_tab()
        self._create_hotkeys_tab()
        self._create_privacy_tab()

        # Connect signals
        self.notebook.connect("switch-page", self._on_tab_changed)

        # Add notebook to dialog
        box = self.get_content_area()
        box.pack_start(self.notebook, True, True, 0)

        # Status bar
        self.statusbar = Gtk.Statusbar()
        self.statusbar.push(0, "Ready")
        box.pack_start(self.statusbar, False, False, 0)

        self.show_all()

    def _create_general_tab(self):
        """Create general settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # Auto-start
        auto_start = Gtk.CheckButton(label="Start VoiceType on login")
        auto_start.set_active(self.config.auto_start)
        auto_start.connect("toggled", self._on_auto_start_toggled)
        box.pack_start(auto_start, False, False, 0)

        # System tray
        tray_icon = Gtk.CheckButton(label="Show system tray icon")
        tray_icon.set_active(self.config.show_tray_icon)
        tray_icon.connect("toggled", self._on_tray_icon_toggled)
        box.pack_start(tray_icon, False, False, 0)

        # Notification preferences
        frame = Gtk.Frame(label="Notifications")
        frame.set_border_width(5)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        frame.add(vbox)

        notify_start = Gtk.CheckButton(label="Notify when recording starts")
        notify_start.set_active(self.config.notify_recording_start)
        notify_start.connect("toggled", self._on_notify_start_toggled)
        vbox.pack_start(notify_start, False, False, 0)

        notify_stop = Gtk.CheckButton(label="Notify when recording stops")
        notify_stop.set_active(self.config.notify_recording_stop)
        notify_stop.connect("toggled", self._on_notify_stop_toggled)
        vbox.pack_start(notify_stop, False, False, 0)

        box.pack_start(frame, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="General"))

    def _create_audio_tab(self):
        """Create audio settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # Input device (placeholder)
        input_frame = Gtk.Frame(label="Input Device")
        input_frame.set_border_width(5)

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        input_frame.add(input_box)

        # Device combo (empty for now)
        device_store = Gtk.ListStore(str, str)  # name, id
        device_combo = Gtk.ComboBox.new_with_model_and_entry(device_store)
        device_combo.set_entry_text_column(0)
        device_combo.connect("changed", self._on_device_changed)
        input_box.pack_start(device_combo, False, False, 0)

        # Test button (placeholder)
        test_button = Gtk.Button(label="Test Microphone")
        test_button.connect("clicked", self._on_test_microphone)
        input_box.pack_start(test_button, False, False, 0)

        box.pack_start(input_frame, False, False, 0)

        # Audio levels visualization placeholder
        level_frame = Gtk.Frame(label="Audio Levels")
        level_frame.set_border_width(5)

        level_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        level_frame.add(level_box)

        # Level bar
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1)
        self.level_bar.set_value(0)
        level_box.pack_start(self.level_bar, False, False, 0)

        # Threshold adjustment
        threshold_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        threshold_label = Gtk.Label(label="Silence Threshold:")
        threshold_box.pack_start(threshold_label, False, False, 0)

        self.threshold_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 0.1, 0.001
        )
        self.threshold_scale.set_value(self.config.silence_threshold)
        self.threshold_scale.set_digits(3)
        self.threshold_scale.connect("value-changed", self._on_threshold_changed)
        threshold_box.pack_start(self.threshold_scale, True, True, 0)

        level_box.pack_start(threshold_box, False, False, 0)

        # Silence duration adjustment
        duration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        duration_label = Gtk.Label(label="Silence Duration (s):")
        duration_box.pack_start(duration_label, False, False, 0)

        self.duration_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.5, 5.0, 0.1
        )
        self.duration_scale.set_value(self.config.silence_duration)
        self.duration_scale.set_digits(1)
        self.duration_scale.connect("value-changed", self._on_duration_changed)
        duration_box.pack_start(self.duration_scale, True, True, 0)

        level_box.pack_start(duration_box, False, False, 0)

        box.pack_start(level_frame, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Audio"))

    def _create_model_tab(self):
        """Create model settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # Model selection
        model_frame = Gtk.Frame(label="Transcription Model")
        model_frame.set_border_width(5)

        model_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        model_frame.add(model_box)

        # Model combo
        model_store = Gtk.ListStore(str, str, str)  # name, size, quality
        models = [
            ("tiny.en", "~1GB VRAM", "Good for fast transcription"),
            ("small.en", "~2GB VRAM", "Better accuracy"),
            ("distil-medium.en", "~3GB VRAM", "Best balance"),
            ("medium.en", "~5GB VRAM", "Highest accuracy"),
        ]

        for model in models:
            model_store.append(model)

        self.model_combo = Gtk.ComboBox.new_with_model(model_store)
        renderer = Gtk.CellRendererText()
        self.model_combo.pack_start(renderer, True)
        self.model_combo.add_attribute(renderer, "text", 0)

        # Set current model
        for i, model in enumerate(models):
            if model[0] == self.config.model_name:
                self.model_combo.set_active(i)
                break

        self.model_combo.connect("changed", self._on_model_changed)
        model_box.pack_start(self.model_combo, False, False, 0)

        # Model info
        info_label = Gtk.Label()
        info_label.set_markup("<small>Select model based on available VRAM</small>")
        info_label.set_xalign(0)
        model_box.pack_start(info_label, False, False, 0)

        # Device selection
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        device_label = Gtk.Label(label="Device:")
        device_box.pack_start(device_label, False, False, 0)

        self.device_combo = Gtk.ComboBoxText()
        self.device_combo.append_text("Auto-detect")
        self.device_combo.append_text("CUDA (NVIDIA GPU)")
        self.device_combo.append_text("CPU")

        if self.config.device == "cuda":
            self.device_combo.set_active(1)
        elif self.config.device == "cpu":
            self.device_combo.set_active(2)
        else:
            self.device_combo.set_active(0)

        self.device_combo.connect("changed", self._on_device_type_changed)
        device_box.pack_start(self.device_combo, True, True, 0)

        model_box.pack_start(device_box, False, False, 0)

        # Compute type
        compute_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        compute_label = Gtk.Label(label="Compute Type:")
        compute_box.pack_start(compute_label, False, False, 0)

        self.compute_combo = Gtk.ComboBoxText()
        self.compute_combo.append_text("float16")
        self.compute_combo.append_text("float32")
        self.compute_combo.append_text("int8_float16")
        self.compute_combo.append_text("int8")

        # Set current compute type
        for i, text in enumerate(["float16", "float32", "int8_float16", "int8"]):
            if text == self.config.compute_type:
                self.compute_combo.set_active(i)
                break

        self.compute_combo.connect("changed", self._on_compute_type_changed)
        compute_box.pack_start(self.compute_combo, True, True, 0)

        model_box.pack_start(compute_box, False, False, 0)

        box.pack_start(model_frame, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Model"))

    def _create_text_tab(self):
        """Create text processing settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        # Text processing options
        frame = Gtk.Frame(label="Text Processing")
        frame.set_border_width(5)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        frame.add(vbox)

        # Remove fillers
        remove_fillers = Gtk.CheckButton(
            label="Remove filler words (um, uh, like, etc.)"
        )
        remove_fillers.set_active(self.config.remove_fillers)
        remove_fillers.connect("toggled", self._on_remove_fillers_toggled)
        vbox.pack_start(remove_fillers, False, False, 0)

        # Auto capitalize
        auto_capitalize = Gtk.CheckButton(label="Auto‑capitalize sentences")
        auto_capitalize.set_active(self.config.auto_capitalize)
        auto_capitalize.connect("toggled", self._on_auto_capitalize_toggled)
        vbox.pack_start(auto_capitalize, False, False, 0)

        # Auto punctuate
        auto_punctuate = Gtk.CheckButton(
            label="Auto‑punctuate (add missing punctuation)"
        )
        auto_punctuate.set_active(self.config.auto_punctuate)
        auto_punctuate.connect("toggled", self._on_auto_punctuate_toggled)
        vbox.pack_start(auto_punctuate, False, False, 0)

        # Trailing punctuation
        trailing_punctuation = Gtk.CheckButton(label="Ensure trailing punctuation")
        trailing_punctuation.set_active(self.config.trailing_punctuation)
        trailing_punctuation.connect("toggled", self._on_trailing_punctuation_toggled)
        vbox.pack_start(trailing_punctuation, False, False, 0)

        box.pack_start(frame, False, False, 0)

        # Dictionary and snippets placeholders
        dict_frame = Gtk.Frame(label="Personal Dictionary (future)")
        dict_frame.set_border_width(5)
        dict_label = Gtk.Label(
            label="Dictionary editing will be available in a future version"
        )
        dict_frame.add(dict_label)
        box.pack_start(dict_frame, False, False, 0)

        snippets_frame = Gtk.Frame(label="Snippets (future)")
        snippets_frame.set_border_width(5)
        snippets_label = Gtk.Label(
            label="Snippet management will be available in a future version"
        )
        snippets_frame.add(snippets_label)
        box.pack_start(snippets_frame, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Text"))

    def _create_hotkeys_tab(self):
        """Create hotkeys settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        label = Gtk.Label(
            label="Hotkey configuration is currently handled via Hyprland "
            "configuration.\n\n"
            "Add to ~/.config/hypr/hyprland.conf:\n"
            "bind = , F12, exec, /path/to/voicetype-toggle.sh"
        )
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Hotkeys"))

    def _create_privacy_tab(self):
        """Create privacy settings tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        label = Gtk.Label(
            label="Privacy features will be added in a future version.\n\n"
            "VoiceType already processes everything locally—"
            "no data is sent to the cloud."
        )
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Privacy"))

    # Event handlers
    def _on_auto_start_toggled(self, widget):
        self.config.auto_start = widget.get_active()
        self.changed = True

    def _on_tray_icon_toggled(self, widget):
        self.config.show_tray_icon = widget.get_active()
        self.changed = True

    def _on_notify_start_toggled(self, widget):
        self.config.notify_recording_start = widget.get_active()
        self.changed = True

    def _on_notify_stop_toggled(self, widget):
        self.config.notify_recording_stop = widget.get_active()
        self.changed = True

    def _on_device_changed(self, widget):
        # Placeholder for device selection
        pass

    def _on_test_microphone(self, widget):
        # Placeholder for microphone test
        self.statusbar.push(0, "Microphone test not yet implemented")

    def _on_threshold_changed(self, widget):
        value = widget.get_value()
        self.config.silence_threshold = value
        self.changed = True

    def _on_duration_changed(self, widget):
        value = widget.get_value()
        self.config.silence_duration = value
        self.changed = True

    def _on_model_changed(self, widget):
        tree_iter = widget.get_active_iter()
        if tree_iter is not None:
            model = widget.get_model()
            model_name = model[tree_iter][0]
            self.config.model_name = model_name
            self.changed = True

    def _on_device_type_changed(self, widget):
        active = widget.get_active()
        if active == 1:
            self.config.device = "cuda"
        elif active == 2:
            self.config.device = "cpu"
        else:
            self.config.device = "auto"
        self.changed = True

    def _on_compute_type_changed(self, widget):
        active = widget.get_active()
        options = ["float16", "float32", "int8_float16", "int8"]
        if 0 <= active < len(options):
            self.config.compute_type = options[active]
            self.changed = True

    def _on_remove_fillers_toggled(self, widget):
        self.config.remove_fillers = widget.get_active()
        self.changed = True

    def _on_auto_capitalize_toggled(self, widget):
        self.config.auto_capitalize = widget.get_active()
        self.changed = True

    def _on_auto_punctuate_toggled(self, widget):
        self.config.auto_punctuate = widget.get_active()
        self.changed = True

    def _on_trailing_punctuation_toggled(self, widget):
        self.config.trailing_punctuation = widget.get_active()
        self.changed = True

    def _on_tab_changed(self, notebook, page, page_num):
        # Update status bar
        tab_names = ["General", "Audio", "Model", "Text", "Hotkeys", "Privacy"]
        if page_num < len(tab_names):
            self.statusbar.push(0, f"Editing {tab_names[page_num]} settings")

    def _show_error(self, message: str):
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message,
        )
        dialog.run()
        dialog.destroy()

    def save_configuration(self) -> bool:
        """Save configuration to file."""
        try:
            if self.config.save():
                self.statusbar.push(0, "Configuration saved successfully")
                self.changed = False
                return True
            else:
                self._show_error("Failed to save configuration file.")
                return False
        except Exception as e:
            self._show_error(f"Failed to save configuration: {e}")
            return False
