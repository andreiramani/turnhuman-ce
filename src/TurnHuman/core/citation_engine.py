"""TurnHuman Decoupled Citation Engine & Academic Taxonomy Resolver (v3.0.1-MODULAR)."""

from __future__ import annotations

import collections
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from TurnHuman.core.crossref_client import (
    CROSSREF_API_URL,
    DEFAULT_MAX_QUERIES_PER_MINUTE,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    CrossRefClientMixin,
    CrossRefRateLimiter,
    _load_max_queries_config,
)
from TurnHuman.core.citation_formatter import (
    _extract_author_parts,
    _format_author_apa_list,
    _format_author_bibtex,
    _format_author_ieee_list,
    _format_author_initials,
    _generate_citation_key,
    _get_family_name,
    _to_apa_bibliography,
    _to_ieee_bibliography,
    export_bibliography,
    export_bibliography_bytes,
    format_in_text_citation,
    to_bibtex,
)
from TurnHuman.core.rules import RuleLoader

logger = logging.getLogger("TurnHuman.core.citation_engine")

SUPPORTED_DISCIPLINES = (
    "computer_science",
    "engineering_physics",
    "mathematics_statistics",
    "medical_life_sciences",
    "quantitative_finance",
)

SUPPORTED_STYLES = ("numeric", "apa", "latex", "inline_bracket")

__all__ = [
    "CitationEngine",
    "CrossRefRateLimiter",
    "SUPPORTED_DISCIPLINES",
    "SUPPORTED_STYLES",
    "format_in_text_citation",
    "to_bibtex",
    "export_bibliography",
    "export_bibliography_bytes",
    "get_citation_engine",
    "auto_detect_discipline",
    "get_landmark_papers",
    "insert_citations",
    "resolve_doi",
    "search_crossref",
    "process_citations",
]

