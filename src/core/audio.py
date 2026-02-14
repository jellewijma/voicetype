#!/usr/bin/env python3
"""
Audio recording functionality for VoiceType.
"""

import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional

import numpy as np
import sounddevice as sd

from ..utils.errors import AudioDeviceError
from ..utils.recovery import log_error, with_retry
from .config import Config

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Handles audio recording with silence detection and error recovery."""

    def __init__(self, config: Config):
        self.config = config
        self.is_recording = False
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self.audio_data: list[np.ndarray] = []
        self._stop_event = threading.Event()
        self.available_devices = self._scan_devices()
        self.current_device = self._select_best_device()
        self.stream = None

    def _scan_devices(self) -> List[Dict[str, Any]]:
        """Scan for available audio input devices."""
        devices = []
        try:
            host_apis = sd.query_hostapis()
            for api_index, api in enumerate(host_apis):
                for device_index in api["devices"]:
                    try:
                        device = sd.query_devices(device_index, "input")
                        if device["max_input_channels"] > 0:
                            devices.append(
                                {
                                    "index": device_index,
                                    "name": device["name"],
                                    "api": api["name"],
                                    "channels": device["max_input_channels"],
                                    "sample_rate": device[
                                        "default_samplerate"
                                    ],
                                    "latency": device[
                                        "default_low_input_latency"
                                    ],
                                }
                            )
                    except Exception:
                        # Device might not be an input device or other error
                        continue
        except Exception as e:
            logger.error(f"Failed to scan audio devices: {e}")
            log_error(e, {"operation": "device_scan"})

        logger.info(f"Found {len(devices)} audio input devices")
        return devices

    def _select_best_device(self) -> Optional[Dict[str, Any]]:
        """Select the best available audio device."""
        if not self.available_devices:
            return None

        # Prefer devices with lower latency and higher sample rate
        self.available_devices.sort(
            key=lambda d: (d["latency"], -d["sample_rate"])
        )
        selected = self.available_devices[0]
        logger.info(f"Selected audio device: {selected['name']}")
        return selected

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        self.audio_queue.put(indata.copy())

    @with_retry(
        max_attempts=2,
        delay=0.5,
        exceptions=(sd.PortAudioError, AudioDeviceError),
        fallback=None,  # We'll handle fallback in the method
    )
    def _start_stream(self) -> bool:
        """Start the audio stream with retry logic."""
        if not self.available_devices:
            raise AudioDeviceError("No audio input devices available")

        if self.current_device is None:
            raise AudioDeviceError("No audio device selected")

        try:
            self.stream = sd.InputStream(
                device=self.current_device["index"],
                samplerate=self.config.sample_rate,
                channels=min(
                    self.config.channels,
                    self.current_device["channels"]
                ),
                dtype=np.float32,
                callback=self._audio_callback,
                blocksize=int(self.config.sample_rate * 0.1),  # 100ms blocks
            )
            assert self.stream is not None
            self.stream.start()
            logger.info(
                f"Started recording on device: {self.current_device['name']}"
            )
            return True

        except sd.PortAudioError as e:
            raise AudioDeviceError.from_device_info(
                self.current_device, "start_recording"
            ) from e

    def _fallback_recording(self) -> bool:
        """Fallback recording method when primary fails."""
        logger.warning("Using fallback recording method")
        try:
            # Try default device with simpler configuration
            self.stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            assert self.stream is not None
            self.stream.start()
            logger.info("Fallback recording started successfully")
            return True
        except sd.PortAudioError as e:
            logger.error(f"Fallback recording also failed: {e}")
            log_error(e, {"operation": "fallback_recording"})
            return False

    def start_recording(self):
        """Start recording audio with error recovery."""
        self.audio_data = []
        self._stop_event.clear()
        self.is_recording = True

        try:
            success = self._start_stream()
            if not success:
                # Try fallback
                success = self._fallback_recording()

            if not success:
                raise AudioDeviceError(
                    "Failed to start recording after all attempts"
                )

            # Start audio processing thread
            self._process_thread = threading.Thread(target=self._process_audio)
            self._process_thread.start()

        except Exception as e:
            self.is_recording = False
            log_error(e, {"operation": "start_recording"})
            raise

    def _process_audio(self):
        """Process audio data with silence detection."""
        silence_start = None

        while not self._stop_event.is_set():
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.audio_data.append(data)

                if self.config.silence_duration > 0:
                    volume = np.abs(data).mean()
                    if volume < self.config.silence_threshold:
                        if silence_start is None:
                            silence_start = time.time()
                        elif (
                            time.time() - silence_start
                            > self.config.silence_duration
                        ):
                            break
                    else:
                        silence_start = None
            except queue.Empty:
                continue

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data."""
        self._stop_event.set()
        self.is_recording = False

        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except sd.PortAudioError as e:
                logger.error(f"Error stopping audio stream: {e}")
                log_error(e, {"operation": "stop_recording"})
            finally:
                self.stream = None

        if (
            hasattr(self, "_process_thread")
            and self._process_thread.is_alive()
        ):
            self._process_thread.join(timeout=1.0)

        if not self.audio_data:
            logger.warning("No audio data recorded")
            return None

        try:
            audio = np.concatenate(self.audio_data, axis=0)
            logger.info(
                f"Recorded {len(audio) / self.config.sample_rate:.2f}s of audio"
            )
            return audio
        except Exception as e:
            logger.error(f"Error concatenating audio data: {e}")
            log_error(e, {"operation": "audio_concatenation"})
            return None
