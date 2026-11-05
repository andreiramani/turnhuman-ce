"""TurnHuman Document Processing Engine (v3.0.0-PROD).

Provides OpenXML (.docx) and LaTeX (.tex) document processing with:
- Run-level OpenXML preservation (bold, italic, font name, font size, color, highlight, underline).
- Table, header, footer, and footnote recursive traversal.
- Graceful skip for unsupported elements (SmartArt, embedded OLE objects, VBA macros).
- C2PA metadata stripping from .docx stream.
- LaTeX zone parsing (preamble isolation, math and citation protection).
- 100% in-memory ZIP packaging for zero-retention privacy.
"""

from __future__ import annotations

import datetime
import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import docx
from docx.text.run import Run

from TurnHuman.core.modifier import strip_zero_width_chars

logger = logging.getLogger("TurnHuman.core.doc_processor")


# =============================================================================
# Helper: Whitespace-Preserving Text Transformer
# =============================================================================

def _transform_run_text(text: str, transform_fn: Callable[[str], str]) -> str:
    """Apply transform_fn to text while strictly preserving leading/trailing whitespace."""
    if not text or not text.strip():
        return strip_zero_width_chars(text)

    # Sanitize steganographic zero-width Unicode tracking characters
    text = strip_zero_width_chars(text)
    leading_ws = text[: len(text) - len(text.lstrip())]
    trailing_ws = text[len(text.rstrip()) :]
    core = text.strip()

    try:
        transformed_core = transform_fn(core)
        # Strip in case transform_fn introduced external padding
        transformed_core = transformed_core.strip()
    except Exception as exc:
        logger.warning(f"Error during run text transform: {exc}; preserving original text.")
        transformed_core = core

    return f"{leading_ws}{strip_zero_width_chars(transformed_core)}{trailing_ws}"


# =============================================================================
# C2PA Stripping Engine
# =============================================================================

def strip_c2pa_from_zip(zip_stream: io.BytesIO) -> io.BytesIO:
    """Remove C2PA provenance and authenticity manifests from a ZIP-based file stream.

    Zero-retention in-memory filter: strips files under c2pa/ or ending with .c2pa,
    and removes C2PA relationships from package metadata.
    """
    zip_stream.seek(0)
    try:
        in_zip = zipfile.ZipFile(zip_stream, "r")
    except zipfile.BadZipFile:
        zip_stream.seek(0)
        return zip_stream

    has_c2pa = any(
        "c2pa" in name.lower() or name.lower().endswith(".c2pa")
        for name in in_zip.namelist()
    )
    if not has_c2pa:
        zip_stream.seek(0)
        return zip_stream

    out_stream = io.BytesIO()
    with zipfile.ZipFile(out_stream, "w", compression=zipfile.ZIP_DEFLATED) as out_zip:
        for item in in_zip.infolist():
            name_lower = item.filename.lower()
            if "c2pa" in name_lower or name_lower.endswith(".c2pa"):
                logger.info(f"Stripping C2PA metadata manifest: {item.filename}")
                continue

            content = in_zip.read(item.filename)
            # Remove any XML relationship tags pointing to c2pa
            if item.filename in ("[Content_Types].xml", "_rels/.rels"):
                content = re.sub(
                    rb'<Override[^>]*c2pa[^>]*/>',
                    b"",
                    content,
                    flags=re.IGNORECASE,
                )
                content = re.sub(
                    rb'<Relationship[^>]*c2pa[^>]*/>',
                    b"",
                    content,
                    flags=re.IGNORECASE,
                )
            out_zip.writestr(item, content)

    out_stream.seek(0)
    return out_stream


# =============================================================================
# Word Document (.docx) Preservation Engine
# =============================================================================

