#!/usr/bin/env python3
"""
Custom exceptions for VoiceType.
"""

import time
from typing import Any, Dict, Optional


class VoiceTypeError(Exception):
    """Base exception for all VoiceType errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/UI."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ConfigurationError(VoiceTypeError):
    """Configuration related errors."""

    pass


class AudioDeviceError(VoiceTypeError):
    """Audio device related errors."""

    @classmethod
    def from_device_info(
        cls, device_info: Dict[str, Any], operation: str
    ) -> "AudioDeviceError":
        return cls(
            f"Audio device error during {operation}",
            details={
                "device": device_info.get("name", "unknown"),
                "operation": operation,
                "input_channels": device_info.get("max_input_channels", 0),
                "sample_rate": device_info.get("default_samplerate", 0),
            },
        )


class ModelError(VoiceTypeError):
    """Model loading/transcription errors."""

    @classmethod
    def from_exception(
        cls, exc: Exception, stage: str, model_name: str
    ) -> "ModelError":
        return cls(
            f"Model error during {stage}",
            details={
                "model": model_name,
                "stage": stage,
                "original_error": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )


class TranscriptionError(VoiceTypeError):
    """Transcription specific errors."""

    pass


class HotkeyError(VoiceTypeError):
    """Hotkey/socket communication errors."""

    pass


class GUINotAvailableError(VoiceTypeError):
    """GUI dependencies not available."""

    pass


class ResourceError(VoiceTypeError):
    """Resource limitation errors (memory, CPU, etc.)."""

    pass


class PlatformNotSupportedError(VoiceTypeError):
    """Platform not supported."""

    pass
