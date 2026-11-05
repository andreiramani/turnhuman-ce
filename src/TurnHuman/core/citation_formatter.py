"""Academic Citation & Bibliography Formatters (BibTeX, APA, IEEE, Chicago) (v3.0.1-MODULAR)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("TurnHuman.core.citation_formatter")

# Author Extraction & Formatting Utilities

def _extract_author_parts(author: Any) -> Tuple[str, str]:
    """Extract (given_names, family_name) from string or dict."""
    if isinstance(author, dict):
        family = str(author.get("family", "")).strip()
        given = str(author.get("given", "")).strip()
        if not family and "name" in author:
            parts = str(author["name"]).strip().split()
            if len(parts) > 1:
                return " ".join(parts[:-1]), parts[-1]
            return "", str(author["name"]).strip()
        return given, family

    author_str = str(author).strip()
    if not author_str:
        return "", "Unknown"

    if "," in author_str:
        parts = [p.strip() for p in author_str.split(",", 1)]
        return parts[1] if len(parts) > 1 else "", parts[0]

    parts = author_str.split()
    if len(parts) > 1:
        return " ".join(parts[:-1]), parts[-1]
    return "", author_str


def _get_family_name(author: Any) -> str:
    """Retrieve family / surname of an author."""
    _, family = _extract_author_parts(author)
    return family or "Unknown"


def _format_author_initials(given: str) -> str:
    """Format given name to initials (e.g. 'Ashish' -> 'A.', 'Steven L.' -> 'S. L.')."""
    if not given:
        return ""
    initials = []
    for token in re.findall(r"\b[A-Za-z]", given):
        initials.append(f"{token.upper()}.")
    return " ".join(initials)


def _format_author_bibtex(authors: List[Any]) -> str:
    """Format authors list for BibTeX ('Family, Given and Family2, Given2')."""
    if not authors:
        return "Unknown"
    formatted = []
    for a in authors:
        given, family = _extract_author_parts(a)
        if given:
            formatted.append(f"{family}, {given}")
        else:
            formatted.append(family)
    return " and ".join(formatted)


def _format_author_apa_list(authors: List[Any]) -> str:
    """Format authors list for APA 7th bibliography."""
    if not authors:
        return "Unknown"
    formatted = []
    for a in authors:
        given, family = _extract_author_parts(a)
        initials = _format_author_initials(given)
        formatted.append(f"{family}, {initials}" if initials else family)

    n = len(formatted)
    if n == 1:
        return formatted[0]
    if n == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    if n <= 20:
        return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
    return ", ".join(formatted[:19]) + f", ... {formatted[-1]}"


def _format_author_ieee_list(authors: List[Any]) -> str:
    """Format authors list for IEEE bibliography."""
    if not authors:
        return "Unknown"
    formatted = []
    for a in authors:
        given, family = _extract_author_parts(a)
        initials = _format_author_initials(given)
        formatted.append(f"{initials} {family}" if initials else family)

    n = len(formatted)
    if n == 1:
        return formatted[0]
    if n == 2:
        return f"{formatted[0]} and {formatted[1]}"
    if n <= 6:
        return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"
    return f"{formatted[0]} et al."


def _generate_citation_key(paper: Dict[str, Any]) -> str:
    """Generate a clean BibTeX citation key from paper metadata."""
    if paper.get("key"):
        return re.sub(r"[^a-zA-Z0-9_\-]", "", str(paper["key"]))

    authors = paper.get("authors", [])
    primary_fam = _get_family_name(authors[0]) if authors else "ref"
    primary_fam = re.sub(r"[^a-zA-Z0-9]", "", primary_fam.lower()) or "ref"

    year = str(paper.get("year", "2026"))
    year_digits = re.findall(r"\d{4}", year)
    year_clean = year_digits[0] if year_digits else "2026"

    title = str(paper.get("title", ""))
    title_words = re.findall(r"[a-zA-Z]{3,}", title.lower())
    # Exclude common stop words
    stopwords = {"the", "and", "for", "with", "from", "that", "this"}
    title_word = next((w for w in title_words if w not in stopwords), "paper")

    return f"{primary_fam}{year_clean}{title_word}"


def format_in_text_citation(
    paper: Dict[str, Any],
    index: int = 1,
    style: str = "latex",
) -> str:
    """Format an in-text citation marker based on requested style.

    Supported styles:
    - 'numeric': '[1]'
    - 'apa': '(Author et al., 2017)'
    - 'latex': '\\cite{key}'
    - 'inline_bracket': '[Author et al., 2017]'
    """
    normalized_style = style.strip().lower()

    if normalized_style == "numeric":
        return f"[{index}]"

    key = paper.get("key") or _generate_citation_key(paper)
    if normalized_style == "latex":
        return f"\\cite{{{key}}}"

    authors = paper.get("authors", [])
    year_str = str(paper.get("year", "n.d."))

    if not authors:
        marker_body = f"{paper.get('title', 'Unknown')[:15]}..., {year_str}"
    else:
        fam1 = _get_family_name(authors[0])
        if len(authors) == 1:
            marker_body = f"{fam1}, {year_str}"
        elif len(authors) == 2:
            fam2 = _get_family_name(authors[1])
            marker_body = f"{fam1} & {fam2}, {year_str}"
        else:
            marker_body = f"{fam1} et al., {year_str}"

    if normalized_style == "apa":
        return f"({marker_body})"
    if normalized_style == "inline_bracket":
        return f"[{marker_body}]"

    # Default fallback
    return f"\\cite{{{key}}}"


def to_bibtex(paper: Dict[str, Any]) -> str:
    """Generate an RFC-compliant BibTeX entry string from paper metadata."""
    key = paper.get("key") or _generate_citation_key(paper)
    entry_type = str(paper.get("type", "article")).lower()

    # Map CrossRef / taxonomy types to canonical BibTeX entry types
    if "proceedings" in entry_type or "conference" in entry_type:
        bib_type = "inproceedings"
    elif "book" in entry_type or "monograph" in entry_type:
        bib_type = "book"
    elif "misc" in entry_type or paper.get("_fallback"):
        bib_type = "misc" if not paper.get("journal") else "article"
    else:
        bib_type = "article"

    authors = paper.get("authors", [])
    author_str = _format_author_bibtex(authors)
    title = str(paper.get("title", "")).strip()

    lines = [f"@{bib_type}{{{key},"]
    lines.append(f"  title = {{{title}}},")
    lines.append(f"  author = {{{author_str}}},")

    journal = paper.get("journal") or paper.get("container-title")
    if journal:
        field_name = "booktitle" if bib_type == "inproceedings" else "journal"
        lines.append(f"  {field_name} = {{{journal}}},")

    year = paper.get("year")
    if year:
        lines.append(f"  year = {{{year}}},")

    volume = paper.get("volume")
    if volume:
        lines.append(f"  volume = {{{volume}}},")

    issue = paper.get("issue") or paper.get("number")
    if issue:
        lines.append(f"  number = {{{issue}}},")

    pages = paper.get("pages") or paper.get("page")
    if pages:
        # Standardize page hyphens in BibTeX (e.g. 100-110 -> 100--110)
        norm_pages = re.sub(r"(?<=\d)-(?=\d)", "--", str(pages))
        lines.append(f"  pages = {{{norm_pages}}},")

    doi = paper.get("doi") or paper.get("DOI")
    if doi:
        lines.append(f"  doi = {{{doi}}},")

    url = paper.get("url") or paper.get("URL")
    if url and not doi:
        lines.append(f"  url = {{{url}}},")

    note = paper.get("note")
    if note:
        lines.append(f"  note = {{{note}}},")

    # Remove trailing comma on last attribute line
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")

    return "\n".join(lines)


def _to_apa_bibliography(paper: Dict[str, Any]) -> str:
    """Format single paper as an APA 7th edition bibliography entry."""
    authors = paper.get("authors", [])
    author_str = _format_author_apa_list(authors)
    year = paper.get("year", "n.d.")
    title = str(paper.get("title", "")).strip()
    journal = paper.get("journal") or paper.get("container-title", "")
    volume = paper.get("volume")
    pages = paper.get("pages") or paper.get("page")
    doi = paper.get("doi") or paper.get("DOI")

    parts = [f"{author_str} ({year}). {title}."]
    if journal:
        journal_part = f" *{journal}*"
        if volume:
            journal_part += f", *{volume}*"
            issue = paper.get("issue") or paper.get("number")
            if issue:
                journal_part += f"({issue})"
        if pages:
            journal_part += f", {pages}"
        journal_part += "."
        parts.append(journal_part)

    if doi:
        doi_clean = doi.strip()
        doi_url = doi_clean if doi_clean.startswith("http") else f"https://doi.org/{doi_clean}"
        parts.append(f" {doi_url}")

    return "".join(parts).strip()


def _to_ieee_bibliography(paper: Dict[str, Any], index: int) -> str:
    """Format single paper as an IEEE bibliography entry."""
    authors = paper.get("authors", [])
    author_str = _format_author_ieee_list(authors)
    title = str(paper.get("title", "")).strip()
    journal = paper.get("journal") or paper.get("container-title", "")
    year = paper.get("year", "2026")
    volume = paper.get("volume")
    pages = paper.get("pages") or paper.get("page")

    body = f'[{index}] {author_str}, "{title},"'
    if journal:
        body += f" {journal}"
    if volume:
        body += f", vol. {volume}"
    if pages:
        norm_pages = re.sub(r"(?<=\d)-(?=\d)", "--", str(pages))
        body += f", pp. {norm_pages}"
    body += f", {year}."

    return body


def export_bibliography(
    citations: List[Dict[str, Any]],
    format_type: str = "bibtex",
) -> str:
    """Export citations as a formatted bibliography string (bibtex, apa, ieee)."""
    if not citations:
        return ""

    fmt = format_type.strip().lower()
    if fmt == "apa":
        entries = [_to_apa_bibliography(c) for c in citations]
        return "\n\n".join(entries) + "\n"
    if fmt == "ieee":
        entries = [_to_ieee_bibliography(c, i + 1) for i, c in enumerate(citations)]
        return "\n".join(entries) + "\n"

    # Default: BibTeX
    entries = [to_bibtex(c) for c in citations]
    return "\n\n".join(entries) + "\n"


def export_bibliography_bytes(
    citations: List[Dict[str, Any]],
    format_type: str = "bibtex",
) -> bytes:
    """Export citations as downloadable UTF-8 bytes."""
    return export_bibliography(citations, format_type).encode("utf-8")