def _check_and_warn_unsupported_elements(doc: docx.Document) -> None:
    """Detect and log warnings for SmartArt, OLE objects, or VBA macros."""
    try:
        for rel_id, rel in list(doc.part.rels.items()):
            target_str = str(getattr(rel, "target_ref", "")).lower()
            rel_type = str(getattr(rel, "reltype", "")).lower()

            if "vba" in rel_type or "vba" in target_str or target_str.endswith(".bin"):
                logger.warning(
                    f"VBA macro detected ({rel.target_ref}); skipping safely without modifying macro."
                )
            if "diagram" in rel_type or "diagram" in target_str:
                logger.warning(
                    f"SmartArt diagram detected ({rel.target_ref}); skipping diagram internals."
                )
            if "oleobject" in rel_type or "oleobject" in target_str:
                logger.warning(
                    f"Embedded OLE object detected ({rel.target_ref}); preserving binary untouched."
                )
    except Exception as exc:
        logger.warning(f"Warning during unsupported elements check: {exc}")


def _process_paragraph(paragraph: Any, transform_fn: Callable[[str], str]) -> None:
    """Process all runs inside a paragraph, preserving font and styling attributes."""
    try:
        # Query all w:r elements (including those within hyperlinks)
        r_elements = paragraph._p.xpath(".//w:r")
        if not r_elements:
            return

        for r_elem in r_elements:
            try:
                run = Run(r_elem, paragraph)
                text = run.text
                if text and text.strip():
                    run.text = _transform_run_text(text, transform_fn)
            except Exception as exc:
                logger.warning(f"Skipping run due to exception: {exc}")
    except Exception as exc:
        logger.warning(f"Skipping paragraph due to exception: {exc}")


def _process_table(table: Any, transform_fn: Callable[[str], str]) -> None:
    """Recursively process all cells, paragraphs, and nested tables in a table."""
    try:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _process_paragraph(p, transform_fn)
                for nested_table in cell.tables:
                    _process_table(nested_table, transform_fn)
    except Exception as exc:
        logger.warning(f"Skipping table element due to exception: {exc}")


def _process_sections(doc: docx.Document, transform_fn: Callable[[str], str]) -> None:
    """Process headers and footers across all sections."""
    for section in doc.sections:
        # Check all possible header varieties
        headers_to_check = [
            getattr(section, "header", None),
            getattr(section, "first_page_header", None),
            getattr(section, "even_page_header", None),
        ]
        for hdr in headers_to_check:
            if hdr is not None:
                try:
                    for p in hdr.paragraphs:
                        _process_paragraph(p, transform_fn)
                    for tbl in hdr.tables:
                        _process_table(tbl, transform_fn)
                except Exception as exc:
                    logger.warning(f"Skipping header element: {exc}")

        # Check all possible footer varieties
        footers_to_check = [
            getattr(section, "footer", None),
            getattr(section, "first_page_footer", None),
            getattr(section, "even_page_footer", None),
        ]
        for ftr in footers_to_check:
            if ftr is not None:
                try:
                    for p in ftr.paragraphs:
                        _process_paragraph(p, transform_fn)
                    for tbl in ftr.tables:
                        _process_table(tbl, transform_fn)
                except Exception as exc:
                    logger.warning(f"Skipping footer element: {exc}")


def _process_footnotes(doc: docx.Document, transform_fn: Callable[[str], str]) -> None:
    """Process footnote and endnote parts in the OpenXML package if present."""
    try:
        from docx.oxml import parse_xml

        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        ns_map = {"w": w_ns}

        for part in doc.part.package.parts:
            partname = str(part.partname).lower()
            if "footnote" in partname or "endnote" in partname:
                try:
                    root = parse_xml(part.blob)
                    # Process text nodes in footnotes, skipping footnoteRef / separator
                    try:
                        r_elements = root.xpath(".//w:r", namespaces=ns_map)
                    except TypeError:
                        r_elements = root.xpath(".//w:r")

                    for r_elem in r_elements:
                        try:
                            has_ref = bool(r_elem.xpath(".//w:footnoteRef | .//w:endnoteRef", namespaces=ns_map))
                        except TypeError:
                            has_ref = bool(r_elem.xpath(".//w:footnoteRef | .//w:endnoteRef"))

                        if has_ref:
                            continue

                        try:
                            t_elements = r_elem.xpath(".//w:t", namespaces=ns_map)
                        except TypeError:
                            t_elements = r_elem.xpath(".//w:t")

                        for t_elem in t_elements:
                            if t_elem.text and t_elem.text.strip():
                                t_elem.text = _transform_run_text(t_elem.text, transform_fn)

                    if hasattr(root, "xml"):
                        part._blob = root.xml.encode("utf-8")
                    else:
                        import lxml.etree
                        part._blob = lxml.etree.tostring(root, encoding="utf-8")
                except Exception as exc:
                    logger.warning(f"Error parsing footnote part {part.partname}: {exc}")
    except Exception as exc:
        logger.warning(f"Footnote processing skipped: {exc}")


