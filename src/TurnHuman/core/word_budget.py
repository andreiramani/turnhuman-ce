"""Word Budget Controller & Unicode Steganography Sanitizer (v3.0.1-MODULAR)."""

from __future__ import annotations

import re
from typing import Any, Dict, Set

# =============================================================================
# Steganographic Tracking Character Sanitizer (Zero-Width Unicode)
# =============================================================================

# Character ranges for hidden steganographic tracking / AI watermarking:
# U+200B: Zero-Width Space
# U+200C: Zero-Width Non-Joiner
# U+200D: Zero-Width Joiner
# U+2060: Word Joiner
# U+FEFF: Zero-Width No-Break Space (Byte Order Mark)
# U+200E: Left-to-Right Mark
# U+200F: Right-to-Left Mark
# U+00AD: Soft Hyphen
# U+202A-U+202E: Directional formatting codes
# U+2066-U+2069: Directional isolate controls
ZERO_WIDTH_TRACKING_CHARS: re.Pattern[str] = re.compile(
    r"[\u200B\u200C\u200D\u2060\uFEFF\u200E\u200F\u00AD\u202A-\u202E\u2066-\u2069]"
)


def strip_zero_width_chars(text: str) -> str:
    """Sanitize and strip hidden steganographic zero-width Unicode tracking characters."""
    if not text:
        return text
    return ZERO_WIDTH_TRACKING_CHARS.sub("", text)


class WordBudgetController:
    """Controls and audits word count deltas across all pipeline stages.

    In 'zero_expansion' mode, strictly disables stages {7, 10, 11, 13, 14}
    and enforces net words added == 0.
    """

    ZE_DISABLED_STAGES: Set[int] = {7, 10, 11, 13, 14}

    def __init__(self, mode: str = "full") -> None:
        self.mode = mode.strip().lower()
        self.stage_deltas: Dict[str, int] = {}

    def is_stage_enabled(self, stage_num: int) -> bool:
        """Return False for ZE-incompatible stages when in zero_expansion mode."""
        if self.mode == "zero_expansion":
            return stage_num not in self.ZE_DISABLED_STAGES
        return True

    def record_delta(self, stage_name: str, before: int, after: int) -> None:
        """Record the word count delta produced by a specific stage."""
        self.stage_deltas[stage_name] = after - before

    def get_telemetry(self) -> Dict[str, Any]:
        """Retrieve word budget delta summary."""
        return {
            "mode": self.mode,
            "deltas": dict(self.stage_deltas),
            "total_delta": sum(self.stage_deltas.values()),
        }
