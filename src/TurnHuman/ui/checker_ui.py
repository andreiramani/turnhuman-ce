"""TurnHuman Module 4: ZipPy Entropy & AI Signature Checker UI (v3.0.0-PROD).

Provides:
- Domain calibration offsets for 5 academic fields + general.
- Dual zlib (level 9) and lzma (preset 9) sliding compression metrics.
- Trilateral entropy distribution gauge (Human-Written %, AI-Refined %, AI-Generated %).
- Interactive sentence-level risk span reader.
"""

from __future__ import annotations

import html
import logging
from typing import Any, Dict, List

import streamlit as st

from TurnHuman.core.entropy_checker import DOMAIN_CALIBRATION, evaluate_entropy
from TurnHuman.ui.common import check_rate_limit
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.checker_ui")


def render_checker_page() -> None:
    """Render the ZipPy Entropic Perplexity & AI Signature Checker workstation."""
    st.markdown(f"## {t('checker.title', '📊 Module 4: ZipPy Entropy & AI Signature Checker')}")
    st.caption(
        t(
            "checker.subtitle",
            "Compression-Based Trilateral Entropy Evaluator • Domain-Aware Calibrated Thresholds",
        )
    )

    # 1. Top Domain Calibration Selector
    domain_labels = {
        "general": "General / Non-Technical Prose",
        "computer_science": "Computer Science (Formulaic Factor: 0.88)",
        "mathematics_statistics": "Mathematics & Statistics (Formulaic Factor: 0.84)",
        "engineering_physics": "Engineering & Physics (Formulaic Factor: 0.90)",
        "medical_life_sciences": "Medical & Life Sciences (Formulaic Factor: 0.94)",
        "quantitative_finance": "Quantitative Finance (Formulaic Factor: 0.92)",
    }

    c_dom, c_info = st.columns([2, 2])
    with c_dom:
        selected_domain = st.selectbox(
            t("checker.select_domain", "Domain Calibration Offset"),
            options=list(DOMAIN_CALIBRATION.keys()),
            format_func=lambda d: domain_labels.get(d, d),
            help=t("checker.domain_help", "Calibrates compression thresholds to avoid false positives on standard technical vocabulary."),
        )

    with c_info:
        st.markdown(
            """
            <div style="font-size: 0.8rem; color: var(--th-text-muted, #64748B); padding-top: 24px;">
                Calibrated against Turnitin & QuillBot detector baselines. Uses Kolmogorov-algorithmic complexity proxies.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Text Area Input
    sample_text = (
        "It is important to remember that deep learning algorithms play a crucial role in modern technology. "
        "In this investigation, we examine the convergence dynamics of stochastic gradient descent. "
        "The empirical results substantiate our theoretical bound across high-dimensional manifolds. "
        "Furthermore, it is noteworthy that computational efficiency is vital for deep neural network architectures."
    )

    input_text = st.text_area(
        t("checker.input_label", "Passage to Analyze"),
        value=sample_text,
        height=180,
        placeholder=t("checker.input_placeholder", "Paste text passage here to evaluate entropic predictability..."),
        help=t("checker.input_help", "Paste a manuscript section, abstract, or paragraph to evaluate AI risk."),
    )

    eval_btn = st.button(t("checker.btn_eval", "📊 Evaluate Entropic Risk"), type="primary")

    if eval_btn:
        if not input_text.strip():
            st.warning(t("checker.warn_empty", "Please provide text to analyze."))
        elif not check_rate_limit():
            st.stop()
        else:
            with st.spinner(t("checker.spinner", "Calculating dual zlib/lzma sliding compression perplexity...")):
                result = evaluate_entropy(input_text, domain=selected_domain)
            st.session_state["_last_checker_result"] = result

    # 3. Telemetry & Visual Gauge Output
    if "_last_checker_result" in st.session_state:
        res = st.session_state["_last_checker_result"]
        score = res.get("composite_score", 0.0)
        risk = res.get("risk_level", "LOW")
        tri = res.get("trilateral_split", {})
        metrics = res.get("compression_metrics", {})
        spans = res.get("spans", [])

        st.markdown("---")

        # Color token mappings
        if score >= 60.0:
            badge_class = "ze-badge-expand"
            risk_color = "#EF4444"
            risk_desc = "HIGH RISK: Strong AI Predictability Signature"
        elif score >= 35.0:
            badge_class = "ze-badge-drift"
            risk_color = "#F59E0B"
            risk_desc = "MODERATE RISK: Hybrid / AI-Refined Signal"
        else:
            badge_class = "ze-badge-neutral"
            risk_color = "#10B981"
            risk_desc = "LOW RISK: Natural Human Entropy"

        # Overall Score & Trilateral Gauge Card
        hw_pct = tri.get("human_written_pct", 100.0)
        ar_pct = tri.get("ai_refined_pct", 0.0)
        ag_pct = tri.get("ai_generated_pct", 0.0)
        safe_risk_desc = html.escape(str(risk_desc))
        safe_risk = html.escape(str(risk))

        st.markdown(
            f"""
            <div class="gauge-card" style="padding: 16px 20px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 12px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="font-size: 2rem; font-weight: 800; font-family: var(--th-font-mono, monospace); color: {risk_color};">
                            {score:.1f}%
                        </span>
                        <span style="font-size: 0.9rem; font-weight: 600; color: var(--th-text-secondary, #334155); margin-left: 10px;">
                            {safe_risk_desc}
                        </span>
                    </div>
                    <span class="ze-badge {badge_class}" style="font-size: 0.85rem; padding: 4px 12px;">
                        {safe_risk} PREDICTABILITY
                    </span>
                </div>
                
                <div style="font-size: 0.78rem; font-weight: 600; color: var(--th-text-muted, #64748B); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;">
                    Trilateral Entropy Distribution
                </div>
                <div style="display: flex; height: 16px; border-radius: 8px; overflow: hidden; background: #E2E8F0; margin-bottom: 10px;">
                    <div style="width: {hw_pct}%; background: #10B981; transition: width 0.3s ease;" title="Human-Written: {hw_pct}%"></div>
                    <div style="width: {ar_pct}%; background: #F59E0B; transition: width 0.3s ease;" title="AI-Refined: {ar_pct}%"></div>
                    <div style="width: {ag_pct}%; background: #EF4444; transition: width 0.3s ease;" title="AI-Generated: {ag_pct}%"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.825rem; flex-wrap: wrap; gap: 8px;">
                    <span style="color: #065F46; font-weight: 600;">🟢 Human-Written: <b>{hw_pct:.1f}%</b></span>
                    <span style="color: #92400E; font-weight: 600;">🟡 AI-Refined: <b>{ar_pct:.1f}%</b></span>
                    <span style="color: #991B1B; font-weight: 600;">🔴 AI-Generated: <b>{ag_pct:.1f}%</b></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Telemetry Metrics Cards
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric(t("checker.metric_raw_bytes", "Raw Text Bytes"), f"{metrics.get('raw_bytes', 0):,} B")
        with m_col2:
            st.metric("zlib Ratio (Lvl 9)", f"{metrics.get('zlib_ratio', 1.0):.3f}")
        with m_col3:
            st.metric("lzma Ratio (Pre 9)", f"{metrics.get('lzma_ratio', 1.0):.3f}")
        with m_col4:
            st.metric("Entropic Perplexity", f"{metrics.get('entropy_perplexity', 0.0):.1f} / 100")

        # Interactive Span Risk Reader
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"##### {t('checker.spans_header', '🔍 Interactive Span Risk Reader')}")
        st.caption(
            "Visual sentence predictability breakdown: "
            "🟢 Low Risk (<35%) | 🟡 Moderate Risk (35-60%) | 🔴 High Predictability (>60%)"
        )

        span_html_pieces: List[str] = []
        for s in spans:
            stext = html.escape(s.get("text", ""))
            s_risk = html.escape(str(s.get("risk", "LOW")))
            s_score = s.get("score", 0.0)

            if s_risk == "HIGH":
                style = "background-color: #FEE2E2; color: #991B1B; padding: 2px 4px; border-radius: 4px; margin: 0 2px;"
            elif s_risk == "MODERATE":
                style = "background-color: #FFFBEB; color: #92400E; padding: 2px 4px; border-radius: 4px; margin: 0 2px;"
            else:
                style = "background-color: #ECFDF5; color: #065F46; padding: 2px 4px; border-radius: 4px; margin: 0 2px;"

            span_html_pieces.append(
                f'<span style="{style}" title="AI Risk: {s_score:.1f}% ({s_risk})">{stext}</span>'
            )

        rendered_reader_html = " ".join(span_html_pieces)

        st.markdown(
            f"""
            <div style="padding: 16px 20px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 10px; font-family: var(--th-font-sans); font-size: 0.95rem; line-height: 1.8;">
                {rendered_reader_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
