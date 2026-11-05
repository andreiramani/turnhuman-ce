"""TurnHuman Security & Hardening Module (v3.1.0-PROD).

Authoritative Specification: PLAN.md & .agents/security-hardening-specialist.md.
Features:
- Unicode zero-width & steganographic tracking character sanitizer.
- Directional formatting override & isolate defense (U+202A-U+202E, U+2066-U+2069).
- XSS prevention helpers and HTML entity escaping.
- File upload validation guards (10 MB limit, MIME/magic bytes inspection).
- Zip Slip and Zip Bomb (decompression bomb) mitigations for OpenXML (.docx) and .zip.
- Path traversal mitigation with absolute base enforcement.
- Strict Zero-Retention in-memory processing guarantees (no disk writes).
"""

from __future__ import annotations

import html
import io
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import zipfile

# =============================================================================
# 1. Security Exceptions
# =============================================================================


class SecurityError(Exception):
    """Base exception for all TurnHuman security violations."""


class FileValidationError(SecurityError):
    """Raised when an uploaded file fails integrity, size, or safety checks."""


class PathTraversalError(SecurityError):
    """Raised when an attempted path traversal is detected."""


# =============================================================================
# 2. Steganographic & Zero-Width Unicode Sanitizer
# =============================================================================

# Comprehensive set of hidden steganographic tracking & watermark characters:
# U+200B: Zero-Width Space (ZWSP)
# U+200C: Zero-Width Non-Joiner (ZWNJ)
# U+200D: Zero-Width Joiner (ZWJ)
# U+2060: Word Joiner (WJ)
# U+FEFF: Zero-Width No-Break Space (ZWNBSP / Byte Order Mark)
# U+200E: Left-to-Right Mark (LRM)
# U+200F: Right-to-Left Mark (RLM)
# U+00AD: Soft Hyphen (SHY)
# U+202A-U+202E: Directional embedding & overrides (LRE, RLE, PDF, LRO, RLO)
# U+2066-U+2069: Directional isolate controls (LRI, RLI, FSI, PDI)
ZERO_WIDTH_TRACKING_CHARS: re.Pattern[str] = re.compile(
    r"[\u200B\u200C\u200D\u2060\uFEFF\u200E\u200F\u00AD\u202A-\u202E\u2066-\u2069]"
)

UNICODE_STEGO_CHAR_NAMES: Dict[str, str] = {
    "\u200b": "Zero-Width Space (U+200B)",
    "\u200c": "Zero-Width Non-Joiner (U+200C)",
    "\u200d": "Zero-Width Joiner (U+200D)",
    "\u2060": "Word Joiner (U+2060)",
    "\ufeff": "Zero-Width No-Break Space / BOM (U+FEFF)",
    "\u200e": "Left-to-Right Mark (U+200E)",
    "\u200f": "Right-to-Left Mark (U+200F)",
    "\u00ad": "Soft Hyphen (U+00AD)",
    "\u202a": "Left-to-Right Embedding (U+202A)",
    "\u202b": "Right-to-Left Embedding (U+202B)",
    "\u202c": "Pop Directional Formatting (U+202C)",
    "\u202d": "Left-to-Right Override (U+202D)",
    "\u202e": "Right-to-Left Override (U+202E)",
    "\u2066": "Left-to-Right Isolate (U+2066)",
    "\u2067": "Right-to-Left Isolate (U+2067)",
    "\u2068": "First Strong Isolate (U+2068)",
    "\u2069": "Pop Directional Isolate (U+2069)",
}


def strip_zero_width_chars(text: str) -> str:
    """Aggressively sanitize and strip hidden steganographic tracking characters."""
    if not text:
        return text
    return ZERO_WIDTH_TRACKING_CHARS.sub("", text)


def has_zero_width_chars(text: str) -> bool:
    """Check whether text contains any steganographic or zero-width characters."""
    if not text:
        return False
    return bool(ZERO_WIDTH_TRACKING_CHARS.search(text))


def get_zero_width_report(text: str) -> Dict[str, Any]:
    """Inspect text and generate an audit report of detected zero-width characters."""
    if not text:
        return {"has_stego": False, "total_count": 0, "breakdown": {}}

    matches = ZERO_WIDTH_TRACKING_CHARS.findall(text)
    breakdown: Dict[str, int] = {}
    for char in matches:
        desc = UNICODE_STEGO_CHAR_NAMES.get(char, f"Hidden Code ({ord(char):#06x})")
        breakdown[desc] = breakdown.get(desc, 0) + 1

    return {
        "has_stego": len(matches) > 0,
        "total_count": len(matches),
        "breakdown": breakdown,
    }


