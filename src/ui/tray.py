#!/usr/bin/env python3
"""
System tray integration.
"""

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..voicetype import VoiceType


class SystemTray:
    """System tray icon and menu."""

    def __init__(self, app: "VoiceType"):
        self.app = app
        self.icon = None  # type: ignore

    def start(self) -> bool:
        """Start system tray icon."""
        try:
            import pystray
            from PIL import Image, ImageDraw

            if not self._check_system_tray():
                return False

            def create_icon():
                img = Image.new("RGB", (64, 64), color="black")
                draw = ImageDraw.Draw(img)
                draw.ellipse([8, 8, 56, 56], fill="red")
                return img

            menu = pystray.Menu(
                pystray.MenuItem(
                    "Record",
                    self._toggle_record,
                    checked=lambda _: self.app.is_recording,
                ),
                pystray.MenuItem("Settings", self._open_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._quit),
            )

            self.icon = pystray.Icon("voicetype", create_icon(), "VoiceType", menu)
            assert self.icon is not None
            self.icon.run()
            return True
        except Exception as e:
            print(f"Failed to start system tray: {e}")
            return False

    def _check_system_tray(self) -> bool:
        """Check if system tray is available."""
        try:
            # Check for common panel/tray applications
            result = subprocess.run(
                ["xdotool", "search", "--class", "panel"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if not result.stdout.strip():
                result = subprocess.run(
                    ["xdotool", "search", "--name", "tray"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )

            # Check desktop environment
            has_tray = bool(result.stdout.strip())
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            supported_desktops = ["kde", "xfce", "lxqt", "mate", "gnome"]

            return has_tray or any(de in desktop_env for de in supported_desktops)
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            return False

    def _toggle_record(self):
        """Toggle recording from tray menu."""
        self.app.toggle_recording()

    def _open_settings(self):
        """Open settings file in editor."""
        from ..core.config import CONFIG_FILE

        editor = os.environ.get("EDITOR", "nano")
        try:
            subprocess.Popen([editor, str(CONFIG_FILE)])
        except (FileNotFoundError, PermissionError) as e:
            print(f"Failed to open settings: {e}")

    def _quit(self):
        """Quit application from tray menu."""
        if self.icon:
            self.icon.stop()  # type: ignore
        self.app.quit()

    def update_icon(self, recording: bool):
        """Update tray icon color based on recording state."""
        if self.icon:
            from PIL import Image, ImageDraw

            def create_icon():
                color = "red" if recording else "green"
                img = Image.new("RGB", (64, 64), color="black")
                draw = ImageDraw.Draw(img)
                draw.ellipse([8, 8, 56, 56], fill=color)
                return img

            self.icon.icon = create_icon()
