"""TurnHuman Stateful Code Comment Processor Facade (v3.0.1-MODULAR)."""

from __future__ import annotations

from typing import Callable, Optional

from TurnHuman.core.code_persona import (
    PERSONA_VOCABULARY,
    apply_developer_persona,
)
from TurnHuman.core.code_scanner import (
    ScannerState,
    _normalize_language,
    _process_block_comment,
    _process_html_comment,
    _process_line_comment,
    _transform_comment_text,
    scan_and_rewrite_code,
)

__all__ = [
    "ScannerState",
    "process_code",
    "apply_developer_persona",
    "_normalize_language",
    "_transform_comment_text",
    "PERSONA_VOCABULARY",
]


def process_code(
    code_str: str,
    language: str = "python",
    persona: str = "intermediate",
    transform_fn: Optional[Callable[[str], str]] = None,
) -> str:
    """Scan and transform comments in code while maintaining 100% executable integrity.

    Operates via a state-machine scanner that accurately isolates strings and comments.
    Code statements, variable names, keywords, and strings containing comment characters
    (like URLs or regex patterns) are guaranteed untouched.

    Args:
        code_str: Source code content as a string.
        language: Programming language ('python', 'c', 'cpp', 'java', 'js', 'ts', 'rust', 'go', 'sql', 'bash', 'r', 'html').
        persona: Developer persona ('beginner', 'intermediate', 'senior').
        transform_fn: Optional custom comment string transformer callable.

    Returns:
        Source code with comments humanized according to the requested persona.
    """
    canon_lang = _normalize_language(language)
    return scan_and_rewrite_code(
        code_str=code_str,
        canon_lang=canon_lang,
        persona=persona,
        transform_fn=transform_fn,
    )