# =============================================================================
# 3. XSS Sanitization & HTML Escaping
# =============================================================================

DANGEROUS_HTML_PATTERNS: re.Pattern[str] = re.compile(
    r"(?i)<\s*script\b|javascript\s*:|on\w+\s*=|data\s*:\s*text\/html|<\s*iframe\b"
)


def sanitize_html(text: Any) -> str:
    """Strictly escape text to prevent Cross-Site Scripting (XSS) in HTML rendering."""
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


def sanitize_for_attribute(text: Any) -> str:
    """Escape text safely for injection into HTML tag attributes."""
    if text is None:
        return ""
    safe = html.escape(str(text), quote=True)
    return safe.replace("\n", " ").replace("\r", " ").replace("\x00", "")


def is_potentially_malicious_xss(text: str) -> bool:
    """Detect whether input contains known XSS payload patterns."""
    if not text:
        return False
    return bool(DANGEROUS_HTML_PATTERNS.search(text))


# Alias for backward-compatible and intuitive naming
is_dangerous_markup = is_potentially_malicious_xss


# =============================================================================
# 4. File Upload Validation & Archive Hardening
# =============================================================================

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB strict limit
MAX_ZIP_UNCOMPRESSED_BYTES: int = 100 * 1024 * 1024  # 100 MB decompressed limit
MAX_ZIP_EXPANSION_RATIO: float = 100.0  # Max expansion ratio (Zip Bomb guard)
MAX_ZIP_ENTRY_COUNT: int = 500  # Max entries per archive

ALLOWED_EXTENSIONS: Set[str] = {
    ".docx",
    ".tex",
    ".txt",
    ".md",
    ".zip",
    ".py",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".sql",
    ".r",
    ".html",
}

# Magic bytes signatures for malicious executable / binary injection detection
DANGEROUS_BINARY_SIGNATURES: List[Tuple[bytes, str]] = [
    (b"MZ", "Windows PE Executable / DLL"),
    (b"\x7fELF", "Linux ELF Executable"),
    (b"\xca\xfe\xba\xbe", "Mach-O / Java Bytecode"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit (Reverse)"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit (Reverse)"),
]

ZIP_MAGIC_PREFIX: bytes = b"PK\x03\x04"


def validate_file_size(file_bytes: bytes, max_bytes: int = MAX_FILE_SIZE_BYTES) -> Tuple[bool, Optional[str]]:
    """Validate that file payload does not exceed maximum byte limit."""
    size = len(file_bytes)
    if size > max_bytes:
        size_mb = size / (1024 * 1024)
        limit_mb = max_bytes / (1024 * 1024)
        return False, f"File size ({size_mb:.2f} MB) exceeds maximum limit of {limit_mb:.0f} MB."
    return True, None


def validate_file_extension(filename: str, allowed: Optional[Set[str]] = None) -> Tuple[bool, Optional[str]]:
    """Validate that the file has a permitted extension."""
    if not filename:
        return False, "File name cannot be empty."

    allowed_exts = allowed if allowed is not None else ALLOWED_EXTENSIONS
    path = Path(filename)
    ext = path.suffix.lower()

    if not ext:
        return False, f"File '{filename}' has no extension. Allowed: {sorted(allowed_exts)}"

    if ext not in allowed_exts:
        return False, f"Extension '{ext}' is not permitted. Allowed: {sorted(allowed_exts)}"

    return True, None


def is_safe_zip_entry_name(entry_name: str) -> bool:
    """Verify that a ZIP entry path is free from Zip Slip traversal vectors."""
    if not entry_name or entry_name.startswith(("/", "\\")):
        return False
    if "\x00" in entry_name:
        return False

    norm = entry_name.replace("\\", "/")
    parts = norm.split("/")
    if any(p in ("..", "") for p in parts[:-1]):
        return False
    if parts[-1] == "..":
        return False

    if re.match(r"^[a-zA-Z]:", entry_name):
        return False

    return True


