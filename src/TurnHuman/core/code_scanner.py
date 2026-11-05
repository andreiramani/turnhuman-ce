"""TurnHuman Stateful Quote-Aware Code Comment Scanner (v3.0.1-MODULAR)."""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Callable, List, Optional

from TurnHuman.core.code_persona import apply_developer_persona
from TurnHuman.core.word_budget import strip_zero_width_chars

logger = logging.getLogger("TurnHuman.core.code_scanner")

class ScannerState(str, Enum):
    """Lexical scanning states for the character-by-character scanner."""

    NORMAL = "NORMAL"
    IN_SINGLE_QUOTE = "IN_SINGLE_QUOTE"
    IN_DOUBLE_QUOTE = "IN_DOUBLE_QUOTE"
    IN_TRIPLE_SINGLE = "IN_TRIPLE_SINGLE"
    IN_TRIPLE_DOUBLE = "IN_TRIPLE_DOUBLE"
    IN_BACKTICK = "IN_BACKTICK"



def _normalize_language(lang: str) -> str:
    """Normalize language identifier string to canonical family."""
    l = lang.strip().lower()
    if l in ("python", "py"):
        return "python"
    if l in ("bash", "sh", "zsh"):
        return "bash"
    if l in ("r",):
        return "r"
    if l in ("c", "h"):
        return "c"
    if l in ("cpp", "c++", "cc", "cxx", "hpp"):
        return "cpp"
    if l in ("java",):
        return "java"
    if l in ("javascript", "js", "jsx"):
        return "javascript"
    if l in ("typescript", "ts", "tsx"):
        return "typescript"
    if l in ("rust", "rs"):
        return "rust"
    if l in ("go",):
        return "go"
    if l in ("sql", "pgsql", "mysql", "sqlite", "plsql"):
        return "sql"
    if l in ("html", "xml", "htm", "xhtml", "svg"):
        return "html"
    return "python"


def _transform_comment_text(
    comment_body: str,
    persona: str,
    transform_fn: Optional[Callable[[str], str]] = None,
) -> str:
    """Transform comment body with persona adaptation and optional transform_fn."""
    stripped = comment_body.strip()
    if not stripped:
        return comment_body

    # Preserve shebangs, encoding pragmas, and linter directives untouched
    if stripped.startswith("#!"):
        return comment_body
    if re.search(
        r"\b(?:noqa|type:\s*ignore|pylint:|flake8:|mypy:|@ts-|eslint|clang-format)\b",
        stripped,
    ):
        return comment_body
    if re.search(r"^coding[:=]\s*[-\w.]+", stripped):
        return comment_body

    # Apply developer persona vocabulary
    adapted = apply_developer_persona(comment_body, persona)
    adapted = strip_zero_width_chars(adapted)

    # Apply custom transform_fn if provided
    if transform_fn is not None:
        try:
            adapted = transform_fn(adapted)
        except Exception as exc:
            logger.warning(f"Error in transform_fn: {exc}; preserving adapted comment.")

    return adapted


def _process_line_comment(
    raw_comment: str,
    persona: str,
    transform_fn: Optional[Callable[[str], str]],
) -> str:
    """Transform a single-line comment (#, //, --)."""
    # Preserve shebang
    if raw_comment.startswith("#!"):
        return raw_comment

    m = re.match(r"^(\s*(?:#+|//+|--+))(\s*)(.*)$", raw_comment)
    if not m:
        return raw_comment

    delimiter = m.group(1)
    spaces = m.group(2)
    body = m.group(3)

    if not body.strip():
        return raw_comment

    transformed_body = _transform_comment_text(body, persona, transform_fn)
    return f"{delimiter}{spaces}{transformed_body}"


