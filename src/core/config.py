#!/usr/bin/env python3
"""
Configuration management for VoiceType.
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set

import yaml

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "voicetype"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "config.yaml"
SOCKET_PATH = Path(tempfile.gettempdir()) / "voicetype.sock"


@dataclass
class Config:
    """VoiceType configuration."""

    model_name: str = "distil-medium.en"
    device: str = "cuda"
    compute_type: str = "float16"
    sample_rate: int = 16000
    channels: int = 1
    silence_threshold: float = 0.01
    silence_duration: float = 1.5
    remove_fillers: bool = True
    auto_capitalize: bool = True
    auto_punctuate: bool = True
    trailing_punctuation: bool = True
    dictionary: Dict[str, str] = field(default_factory=dict)
    snippets: Dict[str, str] = field(default_factory=dict)
    app_overrides: Dict[str, dict] = field(default_factory=dict)
    auto_start: bool = False
    show_tray_icon: bool = True
    notify_recording_start: bool = True
    notify_recording_stop: bool = True

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        config = cls()

        # Copy default config if no config exists
        if not CONFIG_FILE.exists() and DEFAULT_CONFIG.exists():
            import shutil

            shutil.copy(DEFAULT_CONFIG, CONFIG_FILE)

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}

            # Update model settings
            if "model" in data:
                m = data["model"]
                config.model_name = m.get("name", config.model_name)
                config.device = m.get("device", config.device)
                config.compute_type = m.get(
                    "compute_type", config.compute_type
                )

            # Update audio settings
            if "audio" in data:
                a = data["audio"]
                config.sample_rate = a.get("sample_rate", config.sample_rate)
                config.channels = a.get("channels", config.channels)
                config.silence_threshold = a.get(
                    "silence_threshold", config.silence_threshold
                )
                config.silence_duration = a.get(
                    "silence_duration", config.silence_duration
                )

            # Update text processing settings
            if "text_processing" in data:
                t = data["text_processing"]
                config.remove_fillers = t.get(
                    "remove_fillers", config.remove_fillers
                )
                config.auto_capitalize = t.get(
                    "auto_capitalize", config.auto_capitalize
                )
                config.auto_punctuate = t.get(
                    "auto_punctuate", config.auto_punctuate
                )
                config.trailing_punctuation = t.get(
                    "trailing_punctuation", config.trailing_punctuation
                )

            # Update dictionaries and snippets
            config.dictionary = data.get("dictionary", {})
            config.snippets = data.get("snippets", {})
            config.app_overrides = data.get("app_overrides", {})

            # Update general settings
            if "general" in data:
                g = data["general"]
                config.auto_start = g.get("auto_start", config.auto_start)
                config.show_tray_icon = g.get(
                    "show_tray_icon", config.show_tray_icon
                )
                config.notify_recording_start = g.get(
                    "notify_recording_start", config.notify_recording_start
                )
                config.notify_recording_stop = g.get(
                    "notify_recording_stop", config.notify_recording_stop
                )

        return config

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary for serialization."""
        return {
            "model": {
                "name": self.model_name,
                "device": self.device,
                "compute_type": self.compute_type,
            },
            "audio": {
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "silence_threshold": self.silence_threshold,
                "silence_duration": self.silence_duration,
            },
            "text_processing": {
                "remove_fillers": self.remove_fillers,
                "auto_capitalize": self.auto_capitalize,
                "auto_punctuate": self.auto_punctuate,
                "trailing_punctuation": self.trailing_punctuation,
            },
            "dictionary": self.dictionary,
            "snippets": self.snippets,
            "app_overrides": self.app_overrides,
            "general": {
                "auto_start": self.auto_start,
                "show_tray_icon": self.show_tray_icon,
                "notify_recording_start": self.notify_recording_start,
                "notify_recording_stop": self.notify_recording_stop,
            },
        }

    def save(self) -> bool:
        """Save configuration to file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False)
            return True
        except Exception:
            return False


# Common filler words to remove
FILLER_WORDS: Set[str] = {
    "um",
    "uh",
    "umm",
    "uhh",
    "er",
    "err",
    "ah",
    "ahh",
    "like",
    "you know",
    "i mean",
    "sort of",
    "kind of",
    "basically",
    "literally",
    "actually",
    "honestly",
}