def process_docx(
    docx_input: Union[str, Path, bytes, io.BytesIO],
    transform_fn: Optional[Callable[[str], str]] = None,
    **kwargs: Any,
) -> io.BytesIO:
    """Process a Word (.docx) document, preserving formatting, layout, and OpenXML tags.

    Args:
        docx_input: File path, raw bytes, or BytesIO containing the docx document.
        transform_fn: Optional string transformer callable. If None, uses humanize_text with kwargs.
        **kwargs: Extra parameters passed to humanize_text if transform_fn is None.

    Returns:
        io.BytesIO containing the modified, C2PA-cleared docx document.
    """
    if transform_fn is None:
        from TurnHuman.core.modifier import humanize_text

        transform_fn = lambda text: humanize_text(text, **kwargs)[0]

    # Convert input to in-memory stream
    if isinstance(docx_input, (str, Path)):
        stream = io.BytesIO(Path(docx_input).read_bytes())
    elif isinstance(docx_input, bytes):
        stream = io.BytesIO(docx_input)
    elif isinstance(docx_input, io.BytesIO):
        stream = io.BytesIO(docx_input.getvalue())
    else:
        raise TypeError(f"Unsupported docx_input type: {type(docx_input)}")

    doc = docx.Document(stream)
    _check_and_warn_unsupported_elements(doc)

    # 1. Process main document paragraphs
    for p in doc.paragraphs:
        _process_paragraph(p, transform_fn)

    # 2. Process tables
    for table in doc.tables:
        _process_table(table, transform_fn)

    # 3. Process headers and footers
    _process_sections(doc, transform_fn)

    # 4. Process footnotes and endnotes
    _process_footnotes(doc, transform_fn)

    # 5. Save to in-memory BytesIO
    out_io = io.BytesIO()
    doc.save(out_io)
    out_io.seek(0)

    # 6. Clean C2PA metadata from stream
    cleaned_io = strip_c2pa_from_zip(out_io)
    return cleaned_io



from TurnHuman.core.latex_processor import process_latex

__all__ = [
    "process_docx",
    "process_latex",
    "create_in_memory_zip",
    "strip_c2pa_from_zip",
    "_check_and_warn_unsupported_elements",
]

# =============================================================================
# In-Memory ZIP Bundler
# =============================================================================

def create_in_memory_zip(
    file_dict: Dict[str, Union[bytes, str, io.BytesIO]],
    zip_name_prefix: str = "TurnHuman_Humanized_Docs",
) -> Tuple[str, io.BytesIO]:
    """Bundle processed documents into an in-memory ZIP archive.

    100% in-memory via io.BytesIO without writing to disk (zero-retention privacy).

    Args:
        file_dict: Mapping of filename to file content (bytes, str, or BytesIO).
        zip_name_prefix: Prefix for the generated zip filename.

    Returns:
        Tuple of (zip_filename, zip_buffer_stream).
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{zip_name_prefix}_{timestamp}.zip"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in file_dict.items():
            if isinstance(content, io.BytesIO):
                data = content.getvalue()
            elif isinstance(content, str):
                data = content.encode("utf-8")
            elif isinstance(content, bytes):
                data = content
            else:
                raise TypeError(f"Unsupported content type for file {filename}: {type(content)}")

            zf.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_filename, zip_buffer