def _process_block_comment(
    raw_block: str,
    persona: str,
    transform_fn: Optional[Callable[[str], str]],
) -> str:
    """Transform a C-style block comment (/* ... */)."""
    if not (raw_block.startswith("/*") and raw_block.endswith("*/")):
        return raw_block

    inner = raw_block[2:-2]
    lines = inner.split("\n")
    new_lines: List[str] = []

    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue

        # Match C-style asterisk lines: " * comment text"
        star_match = re.match(r"^(\s*\*\s?)(.*)$", line)
        if star_match:
            star_prefix = star_match.group(1)
            line_body = star_match.group(2)
            if line_body.strip():
                new_body = _transform_comment_text(line_body, persona, transform_fn)
                new_lines.append(f"{star_prefix}{new_body}")
            else:
                new_lines.append(line)
            continue

        # Otherwise preserve leading whitespace
        ws_match = re.match(r"^(\s*)(.*)$", line)
        if ws_match and ws_match.group(2).strip():
            lead_ws = ws_match.group(1)
            line_body = ws_match.group(2)
            new_body = _transform_comment_text(line_body, persona, transform_fn)
            new_lines.append(f"{lead_ws}{new_body}")
        else:
            new_lines.append(line)

    return f"/*{chr(10).join(new_lines)}*/"


def _process_html_comment(
    raw_html: str,
    persona: str,
    transform_fn: Optional[Callable[[str], str]],
) -> str:
    """Transform an HTML / XML comment (<!-- ... -->)."""
    if not (raw_html.startswith("<!--") and raw_html.endswith("-->")):
        return raw_html

    inner = raw_html[4:-3]
    ws_match = re.match(r"^(\s*)(.*?)(\s*)$", inner, re.DOTALL)
    if ws_match:
        l_ws, body, r_ws = ws_match.groups()
        if body.strip():
            new_body = _transform_comment_text(body, persona, transform_fn)
            return f"<!--{l_ws}{new_body}{r_ws}-->"

    return raw_html