class CitationEngine(CrossRefClientMixin):
    """Unified Decoupled Citation Engine & Academic Taxonomy Resolver."""

    def __init__(
        self,
        rule_loader: Optional[RuleLoader] = None,
        max_queries_per_minute: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.rule_loader = rule_loader or RuleLoader.get_instance()
        limit = max_queries_per_minute or _load_max_queries_config()
        self.rate_limiter = CrossRefRateLimiter(max_queries=limit)
        self.timeout = timeout

        # In-memory caches to prevent redundant network calls
        self._query_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._doi_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    # Academic Taxonomy & Auto-Detection

    def get_landmark_papers(
        self,
        discipline: Optional[str] = None,
        subfield: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve landmark papers from the local hierarchical taxonomy."""
        tax = self.rule_loader.get_academic_taxonomy(discipline=discipline)
        papers: List[Dict[str, Any]] = []

        subfield_norm = subfield.strip().lower() if subfield else None

        for disc_name, subfields in tax.items():
            if not isinstance(subfields, list):
                continue
            for sf in subfields:
                if not isinstance(sf, dict):
                    continue
                sf_id = sf.get("subfield_id", "").lower()
                sf_name = sf.get("subfield_name", "").lower()

                if subfield_norm and subfield_norm not in (sf_id, sf_name):
                    continue

                for lp in sf.get("landmark_papers", []):
                    if isinstance(lp, dict):
                        paper_copy = dict(lp)
                        paper_copy["discipline"] = disc_name
                        paper_copy["subfield_id"] = sf.get("subfield_id")
                        paper_copy["subfield_name"] = sf.get("subfield_name")
                        papers.append(paper_copy)

        return papers

    def auto_detect_discipline(self, text: str) -> Tuple[str, str, float]:
        """Automatically detect academic discipline and subfield from text.

        Returns:
            (discipline, subfield, confidence_score) where confidence is in [0.0, 1.0].
            Returns ("general", "general", 0.0) if no discipline matches.
        """
        if not text or not text.strip():
            return "general", "general", 0.0

        tax = self.rule_loader.get_academic_taxonomy()
        text_lower = text.lower()

        scores: Dict[Tuple[str, str], int] = {}

        for disc, subfields in tax.items():
            if not isinstance(subfields, list):
                continue
            for sf in subfields:
                if not isinstance(sf, dict):
                    continue
                sf_id = sf.get("subfield_id", "general")
                keywords = sf.get("keywords", [])
                match_count = 0

                for kw in keywords:
                    kw_lower = kw.lower().strip()
                    if not kw_lower:
                        continue
                    # Multi-word keyword matches as phrase; single-word matches with word boundaries
                    if " " in kw_lower or "-" in kw_lower:
                        if kw_lower in text_lower:
                            match_count += 1
                    else:
                        pattern = r"\b" + re.escape(kw_lower) + r"\b"
                        if re.search(pattern, text_lower):
                            match_count += 1

                # Check topics for extra signal
                topics = sf.get("topics", [])
                for topic in topics:
                    topic_lower = topic.lower()
                    if topic_lower in text_lower:
                        match_count += 2

                if match_count > 0:
                    scores[(disc, sf_id)] = match_count

        if not scores:
            return "general", "general", 0.0

        best_target, max_matches = max(scores.items(), key=lambda item: item[1])
        disc, sf = best_target

        # Calculate confidence metric normalized between 0.0 and 1.0
        # 1 match ~ 0.50, 2 matches ~ 0.70, 3 matches ~ 0.85, 4+ matches ~ 0.95-1.0
        confidence = min(1.0, round(0.40 + 0.15 * max_matches, 2))

        return disc, sf, confidence

    # CrossRef REST API DOI Resolver


    def insert_citations(
        self,
        text: str,
        citations: List[Dict[str, Any]],
        style: str = "latex",
        frequency: str = "medium",
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Insert citations at sentence boundaries to disrupt Winnowing rolling hash chains.

        Supported styles: 'numeric', 'apa', 'latex', 'inline_bracket'.
        Supported frequencies: 'low' (every 3 sentences), 'medium' (every 2), 'high' (every 1).
        """
        if not text or not citations:
            return text, []

        norm_style = style.strip().lower()
        if norm_style not in SUPPORTED_STYLES:
            norm_style = "latex"

        interval_map = {"high": 1, "medium": 2, "low": 3}
        interval = interval_map.get(frequency.strip().lower(), 2)

        # Split text into paragraphs to maintain layout integrity
        paragraphs = text.split("\n\n")
        used_citations: List[Dict[str, Any]] = []
        citation_idx_map: Dict[str, int] = {}  # paper key -> 1-based index for numeric style
        global_sentence_counter = 0

        modified_paragraphs: List[str] = []

        for p in paragraphs:
            if not p.strip():
                modified_paragraphs.append(p)
                continue

            # Split paragraph into sentences preserving terminal punctuation
            # Matches sentence content followed by [.!?] and optional trailing quote
            raw_sentences = re.split(r"(?<=[.!?])\s+", p.strip())
            mod_sentences: List[str] = []

            for s_idx, sent in enumerate(raw_sentences):
                sent_clean = sent.strip()
                if not sent_clean:
                    continue

                global_sentence_counter += 1

                # Determine if this sentence receives a citation
                is_selected = (global_sentence_counter % interval == 0)
                # If only 1 sentence total in paragraph and nothing selected yet, insert at sentence 0
                if len(raw_sentences) == 1 and not used_citations and s_idx == 0:
                    is_selected = True

                if is_selected:
                    # Pick next citation (cycle if fewer citations than insertion points)
                    cit_index = len(used_citations) % len(citations)
                    selected_paper = citations[cit_index]

                    key = selected_paper.get("key") or _generate_citation_key(selected_paper)
                    if key not in citation_idx_map:
                        citation_idx_map[key] = len(citation_idx_map) + 1
                        used_citations.append(selected_paper)

                    marker_num = citation_idx_map[key]
                    marker = format_in_text_citation(selected_paper, marker_num, norm_style)

                    # Insert marker before terminal punctuation
                    m = re.search(r'([.!?]["\']?)$', sent_clean)
                    if m:
                        punc = m.group(1)
                        body = sent_clean[:m.start()].rstrip()
                        sent_with_cit = f"{body} {marker}{punc}"
                    else:
                        sent_with_cit = f"{sent_clean} {marker}"
                    mod_sentences.append(sent_with_cit)
                else:
                    mod_sentences.append(sent_clean)

            modified_paragraphs.append(" ".join(mod_sentences))

        # Reconstruct text
        modified_text = "\n\n".join(modified_paragraphs)
        return modified_text, used_citations

    # Unified Facade Processing

    def process_citations(
        self,
        text: str,
        discipline: Optional[str] = None,
        style: str = "latex",
        query: Optional[str] = None,
        frequency: str = "medium",
    ) -> Dict[str, Any]:
        """Unified citation workflow facade: detection, retrieval, insertion, and bibliography."""
        if not text:
            return {
                "text": "",
                "original_text": "",
                "discipline": discipline or "general",
                "subfield": "general",
                "confidence": 0.0,
                "style": style,
                "citations": [],
                "bibliography": {"bibtex": "", "apa": "", "ieee": ""},
                "total_citations_inserted": 0,
            }

        # Step 1: Discipline auto-detection
        det_disc, det_subfield, confidence = self.auto_detect_discipline(text)
        resolved_disc = discipline or det_disc
        resolved_subfield = det_subfield if discipline is None else "general"

        # Step 2: Retrieve citations
        papers: List[Dict[str, Any]] = []
        if query:
            papers = self.search_crossref(query)

        if not papers:
            # Fallback to local taxonomy landmark papers
            papers = self.get_landmark_papers(
                discipline=resolved_disc if resolved_disc != "general" else None,
                subfield=resolved_subfield if resolved_subfield != "general" else None,
            )

        if not papers:
            # Broad fallback across all disciplines
            papers = self.get_landmark_papers()

        # Step 3: Insert citations
        modified_text, used_citations = self.insert_citations(
            text, papers, style=style, frequency=frequency
        )

        # Step 4: Generate bibliographies
        bibtex_str = export_bibliography(used_citations, "bibtex")
        apa_str = export_bibliography(used_citations, "apa")
        ieee_str = export_bibliography(used_citations, "ieee")

        return {
            "text": modified_text,
            "original_text": text,
            "discipline": resolved_disc,
            "subfield": resolved_subfield,
            "confidence": confidence,
            "style": style,
            "citations": used_citations,
            "bibliography": {
                "bibtex": bibtex_str,
                "apa": apa_str,
                "ieee": ieee_str,
            },
            "total_citations_inserted": len(used_citations),
        }



# Convenience Functional Interfaces
_default_engine: Optional[CitationEngine] = None


def get_citation_engine() -> CitationEngine:
    """Retrieve or initialize singleton CitationEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = CitationEngine()
    return _default_engine


def auto_detect_discipline(text: str) -> Tuple[str, str, float]:
    """Auto-detect discipline and subfield from text."""
    return get_citation_engine().auto_detect_discipline(text)


def get_landmark_papers(
    discipline: Optional[str] = None,
    subfield: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve landmark papers from local taxonomy."""
    return get_citation_engine().get_landmark_papers(discipline, subfield)


def insert_citations(
    text: str,
    citations: List[Dict[str, Any]],
    style: str = "latex",
    frequency: str = "medium",
) -> Tuple[str, List[Dict[str, Any]]]:
    """Insert formatted citations at sentence boundaries."""
    return get_citation_engine().insert_citations(text, citations, style, frequency)


def resolve_doi(doi: str) -> Optional[Dict[str, Any]]:
    """Resolve DOI via CrossRef REST API."""
    return get_citation_engine().resolve_doi(doi)


def search_crossref(query: str, rows: int = 3) -> List[Dict[str, Any]]:
    """Search CrossRef with graceful offline fallback."""
    return get_citation_engine().search_crossref(query, rows)


def process_citations(
    text: str,
    discipline: Optional[str] = None,
    style: str = "latex",
    query: Optional[str] = None,
    frequency: str = "medium",
) -> Dict[str, Any]:
    """Execute unified citation workflow."""
    return get_citation_engine().process_citations(text, discipline, style, query, frequency)
