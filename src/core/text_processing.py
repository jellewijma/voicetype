#!/usr/bin/env python3
"""
Text processing and post-processing for transcriptions.
"""

import re

from .config import FILLER_WORDS, Config


class TextProcessor:
    """Processes transcribed text (remove fillers, apply dictionary, etc.)."""

    def __init__(self, config: Config):
        self.config = config

    def process(self, text: str) -> str:
        """Apply all text processing steps."""
        if not text:
            return ""

        text = self._remove_fillers(text)
        text = self._apply_dictionary(text)
        text = self._apply_snippets(text)
        text = self._smart_capitalize(text)
        text = self._smart_punctuate(text)

        return text

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words (um, uh, like, etc.)."""
        if not self.config.remove_fillers:
            return text

        words = text.lower().split()
        filtered = []
        i = 0

        while i < len(words):
            word = words[i]

            # Check single word
            if word in FILLER_WORDS:
                i += 1
                continue

            # Check bigrams
            if i + 1 < len(words):
                bigram = f"{word} {words[i + 1]}"
                if bigram in FILLER_WORDS:
                    i += 2
                    continue

            # Check trigrams
            if i + 2 < len(words):
                trigram = f"{word} {words[i + 1]} {words[i + 2]}"
                if trigram in FILLER_WORDS:
                    i += 3
                    continue

            filtered.append(words[i])
            i += 1

        result = " ".join(filtered)
        return result

    def _apply_dictionary(self, text: str) -> str:
        """Apply personal dictionary replacements."""
        if not self.config.dictionary:
            return text

        for word, replacement in self.config.dictionary.items():
            pattern = r"\b" + re.escape(word) + r"\b"
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _apply_snippets(self, text: str) -> str:
        """Expand snippets (text shortcuts)."""
        if not self.config.snippets:
            return text

        for trigger, expansion in self.config.snippets.items():
            if trigger.lower() in text.lower():
                pattern = re.escape(trigger)
                text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)

        return text

    def _smart_capitalize(self, text: str) -> str:
        """Capitalize sentences."""
        if not self.config.auto_capitalize:
            return text

        sentences = re.split(r"([.!?]+\s*)", text)
        result = []

        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:
                part = part[0].upper() + part[1:] if part else part
            result.append(part)

        return "".join(result)

    def _smart_punctuate(self, text: str) -> str:
        """Add trailing punctuation if missing."""
        if not self.config.auto_punctuate:
            return text

        if text and not text[-1] in ".!?":
            if self.config.trailing_punctuation:
                text = text + "."

        return text
