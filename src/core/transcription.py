#!/usr/bin/env python3
"""
Transcription functionality using faster-whisper.
"""

import logging
import threading

import numpy as np

from ..utils.errors import ModelError, TranscriptionError
from ..utils.recovery import log_error, with_retry
from .config import Config

logger = logging.getLogger(__name__)


class Transcriber:
    """Handles AI model loading and transcription with error recovery."""

    def __init__(self, config: Config):
        self.config = config
        self.model = None  # type: ignore
        self.model_loaded = False
        self._load_lock = threading.Lock()
        self._load_attempts = 0

    @with_retry(
        max_attempts=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(Exception,),
        fallback=None,
    )
    def _load_model_with_retry(self):
        """Load model with retry logic."""
        # Import here to avoid loading unless needed
        from faster_whisper import WhisperModel

        logger.info(f"Loading model: {self.config.model_name} on {self.config.device}")
        self.model = WhisperModel(
            self.config.model_name,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        self.model_loaded = True
        logger.info("Model loaded successfully")

    def _load_model_cpu_fallback(self):
        """Load model on CPU as fallback."""
        from faster_whisper import WhisperModel

        logger.warning("Falling back to CPU mode")
        try:
            self.model = WhisperModel(
                self.config.model_name,
                device="cpu",
                compute_type=self.config.compute_type,
            )
            self.model_loaded = True
            self.config.device = "cpu"  # Update config
            logger.info("Model loaded successfully on CPU")
            return True
        except Exception as e:
            logger.error(f"Failed to load model on CPU: {e}")
            log_error(
                e,
                {
                    "stage": "cpu_fallback",
                    "model": self.config.model_name,
                },
            )
            return False

    def load_model(self):
        """Load the whisper model with comprehensive error handling."""
        with self._load_lock:
            if self.model_loaded:
                return

            self._load_attempts = 0
            original_device = self.config.device

            try:
                # Try loading with retry
                self._load_model_with_retry()
            except Exception as e:
                log_error(
                    e,
                    {
                        "stage": "initial_load",
                        "model": self.config.model_name,
                    },
                )

                # If CUDA failed, try CPU fallback
                if original_device == "cuda":
                    logger.info("CUDA failed, attempting CPU fallback")
                    success = self._load_model_cpu_fallback()
                    if not success:
                        raise ModelError.from_exception(
                            e, "load", self.config.model_name
                        )
                else:
                    # Re-raise as ModelError
                    raise ModelError.from_exception(e, "load", self.config.model_name)

    def ensure_model_loaded(self):
        """Ensure model is loaded before transcription."""
        if not self.model_loaded:
            self.load_model()

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text with error handling."""
        self.ensure_model_loaded()

        if audio is None or len(audio) == 0:
            logger.warning("Empty audio provided for transcription")
            return ""

        # Ensure audio is 1D
        if audio.ndim > 1:
            audio = audio.flatten()

        try:
            logger.info(
                f"Transcribing {len(audio) / self.config.sample_rate:.2f}s of audio"
            )

            # Model should be loaded by ensure_model_loaded()
            assert self.model is not None, "Model not loaded"

            segments, info = self.model.transcribe(
                audio,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            text = " ".join(segment.text.strip() for segment in segments)
            result = text.strip()

            if result:
                logger.info(f"Transcription successful: {result[:50]}...")
            else:
                logger.warning("Transcription returned empty result")

            return result

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            log_error(
                e,
                {
                    "stage": "transcription",
                    "model": self.config.model_name,
                    "audio_length": len(audio),
                    "sample_rate": self.config.sample_rate,
                },
            )
            raise TranscriptionError(f"Transcription failed: {e}")
