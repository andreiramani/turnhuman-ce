"""TurnHuman Module 5: Document Similarity Comparator UI (v3.0.0-PROD).

Provides:
- Dual document input (Document A vs Document B) via text or file upload (.txt, .docx, .tex, .md).
- 4 complementary similarity metrics:
  1. 5-Gram Contiguous Match Overlap
  2. Winnowing Karp-Rabin Rolling Hash Fingerprints (8-word guarantee)
  3. Cosine TF-IDF Term Overlap
  4. Longest Common Subsequence (LCS)
- Weighted composite similarity score with risk grading (Low, Moderate, High).
- Synchronized matching passage inspection table.
"""

from __future__ import annotations

import html
import io
import logging
from typing import Any, Dict, List, Tuple

import docx
import streamlit as st

from TurnHuman.core.security import validate_upload
from TurnHuman.core.similarity import compare_documents
from TurnHuman.ui.common import check_rate_limit
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.similarity_ui")


def _extract_text_from_upload(uploaded_file: Any) -> str:
    """Extract plain text from uploaded file buffer (.docx, .tex, .md, .txt) with security validation."""
    if uploaded_file is None:
        return ""

    fname = uploaded_file.name
    raw_bytes = uploaded_file.read()

    # Security validation
    valid_ok, valid_err = validate_upload(fname, raw_bytes)
    if not valid_ok:
        st.error(f"Security validation failed for '{fname}': {valid_err}")
        return ""

    try:
        if fname.lower().endswith(".docx"):
            doc = docx.Document(io.BytesIO(raw_bytes))
            full_text = []
            for p in doc.paragraphs:
                if p.text.strip():
                    full_text.append(p.text)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            full_text.append(cell.text)
            return "\n\n".join(full_text)
        else:
            return raw_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.error("Failed to extract text from %s: %s", fname, exc)
        return ""