def validate_zip_archive(
    zip_source: Union[bytes, io.BytesIO],
    max_uncompressed_bytes: int = MAX_ZIP_UNCOMPRESSED_BYTES,
    max_ratio: float = MAX_ZIP_EXPANSION_RATIO,
    max_entries: int = MAX_ZIP_ENTRY_COUNT,
) -> Tuple[bool, Optional[str]]:
    """Audit ZIP archive integrity against Zip Slip, Zip Bombs, and entry spam."""
    stream = io.BytesIO(zip_source) if isinstance(zip_source, bytes) else zip_source

    try:
        with zipfile.ZipFile(stream, "r") as zf:
            infolist = zf.infolist()

            if len(infolist) > max_entries:
                return False, f"ZIP contains {len(infolist)} entries, exceeding safety limit ({max_entries})."

            total_uncompressed = 0
            total_compressed = 0

            for info in infolist:
                # Zip Slip check
                if not is_safe_zip_entry_name(info.filename):
                    return False, f"Malicious path traversal detected in ZIP entry: '{info.filename}'"

                total_uncompressed += info.file_size
                total_compressed += info.compress_size

                # Per-file Zip Bomb check (if uncompressed is non-trivial > 100KB)
                if info.file_size > 100_000 and info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > max_ratio:
                        return False, (
                            f"Suspicious compression ratio ({ratio:.1f}x) in '{info.filename}' "
                            f"(potential decompression bomb)."
                        )

            if total_uncompressed > max_uncompressed_bytes:
                limit_mb = max_uncompressed_bytes / (1024 * 1024)
                total_mb = total_uncompressed / (1024 * 1024)
                return False, (
                    f"Total uncompressed archive size ({total_mb:.1f} MB) exceeds safety threshold ({limit_mb:.0f} MB)."
                )

            return True, None

    except zipfile.BadZipFile:
        return False, "Corrupted or invalid ZIP archive."
    except Exception as exc:
        return False, f"ZIP archive validation failed: {exc}"


def validate_file_content(filename: str, file_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """Validate file content integrity, checking magic bytes and payload safety."""
    if not file_bytes:
        return False, "Uploaded file is empty (0 bytes)."

    path = Path(filename)
    ext = path.suffix.lower()

    # Reject dangerous executable binaries disguised as harmless documents
    for sig, desc in DANGEROUS_BINARY_SIGNATURES:
        if file_bytes.startswith(sig):
            return False, f"Dangerous executable header detected ({desc}). File rejected."

    # Validate OpenXML Word Document (.docx)
    if ext == ".docx":
        if not file_bytes.startswith(ZIP_MAGIC_PREFIX):
            return False, "Invalid Word document: Missing standard ZIP/OpenXML magic bytes."

        # Verify ZIP security (Zip Slip & Zip Bomb)
        zip_ok, zip_err = validate_zip_archive(file_bytes)
        if not zip_ok:
            return False, f"Invalid Word document package: {zip_err}"

        # Ensure essential OpenXML parts exist
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                names = set(zf.namelist())
                if "[Content_Types].xml" not in names and "word/document.xml" not in names:
                    return False, "Invalid Word document: Missing standard OpenXML package structures."
        except Exception:
            return False, "Malformed OpenXML Word package."

    # Validate generic ZIP archive
    elif ext == ".zip":
        if not file_bytes.startswith(ZIP_MAGIC_PREFIX):
            return False, "Invalid ZIP archive: Missing ZIP magic bytes."
        zip_ok, zip_err = validate_zip_archive(file_bytes)
        if not zip_ok:
            return False, zip_err

    # Validate plain text / LaTeX / code formats
    elif ext in {".txt", ".tex", ".md", ".py", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".go", ".rs", ".sql", ".r"}:
        if b"\x00" in file_bytes[:1024]:
            return False, "Text document contains binary null bytes (potential binary payload)."

    return True, None


def validate_upload(
    filename: str,
    file_bytes: bytes,
    max_size_mb: int = 10,
    allowed_extensions: Optional[Set[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """Comprehensive upload guard verifying extension, size, magic bytes, and archive safety."""
    max_bytes = max_size_mb * 1024 * 1024
    sz_ok, sz_err = validate_file_size(file_bytes, max_bytes=max_bytes)
    if not sz_ok:
        return False, sz_err

    ext_ok, ext_err = validate_file_extension(filename, allowed=allowed_extensions)
    if not ext_ok:
        return False, ext_err

    ct_ok, ct_err = validate_file_content(filename, file_bytes)
    if not ct_ok:
        return False, ct_err

    return True, None


# =============================================================================
# 5. Path Traversal & Safe Resolution Guard
# =============================================================================

def validate_safe_path(target_path: Union[str, Path], allowed_base: Union[str, Path]) -> Path:
    """Resolve and verify that target_path is strictly contained within allowed_base.

    Raises:
        PathTraversalError: If target_path resolves outside allowed_base.
    """
    base_resolved = Path(allowed_base).resolve()
    target_resolved = (base_resolved / Path(target_path)).resolve() if not Path(target_path).is_absolute() else Path(target_path).resolve()

    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise PathTraversalError(
            f"Path traversal detected! Path '{target_path}' resolves outside allowed base '{allowed_base}'."
        ) from exc

    return target_resolved
