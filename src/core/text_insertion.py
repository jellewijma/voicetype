#!/usr/bin/env python3
"""
Text insertion functionality for different desktop environments.
"""

import json
import os
import subprocess
import time

import pyperclip

from .config import Config


class TextInserter:
    """Handles inserting text into active window (Wayland/X11)."""

    def __init__(self, config: Config):
        self.config = config
        self._use_wayland = os.environ.get("XDG_SESSION_TYPE", "") == "wayland"
        self._saved_window = None

    def save_focus(self):
        """Save current window focus (for Wayland)."""
        if self._use_wayland:
            try:
                result = subprocess.run(
                    ["hyprctl", "activewindow", "-j"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    self._saved_window = data.get("address")
            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                json.JSONDecodeError,
                FileNotFoundError,
            ):
                pass  # Hyprctl might not be available

    def insert(self, text: str):
        """Insert text into active window."""
        if not text:
            return

        if self._use_wayland:
            self._insert_wayland(text)
        else:
            self._insert_x11(text)

    def _insert_wayland(self, text: str):
        """Insert text on Wayland."""
        time.sleep(0.1)  # Small delay for focus change

        # Restore focus if we saved a window
        if self._saved_window:
            try:
                subprocess.run(
                    [
                        "hyprctl",
                        "dispatch",
                        "focuswindow",
                        f"address:{self._saved_window}",
                    ],
                    capture_output=True,
                    timeout=2.0,
                )
                time.sleep(0.05)
            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                FileNotFoundError,
            ):
                pass  # Continue without focus restoration

        # Try wtype first (direct typing)
        try:
            result = subprocess.run(
                ["wtype", text], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass  # wtype not available or failed

        # Fallback: copy to clipboard and paste
        try:
            subprocess.run(
                ["wl-copy"],
                input=text.encode(),
                check=True,
                timeout=2.0,
            )
            time.sleep(0.05)
            subprocess.run(
                ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                check=True,
                timeout=2.0,
            )
            return
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass  # Clipboard method failed

        # Ultimate fallback: just copy to clipboard
        try:
            subprocess.run(["wl-copy"], input=text.encode(), timeout=2.0)
            print("Text copied to clipboard - press Ctrl+V to paste")
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            print("Failed to insert text - no compatible method available")

    def _insert_x11(self, text: str):
        """Insert text on X11."""
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", text],
                check=True,
                timeout=5,
            )
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            # Fallback: copy to clipboard and paste
            try:
                pyperclip.copy(text)
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"],
                    check=True,
                    timeout=5,
                )
            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                FileNotFoundError,
                pyperclip.PyperclipException,
            ):
                print(
                    "Failed to insert text on X11 - "
                    "xdotool or clipboard not available"
                )

    def get_active_window(self) -> str:
        """Get name of active window (X11 only)."""
        try:
            result = subprocess.run(
                ["xdotool", "getwindowfocus", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            return result.stdout.strip().lower()
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            return ""