def render_similarity_page() -> None:
    """Render the Document Similarity Comparator workstation."""
    st.markdown(f"## {t('similarity.title', '🔬 Module 5: Document Similarity Comparator')}")
    st.caption(
        t(
            "similarity.subtitle",
            "Pairwise multi-metric algorithmic audit measuring 5-gram overlap, Karp-Rabin winnowing fingerprints, TF-IDF cosine, and LCS.",
        )
    )

    # 1. Dual Document Input (Document A vs Document B)
    col_a, col_b = st.columns(2)

    sample_doc_a = (
        "It is critical to utilize high-performance algorithms to optimize accuracy in deep neural networks. "
        "Furthermore, stochastic gradient descent exhibits robust empirical convergence properties on benchmark datasets. "
        "In addition, researchers must ensure that validation loss does not diverge during iterative backpropagation."
    )

    sample_doc_b = (
        "It is vital to employ high-performance algorithms to enhance accuracy in deep neural networks. "
        "Moreover, stochastic gradient descent shows sound empirical convergence behavior on standard benchmark datasets. "
        "Also, investigators should verify that validation loss remains stable during iterative optimization passes."
    )

    with col_a:
        st.markdown(f"##### {t('similarity.doc_a_header', '📄 Document A (Original / Source)')}")
        tab_a_text, tab_a_file = st.tabs(["✍️ Paste Text", "📁 Upload File"])
        with tab_a_text:
            text_a_input = st.text_area(
                "Document A Content",
                value=sample_doc_a,
                height=220,
                key="doc_a_textarea",
            )
        with tab_a_file:
            file_a = st.file_uploader(
                "Upload Document A (.txt, .docx, .tex, .md)",
                type=["txt", "docx", "tex", "md"],
                key="doc_a_uploader",
            )
            if file_a is not None:
                extracted_a = _extract_text_from_upload(file_a)
                if extracted_a:
                    text_a_input = extracted_a
                    st.success(f"Loaded {file_a.name} ({len(extracted_a.split())} words).")

    with col_b:
        st.markdown(f"##### {t('similarity.doc_b_header', '📄 Document B (Transformed / Comparison)')}")
        tab_b_text, tab_b_file = st.tabs(["✍️ Paste Text", "📁 Upload File"])
        with tab_b_text:
            text_b_input = st.text_area(
                "Document B Content",
                value=sample_doc_b,
                height=220,
                key="doc_b_textarea",
            )
        with tab_b_file:
            file_b = st.file_uploader(
                "Upload Document B (.txt, .docx, .tex, .md)",
                type=["txt", "docx", "tex", "md"],
                key="doc_b_uploader",
            )
            if file_b is not None:
                extracted_b = _extract_text_from_upload(file_b)
                if extracted_b:
                    text_b_input = extracted_b
                    st.success(f"Loaded {file_b.name} ({len(extracted_b.split())} words).")

    run_btn = st.button(t("similarity.btn_run", "🔬 Run Pairwise Similarity Analysis"), type="primary")

    if run_btn:
        if not text_a_input.strip() or not text_b_input.strip():
            st.warning(t("similarity.warn_empty", "Please provide text for both Document A and Document B."))
        elif not check_rate_limit():
            st.stop()
        else:
            with st.spinner(t("similarity.spinner", "Computing 4-metric similarity suite and Karp-Rabin winnowing hashes...")):
                sim_result = compare_documents(text_a_input, text_b_input)
            st.session_state["_last_sim_result"] = sim_result

    # 2. Results & Metrics Presentation
    if "_last_sim_result" in st.session_state:
        res = st.session_state["_last_sim_result"]
        comb_score = res.get("combined_score", 0.0)
        risk_cat = res.get("risk_category", "LOW")
        metrics = res.get("metrics", {})
        win_info = res.get("winnowing_details", {})
        matching_passages = res.get("matching_passages", [])

        st.markdown("---")

        if risk_cat == "HIGH":
            badge_class = "ze-badge-expand"
            risk_color = "#EF4444"
            risk_desc = "HIGH SIMILARITY: Strong Structural & Phrasal Overlap (High Turnitin Match)"
        elif risk_cat == "MODERATE":
            badge_class = "ze-badge-drift"
            risk_color = "#F59E0B"
            risk_desc = "MODERATE SIMILARITY: Shared Lexical Context / Paraphrase Overlap"
        else:
            badge_class = "ze-badge-neutral"
            risk_color = "#10B981"
            risk_desc = "LOW SIMILARITY: Successfully Disrupted K-Grams & Winnowing Fingerprints"

        safe_risk_desc = html.escape(str(risk_desc))
        safe_risk_cat = html.escape(str(risk_cat))

        st.markdown(
            f"""
            <div style="padding: 16px 20px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 2.2rem; font-weight: 800; font-family: var(--th-font-mono, monospace); color: {risk_color};">
                        {comb_score:.1f}%
                    </span>
                    <span style="font-size: 0.95rem; font-weight: 600; color: var(--th-text-secondary, #334155); margin-left: 12px;">
                        {safe_risk_desc}
                    </span>
                </div>
                <span class="ze-badge {badge_class}" style="font-size: 0.9rem; padding: 4px 14px;">
                    {safe_risk_cat} RISK
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Metric Cards
        m1, m2, m3, m4 = st.columns(4)

        ngram_pct = metrics.get("ngram_5_ratio", 0.0) * 100.0
        with m1:
            st.metric("5-Gram Contiguous", f"{ngram_pct:.1f}%")
            if ngram_pct == 0.0:
                st.caption("🟢 0 Contiguous 5-grams")
            else:
                st.caption(f"⚠️ {len(res.get('matching_ngrams', []))} chain(s) match")

        win_pct = metrics.get("winnowing_jaccard", 0.0) * 100.0
        with m2:
            st.metric("Winnowing Jaccard", f"{win_pct:.1f}%")
            shared_fp = win_info.get("shared_fingerprints_count", 0)
            st.caption(f"🛡️ {shared_fp} shared hash(es) (k={win_info.get('k', 5)}, w={win_info.get('w', 4)})")

        tfidf_pct = metrics.get("cosine_tfidf", 0.0) * 100.0
        with m3:
            st.metric("Cosine TF-IDF", f"{tfidf_pct:.1f}%")
            st.caption("Vocabulary distribution overlap")

        lcs_pct = metrics.get("lcs_ratio", 0.0) * 100.0
        with m4:
            st.metric("Longest Common Subseq", f"{lcs_pct:.1f}%")
            st.caption(f"LCS length: {metrics.get('lcs_length', 0)} tokens")

        # Synchronized Matching Passages Box
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 🔗 Synchronized Matching Passages (Chains >= 3 Tokens)")

        if not matching_passages:
            st.success("✅ **0 contiguous chains detected.** Karp-Rabin winnowing fingerprint chains have been disrupted successfully across all sentences.")
        else:
            table_rows = []
            for p in matching_passages:
                table_rows.append({
                    "Length (Words)": p.get("length_words", 0),
                    "Matching Passage": p.get("passage", ""),
                    "Doc A Position": f"Words {p.get('start_idx_a', 0)}–{p.get('end_idx_a', 0)}",
                    "Doc B Position": f"Words {p.get('start_idx_b', 0)}–{p.get('end_idx_b', 0)}",
                })
            st.table(table_rows)
