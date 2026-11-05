"""TurnHuman Module 1: Plagiarism & AI Humanizer UI (v3.0.0-PROD).

Provides:
- Dual-tab interface: Interactive Text Area & Batch Documents Dropzone (.docx, .tex, .md, .txt, .zip).
- Strict Zero-Expansion (0 Net Words Added) vs Full Deterministic pipeline.
- High-contrast interactive side-by-side diff viewer.
- Full Word Budget Controller telemetry card and export options.
- Adheres to Section 7 Code Standards (<= 450 LOC).
"""

from __future__ import annotations

import html
import io
import logging
from typing import Any, Dict, List
import zipfile

import streamlit as st

from TurnHuman.core.doc_processor import create_in_memory_zip, process_docx, process_latex
from TurnHuman.core.modifier import TextModifier
from TurnHuman.core.security import is_safe_zip_entry_name, validate_upload
from TurnHuman.ui.common import build_diff_html, check_rate_limit
from TurnHuman.ui.humanizer_controls import HumanizerConfig, render_humanizer_controls
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.humanizer_ui")


def _render_single_text_tab(cfg: HumanizerConfig) -> None:
    """Render interactive single-text transformation tab with diff and telemetry."""
    sample_placeholder = (
        "Paste your draft abstract, conference manuscript prose, or thesis section here...\n\n"
        "Example: It is critical to utilize high-performance algorithms to optimize accuracy. "
        "Furthermore, it is noteworthy that deep neural networks exhibit robust convergence metrics."
    )
    input_text = st.text_area(
        t("humanizer.input_label", "Draft Manuscript Text"),
        height=200,
        placeholder=sample_placeholder,
    )

    execute_btn = st.button(t("humanizer.btn_execute", "🚀 Execute Humanization"), type="primary")

    if not execute_btn:
        return

    if not input_text.strip():
        st.warning(t("humanizer.warn_empty_input", "Please provide input text to transform."))
        return

    if not check_rate_limit():
        st.stop()

    seed = None if cfg.use_random_seed else 42

    with st.spinner(t("humanizer.spinner_transform", "Executing deterministic transformation pipeline...")):
        modifier = TextModifier(
            mode=cfg.mode,
            synonym_probability=cfg.synonym_probability,
            domain=cfg.domain,
            seed=seed,
            custom_protected_terms=list(cfg.protected_terms),
        )
        output_text = modifier.transform(input_text)
        telemetry = modifier.get_telemetry()

    initial_wc = telemetry.get("word_count_initial", len(input_text.split()))
    final_wc = telemetry.get("word_count_final", len(output_text.split()))
    net_delta = telemetry.get("total_delta", final_wc - initial_wc)
    time_ms = telemetry.get("total_time_ms", 0.0)
    spacy_stat = html.escape("Active" if telemetry.get("spacy_available", False) else "Regex Fallback")
    safe_mode = html.escape(str(cfg.mode).upper())

    is_ze_passed = net_delta == 0 if cfg.is_ze else True
    ze_badge_html = (
        '<span class="telemetry-badge-safe">🟢 100% ZE Validated (0 Words)</span>'
        if (cfg.is_ze and is_ze_passed)
        else f'<span style="font-weight:700;">{net_delta:+d} Words</span>'
    )

    st.markdown(
        f"""
        <div class="telemetry-card" style="padding: 14px 18px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 10px; margin: 16px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom: 12px; font-weight:700; font-size:0.875rem;">
                <span>📊 Word Budget Controller Execution Telemetry</span>
                <span>Pipeline Mode: <b style="color:var(--th-cobalt, #2563EB);">{safe_mode}</b></span>
            </div>
            <div class="telemetry-grid" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px;">
                <div class="telemetry-item">
                    <span class="telemetry-label">Initial Words</span>
                    <span class="telemetry-value">{initial_wc}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-label">Final Words</span>
                    <span class="telemetry-value">{final_wc}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-label">Net Word Delta</span>
                    <span class="telemetry-value">{ze_badge_html}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-label">Pipeline Latency</span>
                    <span class="telemetry-value">{time_ms} ms</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-label">NLP Parser Engine</span>
                    <span class="telemetry-value" style="font-size:0.95rem;">{spacy_stat}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    orig_html, mod_html = build_diff_html(input_text, output_text, protected_terms=cfg.protected_terms)

    st.markdown("##### 🔍 Interactive Side-by-Side Diff Viewer")
    st.caption(
        "🔴 Strikethrough = Original text removed | "
        "🟢 Highlight = Humanized substitution | "
        "🔵 Pill 🔒 = Protected term intact"
    )

    diff_col1, diff_col2 = st.columns(2)
    with diff_col1:
        st.markdown(
            f"""
            <div class="diff-column" style="border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 8px; overflow: hidden; background: var(--th-bg-surface, #FFF);">
                <div class="diff-header" style="background: var(--th-bg-subtle, #F1F5F9); padding: 8px 12px; font-weight: 600; font-size: 0.85rem; border-bottom: 1px solid var(--th-border-subtle, #E2E8F0); display: flex; justify-content: space-between;">
                    <span>Original Manuscript</span>
                    <span>{initial_wc} Words</span>
                </div>
                <div class="diff-scroll-box" style="padding: 14px; max-height: 380px; overflow-y: auto; font-family: var(--th-font-sans); font-size: 0.885rem; line-height: 1.6;">
                    {orig_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with diff_col2:
        st.markdown(
            f"""
            <div class="diff-column" style="border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 8px; overflow: hidden; background: var(--th-bg-surface, #FFF);">
                <div class="diff-header" style="background: var(--th-bg-subtle, #F1F5F9); padding: 8px 12px; font-weight: 600; font-size: 0.85rem; border-bottom: 1px solid var(--th-border-subtle, #E2E8F0); display: flex; justify-content: space-between;">
                    <span>Humanized Manuscript</span>
                    <span>{final_wc} Words</span>
                </div>
                <div class="diff-scroll-box" style="padding: 14px; max-height: 380px; overflow-y: auto; font-family: var(--th-font-sans); font-size: 0.885rem; line-height: 1.6;">
                    {mod_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label=t("humanizer.btn_download_txt", "📥 Download Humanized Text (.txt)"),
        data=output_text.encode("utf-8"),
        file_name="humanized_manuscript.txt",
        mime="text/plain",
    )


def _render_batch_documents_tab(cfg: HumanizerConfig) -> None:
    """Render batch documents upload and processing tab."""
    st.markdown(
        """
        <div style="font-size: 0.875rem; color: var(--th-text-secondary, #334155); margin-bottom: 12px;">
            Upload one or multiple academic documents. Formatting, typography, LaTeX math formulas, 
            and XML runs are preserved 100%. Processed entirely in RAM (0 bytes written to disk).
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=["docx", "tex", "txt", "md", "zip"],
        accept_multiple_files=True,
        help="Supported: Word (.docx), LaTeX (.tex), Markdown (.md), Plain Text (.txt), Archive (.zip)",
    )

    if not uploaded_files:
        return

    st.info(f"📁 {len(uploaded_files)} file(s) loaded into RAM.")
    if not st.button(t("humanizer.btn_batch_transform", "🚀 Transform Batch Documents"), type="primary"):
        return

    if not check_rate_limit():
        st.stop()

    processed_files_dict: Dict[str, Any] = {}
    summary_records: List[Dict[str, Any]] = []

    with st.spinner(t("humanizer.batch_spinner", "Processing batch documents in-memory...")):
        modifier = TextModifier(
            mode=cfg.mode,
            synonym_probability=cfg.synonym_probability,
            domain=cfg.domain,
            seed=None if cfg.use_random_seed else 42,
            custom_protected_terms=list(cfg.protected_terms),
        )

        for uf in uploaded_files:
            fname = uf.name
            raw_bytes = uf.read()
            ext = fname.split(".")[-1].lower() if "." in fname else ""

            # Security upload validation guard
            val_ok, val_err = validate_upload(fname, raw_bytes)
            if not val_ok:
                summary_records.append({
                    "File Name": fname,
                    "Format": ext.upper() if ext else "UNKNOWN",
                    "Status": f"❌ Rejected by Security Guard: {val_err}",
                })
                continue

            try:
                if ext == "docx":
                    out_stream = process_docx(
                        io.BytesIO(raw_bytes),
                        transform_fn=modifier.transform,
                    )
                    processed_files_dict[f"humanized_{fname}"] = out_stream
                    summary_records.append({
                        "File Name": fname,
                        "Format": "Word (.docx)",
                        "Status": "✅ Transformed (OpenXML Safe)",
                    })

                elif ext == "tex":
                    raw_str = raw_bytes.decode("utf-8", errors="replace")
                    out_tex = process_latex(
                        raw_str,
                        transform_fn=modifier.transform,
                    )
                    processed_files_dict[f"humanized_{fname}"] = out_tex
                    summary_records.append({
                        "File Name": fname,
                        "Format": "LaTeX (.tex)",
                        "Status": "✅ Transformed (Math Protected)",
                    })

                elif ext in ("txt", "md"):
                    raw_str = raw_bytes.decode("utf-8", errors="replace")
                    out_txt = modifier.transform(raw_str)
                    processed_files_dict[f"humanized_{fname}"] = out_txt
                    summary_records.append({
                        "File Name": fname,
                        "Format": f"{ext.upper()}",
                        "Status": "✅ Transformed",
                    })

                elif ext == "zip":
                    in_zip = zipfile.ZipFile(io.BytesIO(raw_bytes))
                    for zip_subfile in in_zip.namelist():
                        if zip_subfile.startswith("__MACOSX") or zip_subfile.endswith("/"):
                            continue
                        # Zip Slip mitigation
                        if not is_safe_zip_entry_name(zip_subfile):
                            logger.warning("Zip Slip attempt blocked in archive: %s", zip_subfile)
                            continue
                        sub_bytes = in_zip.read(zip_subfile)
                        sub_ext = zip_subfile.split(".")[-1].lower() if "." in zip_subfile else ""

                        if sub_ext == "docx":
                            sub_out = process_docx(
                                io.BytesIO(sub_bytes),
                                transform_fn=modifier.transform,
                            )
                            processed_files_dict[f"humanized_{zip_subfile}"] = sub_out
                        elif sub_ext == "tex":
                            sub_str = sub_bytes.decode("utf-8", errors="replace")
                            sub_out_tex = process_latex(
                                sub_str,
                                transform_fn=modifier.transform,
                            )
                            processed_files_dict[f"humanized_{zip_subfile}"] = sub_out_tex
                        elif sub_ext in ("txt", "md"):
                            sub_str = sub_bytes.decode("utf-8", errors="replace")
                            sub_out_txt = modifier.transform(sub_str)
                            processed_files_dict[f"humanized_{zip_subfile}"] = sub_out_txt

                    summary_records.append({
                        "File Name": fname,
                        "Format": "Archive (.zip)",
                        "Status": "✅ Extracted & Transformed",
                    })

            except Exception as exc:
                logger.error("Error processing %s: %s", fname, exc)
                summary_records.append({
                    "File Name": fname,
                    "Format": ext.upper(),
                    "Status": f"⚠️ Error: {exc}",
                })

    st.markdown("##### 📋 Batch Processing Summary")
    st.table(summary_records)

    if processed_files_dict:
        zip_name, zip_stream = create_in_memory_zip(
            processed_files_dict,
            zip_name_prefix="TurnHuman_Humanized_Batch",
        )

        st.download_button(
            label=t(
                "humanizer.btn_download_batch_zip",
                f"📦 Download All Processed Documents ({zip_name})",
                zip_name=zip_name,
            ),
            data=zip_stream.getvalue(),
            file_name=zip_name,
            mime="application/zip",
            type="primary",
        )


def render_humanizer_page() -> None:
    """Render the primary Plagiarism & AI Humanizer workstation."""
    st.markdown(f"## {t('humanizer.title', '🛡️ Module 1: Plagiarism & AI Humanizer')}")
    st.caption(
        t("humanizer.subtitle", "Deterministic 16-stage syntactic transformation with mathematical word budget guarantees.")
    )

    cfg = render_humanizer_controls()

    tab_text, tab_batch = st.tabs(
        [
            t("humanizer.tab_single", "✍️ Interactive Text Input"),
            t("humanizer.tab_batch", "📁 Batch Documents Upload (.docx, .tex, .md, .txt, .zip)"),
        ]
    )

    with tab_text:
        _render_single_text_tab(cfg)

    with tab_batch:
        _render_batch_documents_tab(cfg)
