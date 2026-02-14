#!/usr/bin/env python3
"""
VoiceType - Local AI Voice Dictation for Linux
Inspired by Wispr Flow, uses faster-whisper for fast, accurate transcription.
Controlled via Hyprland keybind -> socket communication.
"""

import argparse
import logging
import os
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gtk  # noqa: E402

# If we're running as a script (not as a module), adjust sys.path
if __package__ is None:
    # Add parent directory to sys.path to allow package imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "src"

from src.core.audio import AudioRecorder  # noqa: E402
from src.core.config import Config  # noqa: E402
from src.core.text_insertion import TextInserter  # noqa: E402
from src.core.text_processing import TextProcessor  # noqa: E402
from src.core.transcription import Transcriber  # noqa: E402
from src.integration.socket_server import SocketListener  # noqa: E402
from src.ui.popup import RecordingPopup  # noqa: E402
from src.ui.tray import SystemTray  # noqa: E402
from src.utils.errors import AudioDeviceError  # noqa: E402
from src.utils.errors import (ConfigurationError, HotkeyError,  # noqa: E402
                              ModelError, TranscriptionError)
from src.utils.recovery import log_error, setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


class VoiceType:
    def __init__(self, auto_record: bool = False):
        # Set up logging
        setup_logging()
        logger.info("Initializing VoiceType")

        try:
            self.config = Config.load()
            logger.info(
                f"Configuration loaded: model={self.config.model_name}, "
                f"device={self.config.device}"
            )
        except Exception as e:
            log_error(e, {"stage": "config_load"})
            logger.error("Failed to load configuration, using defaults")
            self.config = Config()

        self.recorder = AudioRecorder(self.config)
        self.transcriber = Transcriber(self.config)
        self.processor = TextProcessor(self.config)
        self.inserter = TextInserter(self.config)
        self.tray = SystemTray(self)
        self.popup = RecordingPopup()
        self.is_recording = False
        self._running = True
        self.auto_record = auto_record
        self.model_loading = False
        self.model_loaded = False
        self.pending_toggle = False
        logger.info("VoiceType initialized successfully")

    def _initialize_model(self):
        """Start loading the model in background thread with error handling."""
        if self.model_loading or self.model_loaded:
            return

        self.model_loading = True
        self.popup.show("Initializing...")
        logger.info("Starting model initialization")

        def load_in_background():
            try:
                self.transcriber.load_model()
                self.model_loaded = True
                logger.info("Model loaded successfully")
                GLib.idle_add(self._on_model_loaded)
            except ModelError as e:
                log_error(e, {"stage": "model_load_background"})
                logger.error("Failed to load model")
                GLib.idle_add(self._on_model_load_failed, e)
            except Exception as e:
                log_error(e, {"stage": "model_load_background"})
                logger.error(f"Unexpected error loading model: {e}")
                GLib.idle_add(self._on_model_load_failed, e)
            finally:
                self.model_loading = False

        threading.Thread(target=load_in_background, daemon=True).start()

    def _on_model_load_failed(self, error: Exception):
        """Handle model load failure."""
        self.model_loading = False
        self.model_loaded = False
        self.pending_toggle = False

        error_msg = str(error)
        if "CUDA" in error_msg or "GPU" in error_msg:
            display_msg = "GPU not available, falling back to CPU"
            logger.warning(display_msg)
        else:
            display_msg = f"Model load failed: {error_msg[:50]}"
            logger.error(display_msg)

        self.popup.show(display_msg)
        GLib.timeout_add(3000, self.popup.hide)

    def _on_model_loaded(self):
        """Called when model loading completes."""
        logger.info("Model loaded callback")
        self.popup.hide()
        if self.auto_record:
            logger.info("Auto-record enabled, starting recording")
            self._start_recording()
        elif self.pending_toggle:
            logger.info("Pending toggle, triggering recording")
            self.pending_toggle = False
            self.toggle_recording()

    def toggle_recording(self):
        try:
            if self.is_recording:
                logger.debug("Stopping recording (toggle)")
                self._stop_and_transcribe()
                return

            if not self.model_loaded:
                if not self.model_loading:
                    logger.debug("Model not loaded, initializing")
                    self._initialize_model()
                self.pending_toggle = True
                logger.debug("Toggle pending model load")
                return

            logger.debug("Starting recording (toggle)")
            self._start_recording()

        except Exception as e:
            log_error(
                e, {"operation": "toggle_recording", "is_recording": self.is_recording}
            )
            logger.error(f"Failed to toggle recording: {e}")
            # Show error to user via popup
            self.popup.show("Error: Failed to toggle recording")
            GLib.timeout_add(3000, self.popup.hide)

    def _start_recording(self):
        try:
            logger.info("Starting recording")
            self.inserter.save_focus()
            self.is_recording = True
            self.recorder.start_recording()
            self.tray.update_icon(True)
            self.popup.show("Listening...")
            logger.info("Recording started successfully")

        except AudioDeviceError as e:
            log_error(e, {"operation": "start_recording"})
            logger.error("Audio device error, cannot start recording")
            self.popup.show("Error: No audio device")
            GLib.timeout_add(3000, self.popup.hide)
            self.is_recording = False
            self.tray.update_icon(False)

        except Exception as e:
            log_error(e, {"operation": "start_recording"})
            logger.error(f"Failed to start recording: {e}")
            self.popup.show("Error: Failed to start recording")
            GLib.timeout_add(3000, self.popup.hide)
            self.is_recording = False
            self.tray.update_icon(False)

    def _stop_and_transcribe(self):
        try:
            self.is_recording = False
            self.tray.update_icon(False)
            self.popup.update_text("Transcribing...")
            logger.info("Recording stopped, starting transcription")

            audio = self.recorder.stop_recording()
            if audio is not None:
                logger.info(
                    f"Audio captured: {len(audio) / self.config.sample_rate:.2f}s"
                )

                try:
                    text = self.transcriber.transcribe(audio)
                    processed = self.processor.process(text)
                    self.popup.hide()

                    if processed:
                        logger.info(f"Transcription: {processed[:100]}...")
                        self.inserter.insert(processed)
                        logger.info("Text inserted successfully")
                    else:
                        logger.info("No speech detected in audio")
                        self.popup.show("No speech detected")
                        GLib.timeout_add(2000, self.popup.hide)

                except TranscriptionError as e:
                    log_error(
                        e, {"operation": "transcription", "audio_length": len(audio)}
                    )
                    logger.error("Transcription failed")
                    self.popup.show("Error: Transcription failed")
                    GLib.timeout_add(3000, self.popup.hide)

                except Exception as e:
                    log_error(
                        e, {"operation": "transcription", "audio_length": len(audio)}
                    )
                    logger.error(f"Transcription error: {e}")
                    self.popup.show("Error: Processing failed")
                    GLib.timeout_add(3000, self.popup.hide)
            else:
                logger.warning("No audio data recorded")
                self.popup.hide()

        except Exception as e:
            log_error(e, {"operation": "stop_and_transcribe"})
            logger.error(f"Failed to stop and transcribe: {e}")
            self.popup.show("Error: Failed to process recording")
            GLib.timeout_add(3000, self.popup.hide)
            # Ensure recording state is cleared
            self.is_recording = False
            self.tray.update_icon(False)

    def run(self):
        logger.info("VoiceType starting")
        logger.info("Press Ctrl+C to quit.")

        try:
            self.socket = SocketListener(self.toggle_recording)
            self.socket.start()
            logger.info("Socket listener started")
        except HotkeyError as e:
            log_error(e, {"stage": "socket_start"})
            logger.warning("Hotkey socket failed, continuing without hotkey support")
            self.socket = None
        except Exception as e:
            log_error(e, {"stage": "socket_start"})
            logger.warning(f"Socket failed: {e}, continuing without hotkey support")
            self.socket = None

        if self.auto_record:
            self._initialize_model()

        GLib.timeout_add(100, self._check_quit)

        if self.tray.start():
            logger.info("System tray started")
            Gtk.main()
        else:
            logger.warning("System tray not available. Running in console mode.")
            try:
                Gtk.main()
            except KeyboardInterrupt:
                self.quit()

    def _check_quit(self):
        if not self._running:
            Gtk.main_quit()
            return False
        return True

    def on_config_changed(self):
        """Handle configuration changes."""
        logger.info("Configuration changed")
        # Components already reference the same config object, no need to reload.
        # However, some settings may require restart (e.g., sample_rate).
        # For now, just log.
        pass

    def quit(self):
        logger.info("Shutting down VoiceType")
        self._running = False

        if self.is_recording:
            logger.info("Stopping active recording")
            try:
                self.recorder.stop_recording()
            except Exception as e:
                log_error(e, {"operation": "quit_recording_stop"})
                logger.warning(f"Error stopping recording: {e}")

        if hasattr(self, "socket") and self.socket is not None:
            try:
                self.socket.stop()
                logger.info("Socket listener stopped")
            except Exception as e:
                log_error(e, {"operation": "quit_socket_stop"})
                logger.warning(f"Error stopping socket: {e}")

        logger.info("VoiceType shutdown complete")
        sys.exit(0)


def main():
    """Main entry point with global error handling."""
    parser = argparse.ArgumentParser(description="VoiceType - Local AI Voice Dictation")
    parser.add_argument(
        "--auto-record",
        action="store_true",
        help="Start recording automatically after initialization",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Set up logging early
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    logger.info(f"VoiceType starting with args: {vars(args)}")

    try:
        app = VoiceType(auto_record=args.auto_record)
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except ConfigurationError as e:
        log_error(e, {"stage": "main_config"})
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        log_error(e, {"stage": "main_unhandled"})
        logger.critical(f"Unhandled error: {e}", exc_info=True)
        # Try to show error to user if possible
        try:
            import gi

            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk

            dialog = Gtk.MessageDialog(
                parent=None,
                flags=Gtk.DialogFlags.MODAL,
                type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                message_format=f"VoiceType crashed: {str(e)[:100]}",
            )
            dialog.run()
            dialog.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
