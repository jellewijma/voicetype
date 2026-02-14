#!/usr/bin/env python3
"""
Socket server for hotkey communication with error handling.
"""

import logging
import socket
import threading
import time
from typing import Callable, Optional

from ..core.config import SOCKET_PATH
from ..utils.errors import HotkeyError
from ..utils.recovery import log_error

logger = logging.getLogger(__name__)


class SocketListener:
    """Listens for socket commands to toggle recording with error handling."""

    def __init__(self, callback: Callable[[], None]):
        self.callback = callback
        self._running = False
        self.socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._start_timeout = 5.0  # seconds
        self._socket_timeout = 1.0  # seconds
        self._max_connection_attempts = 3

    def start(self):
        """Start socket listener with error recovery."""
        # Clean up existing socket
        if SOCKET_PATH.exists():
            try:
                SOCKET_PATH.unlink()
                logger.info(f"Removed existing socket: {SOCKET_PATH}")
            except OSError as e:
                logger.warning(f"Could not remove existing socket: {e}")
                log_error(e, {"operation": "socket_cleanup"})

        # Create socket with retry logic
        for attempt in range(self._max_connection_attempts):
            try:
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.settimeout(self._start_timeout)

                self.socket.bind(str(SOCKET_PATH))
                self.socket.listen(1)
                self.socket.settimeout(self._socket_timeout)

                logger.info(f"Socket listening at: {SOCKET_PATH}")
                logger.info(
                    "Add to your Hyprland config (~/.config/hypr/hyprland.conf):"
                )
                logger.info(
                    '  bind = , F12, exec, echo "toggle" | nc -U /tmp/voicetype.sock'
                )
                logger.info("Then reload Hyprland config.")

                # Start listener thread
                self._running = True
                self._thread = threading.Thread(target=self._listen, daemon=True)
                self._thread.start()
                return  # Success

            except (OSError, socket.error) as e:
                log_error(e, {"attempt": attempt + 1, "operation": "socket_start"})

                if self.socket:
                    try:
                        self.socket.close()
                    except OSError:
                        pass
                    self.socket = None

                if attempt < self._max_connection_attempts - 1:
                    retry_delay = 2.0 * (attempt + 1)
                    logger.warning(
                        f"Socket start failed, retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Failed to start socket server after "
                        f"{self._max_connection_attempts} attempts"
                    )
                    self._running = False
                    raise HotkeyError(f"Socket server failed: {e}")

    def _listen(self):
        """Listen for incoming connections with error handling."""
        while self._running and self.socket:
            try:
                # Socket should be valid due to while condition, but check for mypy
                if self.socket is None:
                    logger.warning("Socket is None in listen loop")
                    time.sleep(0.1)
                    continue

                conn, addr = self.socket.accept()
                conn.settimeout(2.0)  # Timeout for receiving data

                try:
                    data = conn.recv(1024).decode().strip()
                    conn.close()

                    if data == "toggle":
                        logger.debug("Toggle command received via socket")
                        # Use GLib if available, otherwise call directly
                        try:
                            from gi.repository import GLib

                            GLib.idle_add(self.callback)
                        except ImportError:
                            self.callback()
                    else:
                        logger.warning(f"Unknown socket command: {data}")

                except (socket.timeout, socket.error, UnicodeDecodeError) as e:
                    logger.warning(f"Error handling socket connection: {e}")
                    try:
                        conn.close()
                    except OSError:
                        pass

            except socket.timeout:
                # Expected timeout for non-blocking accept
                continue
            except (socket.error, OSError) as e:
                if self._running:
                    logger.error(f"Socket accept error: {e}")
                    log_error(e, {"operation": "socket_accept"})
                    # Brief pause before retrying to avoid tight loop on
                    # persistent error
                    time.sleep(0.5)
            except Exception as e:
                if self._running:
                    logger.error(f"Unexpected socket error: {e}")
                    log_error(e, {"operation": "socket_listen"})

    def stop(self):
        """Stop socket listener gracefully."""
        self._running = False

        if self.socket:
            try:
                self.socket.close()
                logger.info("Socket closed")
            except OSError as e:
                logger.warning(f"Error closing socket: {e}")
            finally:
                self.socket = None

        if SOCKET_PATH.exists():
            try:
                SOCKET_PATH.unlink()
                logger.info("Socket file removed")
            except OSError as e:
                logger.warning(f"Could not remove socket file: {e}")

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Socket thread did not terminate gracefully")
            else:
                logger.info("Socket thread terminated")

    def is_running(self) -> bool:
        """Check if socket listener is running."""
        return self._running and self.socket is not None
