"""TurnHuman Module 3: Citation & BibTeX Inserter UI (v3.0.0-PROD).

Provides:
- Academic Discipline selection across 5 taxonomies or Auto-Detection.
- CrossRef REST API live DOI search & resolver with etiquette rate limiting.
- Multi-style citation formatting (numeric, apa, latex, inline_bracket).
- Risk-Driven Winnowing hash chain disruption at sentence boundaries.
- Multi-format bibliography exports (BibTeX, APA, IEEE, JSON).
"""

from __future__ import annotations

import html
import json
import logging
from typing import Any, Dict, List, Optional

import streamlit as st

from TurnHuman.core.citation_engine import (
    SUPPORTED_DISCIPLINES,
    SUPPORTED_STYLES,
    export_bibliography,
    get_citation_engine,
    get_landmark_papers,
    process_citations,
    resolve_doi,
    search_crossref,
)
from TurnHuman.ui.common import check_rate_limit
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.citation_ui")


def render_citation_page() -> None:
    """Render the Citation & BibTeX Inserter workstation."""
    st.markdown(f"## {t('citation.title', '📚 Module 3: Citation & BibTeX Inserter')}")
    st.caption(
        t(
            "citation.subtitle",
            "Academic discipline taxonomy matching, CrossRef live DOI search, and risk-driven sentence boundary shielding.",
        )
    )

    engine = get_citation_engine()

    # -------------------------------------------------------------------------
    # 1. Top Configuration Controls
    # -------------------------------------------------------------------------
    c_disc, c_style, c_freq = st.columns([1.5, 1.2, 1.3])

    with c_disc:
        disc_options = ["auto"] + list(SUPPORTED_DISCIPLINES)
        disc_labels = {
            "auto": "✨ Auto-Detect from Manuscript",
            "computer_science": "Computer Science",
            "engineering_physics": "Engineering & Physics",
            "mathematics_statistics": "Mathematics & Statistics",
            "medical_life_sciences": "Medical & Life Sciences",
            "quantitative_finance": "Quantitative Finance",
        }
        selected_disc = st.selectbox(
            "Academic Discipline Taxonomy",
            options=disc_options,
            format_func=lambda d: disc_labels.get(d, d),
            help="Select academic domain or let TurnHuman classify discipline via taxonomy keywords.",
        )

    with c_style:
        style_choice = st.selectbox(
            "In-Text Citation Style",
            options=list(SUPPORTED_STYLES),
            format_func=lambda s: {
                "latex": "LaTeX \\cite{key}",
                "apa": "APA (Author, Year)",
                "numeric": "IEEE Numeric [1]",
                "inline_bracket": "Bracket [Author, Year]",
            }[s],
            index=0,
            help="Formatting style for citation anchors inserted into sentence boundaries.",
        )

    with c_freq:
        freq_choice = st.selectbox(
            "Shielding Frequency",
            options=["medium", "high", "low"],
            format_func=lambda f: {
                "high": "High (Every 1 Sentence)",
                "medium": "Medium (Every 2 Sentences)",
                "low": "Low (Every 3 Sentences)",
            }[f],
            index=0,
            help="Interval at which citation tokens are injected to disrupt Karp-Rabin winnowing chains.",
        )

    # -------------------------------------------------------------------------
    # 2. CrossRef REST API Live DOI Search & Resolver
    # -------------------------------------------------------------------------
    with st.expander("🔍 CrossRef REST API Live DOI Search & Landmark Papers", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.825rem; color: var(--th-text-secondary, #334155); margin-bottom: 8px;">
                Query the live CrossRef REST API (User-Agent: <code>TurnHuman/3.0</code>, rate limited to 50 rpm) 
                or search by DOI to fetch validated bibliographic metadata and BibTeX records.
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_search, c_btn = st.columns([3.5, 1.5])
        with c_search:
            search_query = st.text_input(
                t("citation.crossref_input_label", "Search CrossRef Query or DOI"),
                placeholder=t("citation.crossref_input_placeholder", "e.g., 10.1145/3318464.3389700 or Attention Is All You Need"),
                key="crossref_search_input",
            )
        with c_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            search_clicked = st.button(t("citation.btn_search_crossref", "🔍 Search CrossRef"), key="crossref_search_btn", use_container_width=True)

        if search_clicked and search_query.strip():
            if not check_rate_limit():
                st.stop()

            q_clean = search_query.strip()
            with st.spinner("Connecting to CrossRef REST API..."):
                if q_clean.startswith("10.") or "doi.org" in q_clean:
                    resolved_paper = resolve_doi(q_clean)
                    papers_found = [resolved_paper] if resolved_paper else []
                else:
                    papers_found = search_crossref(q_clean, rows=3)

            if papers_found:
                st.session_state["_crossref_results"] = papers_found
                st.success(f"Found {len(papers_found)} work(s) via CrossRef.")
            else:
                st.warning("No records found on CrossRef. Showing local landmark papers.")
                st.session_state["_crossref_results"] = get_landmark_papers()

        if "_crossref_results" in st.session_state:
            for p in st.session_state["_crossref_results"]:
                authors_str = html.escape(", ".join(p.get("authors", [])))
                safe_title = html.escape(str(p.get("title", "")))
                safe_year = html.escape(str(p.get("year", "")))
                safe_journal = html.escape(str(p.get("journal", "N/A")))
                safe_doi = html.escape(str(p.get("doi", "N/A")))
                safe_key = html.escape(str(p.get("key", "")))
                st.markdown(
                    f"""
                    <div style="padding: 10px 14px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 8px; margin-bottom: 8px;">
                        <b style="color: var(--th-cobalt, #2563EB);">{safe_title}</b><br>
                        <span style="font-size: 0.8rem; color: var(--th-text-secondary, #334155);">
                            Authors: {authors_str} • Year: {safe_year} • Journal: {safe_journal}
                        </span><br>
                        <span style="font-size: 0.75rem; font-family: monospace; color: var(--th-text-muted, #64748B);">
                            DOI: {safe_doi} | Key: {safe_key}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # 3. Manuscript Narrative Input
    # -------------------------------------------------------------------------
    sample_text = (
        "Deep neural networks have shown significant empirical success in natural language processing. "
        "The transformer architecture relies on self-attention mechanisms to compute representations. "
        "Stochastic gradient descent remains the foundational optimization framework for large language models. "
        "Recent advances substantiate theoretical guarantees regarding generalization bounds in overparameterized regimes."
    )

    manuscript_text = st.text_area(
        t("citation.manuscript_label", "Manuscript Text for Citation Shielding"),
        value=sample_text,
        height=180,
        placeholder=t("citation.manuscript_placeholder", "Paste academic manuscript text here..."),
        help=t("citation.manuscript_help", "Citations will be inserted at sentence boundaries according to chosen frequency and style."),
    )

    process_btn = st.button(t("citation.btn_process", "🚀 Insert Citations"), type="primary")

    if process_btn:
        if not manuscript_text.strip():
            st.warning(t("citation.warn_empty", "Please provide manuscript text."))
        elif not check_rate_limit():
            st.stop()
        else:
            disc_arg = None if selected_disc == "auto" else selected_disc

            with st.spinner(t("citation.spinner_process", "Inserting contextual landmark citations from academic taxonomy...")):
                result = process_citations(
                    text=manuscript_text,
                    discipline=disc_arg,
                    style=style_choice,
                    frequency=freq_choice,
                )

            st.session_state["_last_citation_result"] = result

    # -------------------------------------------------------------------------
    # 4. Results & Multi-Format Bibliography Tabs
    # -------------------------------------------------------------------------
    if "_last_citation_result" in st.session_state:
        res = st.session_state["_last_citation_result"]

        st.markdown("---")
        det_disc = html.escape(str(res.get("discipline", "general")).replace("_", " ").title())
        det_sub = html.escape(str(res.get("subfield", "general")).replace("_", " ").title())
        conf = res.get("confidence", 0.0) * 100.0
        inserted_count = html.escape(str(res.get("total_citations_inserted", 0)))

        st.markdown(
            f"""
            <div style="display: flex; gap: 12px; margin-bottom: 14px; align-items: center; flex-wrap: wrap;">
                <span class="ze-badge ze-badge-neutral">Discipline: <b>{det_disc}</b></span>
                <span class="ze-badge ze-badge-neutral">Subfield: <b>{det_sub}</b></span>
                <span class="ze-badge ze-badge-neutral">Classification Confidence: <b>{conf:.0f}%</b></span>
                <span class="ze-badge ze-badge-drift">Inserted: <b>{inserted_count} Citation(s)</b></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("##### 📝 Manuscript with Shielded Citations")
        cited_text = res.get("text", "")
        st.text_area("Cited Manuscript Output", value=cited_text, height=180, key="cited_output_area")

        st.download_button(
            label=t("citation.btn_download_cited", "📥 Download Cited Manuscript (.txt)"),
            data=cited_text.encode("utf-8"),
            file_name="manuscript_with_citations.txt",
            mime="text/plain",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📚 Formatted Bibliographies & Export Formats")

        tab_bib, tab_apa, tab_ieee, tab_json = st.tabs(
            [
                t("citation.tab_bib", "BibTeX (.bib)"),
                t("citation.tab_apa", "APA 7th Edition"),
                t("citation.tab_ieee", "IEEE Format"),
                t("citation.tab_json", "JSON Citations Meta"),
            ]
        )

        bibs = res.get("bibliography", {})
        bibtex_content = bibs.get("bibtex", "")
        apa_content = bibs.get("apa", "")
        ieee_content = bibs.get("ieee", "")
        json_content = json.dumps(res.get("citations", []), indent=2)

        with tab_bib:
            st.code(bibtex_content, language="bibtex")
            st.download_button(
                label=t("citation.btn_download_bib", "📥 Download references.bib"),
                data=bibtex_content.encode("utf-8"),
                file_name="references.bib",
                mime="text/plain",
            )

        with tab_apa:
            st.text_area("APA Formatted References", value=apa_content, height=200, key="apa_area")
            st.download_button(
                label=t("citation.btn_download_apa", "📥 Download references_apa.txt"),
                data=apa_content.encode("utf-8"),
                file_name="references_apa.txt",
                mime="text/plain",
            )

        with tab_ieee:
            st.text_area("IEEE Formatted References", value=ieee_content, height=200, key="ieee_area")
            st.download_button(
                label=t("citation.btn_download_ieee", "📥 Download references_ieee.txt"),
                data=ieee_content.encode("utf-8"),
                file_name="references_ieee.txt",
                mime="text/plain",
            )

        with tab_json:
            st.code(json_content, language="json")
            st.download_button(
                label=t("citation.btn_download_json", "📥 Download citations.json"),
                data=json_content.encode("utf-8"),
                file_name="citations.json",
                mime="application/json",
            )