def scan_and_rewrite_code(
    code_str: str,
    canon_lang: str,
    persona: str = "intermediate",
    transform_fn: Optional[Callable[[str], str]] = None,
) -> str:
    """Core character-by-character state machine scanner."""
    code_str = strip_zero_width_chars(code_str)
    n = len(code_str)
    i = 0
    state = ScannerState.NORMAL
    out_pieces: List[str] = []

    while i < n:
        if state == ScannerState.NORMAL:
            # --- 1. Python Specific Multi-line / Triple Quotes ---
            if canon_lang == "python":
                if code_str[i : i + 3] == '"""':
                    state = ScannerState.IN_TRIPLE_DOUBLE
                    out_pieces.append('"""')
                    i += 3
                    continue
                if code_str[i : i + 3] == "'''":
                    state = ScannerState.IN_TRIPLE_SINGLE
                    out_pieces.append("'''")
                    i += 3
                    continue

            # --- 2. Comments in Line-Based Languages (#) ---
            if canon_lang in ("python", "bash", "r"):
                if code_str[i] == "#":
                    start = i
                    while i < n and code_str[i] != "\n":
                        i += 1
                    raw_comment = code_str[start:i]
                    processed = _process_line_comment(raw_comment, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

            # --- 3. Comments in C-Family / SQL / HTML ---
            if canon_lang in ("c", "cpp", "java", "javascript", "typescript", "rust", "go"):
                # C-style line comment: //
                if code_str[i : i + 2] == "//":
                    start = i
                    while i < n and code_str[i] != "\n":
                        i += 1
                    raw_comment = code_str[start:i]
                    processed = _process_line_comment(raw_comment, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

                # C-style block comment: /* ... */
                if code_str[i : i + 2] == "/*":
                    start = i
                    i += 2
                    while i < n:
                        # Skip literal comment examples in text like "/* */" (5 chars)
                        if code_str[i : i + 5] == "/* */":
                            i += 5
                        elif code_str[i : i + 2] == "*/":
                            i += 2
                            break
                        else:
                            i += 1
                    raw_block = code_str[start:i]
                    processed = _process_block_comment(raw_block, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

                # JS/TS/Go backtick strings
                if code_str[i] == "`" and canon_lang in ("javascript", "typescript", "go"):
                    state = ScannerState.IN_BACKTICK
                    out_pieces.append("`")
                    i += 1
                    continue

            if canon_lang == "sql":
                # SQL line comment: --
                if code_str[i : i + 2] == "--":
                    start = i
                    while i < n and code_str[i] != "\n":
                        i += 1
                    raw_comment = code_str[start:i]
                    processed = _process_line_comment(raw_comment, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

                # SQL block comment: /* ... */
                if code_str[i : i + 2] == "/*":
                    start = i
                    i += 2
                    while i < n:
                        if code_str[i : i + 5] == "/* */":
                            i += 5
                        elif code_str[i : i + 2] == "*/":
                            i += 2
                            break
                        else:
                            i += 1
                    raw_block = code_str[start:i]
                    processed = _process_block_comment(raw_block, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

            if canon_lang == "html":
                # HTML block comment: <!-- ... -->
                if code_str[i : i + 4] == "<!--":
                    start = i
                    i += 4
                    while i < n and code_str[i : i + 3] != "-->":
                        i += 1
                    if i < n:
                        i += 3
                    raw_html = code_str[start:i]
                    processed = _process_html_comment(raw_html, persona, transform_fn)
                    out_pieces.append(processed)
                    continue

            # --- 4. String Literals Transitions ---
            if code_str[i] == '"':
                state = ScannerState.IN_DOUBLE_QUOTE
                out_pieces.append('"')
                i += 1
                continue

            if code_str[i] == "'":
                state = ScannerState.IN_SINGLE_QUOTE
                out_pieces.append("'")
                i += 1
                continue

            # Regular code character
            out_pieces.append(code_str[i])
            i += 1

        elif state == ScannerState.IN_DOUBLE_QUOTE:
            if code_str[i] == "\\":
                # Escaped character: consume '\' and next char together
                out_pieces.append(code_str[i : i + 2])
                i += 2
            elif code_str[i] == '"':
                state = ScannerState.NORMAL
                out_pieces.append('"')
                i += 1
            elif code_str[i] == "\n" and canon_lang not in ("python", "bash"):
                state = ScannerState.NORMAL
                out_pieces.append("\n")
                i += 1
            else:
                out_pieces.append(code_str[i])
                i += 1

        elif state == ScannerState.IN_SINGLE_QUOTE:
            if code_str[i] == "\\":
                out_pieces.append(code_str[i : i + 2])
                i += 2
            elif canon_lang == "sql" and code_str[i : i + 2] == "''":
                # SQL escaped single quote
                out_pieces.append("''")
                i += 2
            elif code_str[i] == "'":
                state = ScannerState.NORMAL
                out_pieces.append("'")
                i += 1
            elif code_str[i] == "\n" and canon_lang not in ("python", "bash"):
                state = ScannerState.NORMAL
                out_pieces.append("\n")
                i += 1
            else:
                out_pieces.append(code_str[i])
                i += 1

        elif state == ScannerState.IN_BACKTICK:
            if code_str[i] == "\\":
                out_pieces.append(code_str[i : i + 2])
                i += 2
            elif code_str[i] == "`":
                state = ScannerState.NORMAL
                out_pieces.append("`")
                i += 1
            else:
                out_pieces.append(code_str[i])
                i += 1

        elif state == ScannerState.IN_TRIPLE_DOUBLE:
            if code_str[i] == "\\":
                out_pieces.append(code_str[i : i + 2])
                i += 2
            elif code_str[i : i + 3] == '"""':
                state = ScannerState.NORMAL
                out_pieces.append('"""')
                i += 3
            else:
                out_pieces.append(code_str[i])
                i += 1

        elif state == ScannerState.IN_TRIPLE_SINGLE:
            if code_str[i] == "\\":
                out_pieces.append(code_str[i : i + 2])
                i += 2
            elif code_str[i : i + 3] == "'''":
                state = ScannerState.NORMAL
                out_pieces.append("'''")
                i += 3
            else:
                out_pieces.append(code_str[i])
                i += 1

    return "".join(out_pieces)
