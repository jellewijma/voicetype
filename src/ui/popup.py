#!/usr/bin/env python3
"""
Recording popup notification.
"""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402


class RecordingPopup:
    """Popup window showing recording status."""

    def __init__(self):
        self.window = None
        self.label = None
        self._visible = False

    def show(self, text: str = "Listening..."):
        """Show popup with text."""
        if self.window is None:
            self._create_window()

        GLib.idle_add(self._update_text, text)

        if not self._visible:
            self._visible = True
            GLib.idle_add(self._do_show)

    def _do_show(self):
        """Show window (called from GLib.idle_add)."""
        if self.window:
            self.window.show_all()
            self._position_window()
        return False

    def hide(self):
        """Hide popup."""
        if self.window and self._visible:
            self._visible = False
            GLib.idle_add(self.window.hide)

    def update_text(self, text: str):
        """Update popup text."""
        if self.label:
            GLib.idle_add(self._update_text, text)

    def _update_text(self, text: str):
        """Update label text (called from GLib.idle_add)."""
        if self.label:
            self.label.set_text(text)
        return False

    def _create_window(self):
        """Create GTK window."""
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_resizable(False)
        self.window.set_accept_focus(False)

        self.window.connect("realize", self._on_realize)

        # CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: rgba(30, 30, 30, 0.95);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .container {
                padding: 14px 20px;
                border-radius: 24px;
            }
            .mic-icon {
                color: #FF5252;
                font-size: 16px;
            }
            label {
                color: white;
                font-size: 14px;
                font-weight: 500;
            }
            .transcribing {
                color: #4CAF50;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Layout
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.get_style_context().add_class("container")

        # Microphone icon
        mic_label = Gtk.Label()
        mic_label.set_markup('<span foreground="#FF5252">●</span>')
        mic_label.set_margin_end(4)
        hbox.pack_start(mic_label, False, False, 0)

        # Status text
        self.label = Gtk.Label(label="Listening...")
        hbox.pack_start(self.label, False, False, 0)

        self.window.add(hbox)

    def _on_realize(self, widget):
        """Window realize event."""
        window = widget.get_window()
        if window:
            window.set_override_redirect(True)

    def _position_window(self):
        """Position window at bottom center of screen."""
        if not self.window:
            return

        display = Gdk.Display.get_default()
        if not display:
            return

        monitor = display.get_primary_monitor()
        if not monitor:
            monitor = display.get_monitor(0)
        if not monitor:
            return

        geometry = monitor.get_geometry()

        # Get window size (requires window to be realized)
        self.window.realize()
        window_width, window_height = self.window.get_size()

        # Center horizontally, position near bottom
        x = geometry.x + (geometry.width - window_width) // 2
        y = geometry.y + geometry.height - window_height - 80

        self.window.move(x, y)
