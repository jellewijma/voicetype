#!/usr/bin/env python3
"""
Error recovery utilities for VoiceType.
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type

from .errors import VoiceTypeError

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    fallback: Optional[Callable] = None,
):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch and retry
        fallback: Fallback function to call if all retries fail

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for "
                        f"{func.__name__}: {exc}"
                    )

                    if attempt < max_attempts:
                        logger.info(f"Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            if fallback is not None:
                logger.info(f"Using fallback for {func.__name__}")
                return fallback(*args, **kwargs)

            if last_exception is not None:
                raise last_exception
            raise RuntimeError(
                f"Function {func.__name__} failed but no exception was captured"
            )

        return wrapper

    return decorator


class ErrorRecorder:
    """
    Records errors for later analysis and reporting.
    """

    def __init__(self, max_errors: int = 100):
        self.errors: list[dict[str, Any]] = []
        self.max_errors = max_errors

    def record(self, error: Exception) -> None:
        """
        Record an error.

        Args:
            error: Exception to record
        """
        error_data = {"timestamp": time.time(), "error": error}

        if isinstance(error, VoiceTypeError):
            error_data.update(error.to_dict())
        else:
            error_data.update(
                {
                    "error_type": error.__class__.__name__,
                    "message": str(error),
                }
            )

        self.errors.append(error_data)

        # Keep only recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]

    def get_recent_errors(self, count: int = 10) -> list:
        """
        Get most recent errors.

        Args:
            count: Number of recent errors to return

        Returns:
            List of recent errors
        """
        return self.errors[-count:]

    def clear(self) -> None:
        """Clear all recorded errors."""
        self.errors.clear()


# Global error recorder instance
error_recorder = ErrorRecorder()


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up structured logging for VoiceType.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress verbose logging from some libraries
    logging.getLogger("sounddevice").setLevel(logging.WARNING)
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    logging.getLogger("gi.repository").setLevel(logging.WARNING)


def log_error(error: Exception, context: Optional[dict] = None) -> None:
    """
    Log an error with context.

    Args:
        error: Exception to log
        context: Additional context information
    """
    if context is None:
        context = {}

    if isinstance(error, VoiceTypeError):
        error_data = error.to_dict()
        error_data.update(context)
        logger.error(f"VoiceTypeError: {error_data}")
    else:
        logger.error(
            f"{error.__class__.__name__}: {str(error)}",
            extra={"context": context, "error_type": error.__class__.__name__},
        )

    # Record error for later analysis
    error_recorder.record(error)
