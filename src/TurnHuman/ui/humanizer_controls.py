"""TurnHuman Humanizer Controls Component (v3.0.0-PROD).

Provides parameter controls, 14 transformation stage badges,
and custom protected terms parsing for Module 1 (Humanizer).
Adheres to Section 7 Code Standards (<= 450 LOC).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any, List, Set

import streamlit as st

from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.humanizer_controls")


@dataclass(frozen=True)
class HumanizerConfig:
    """Configuration container for humanizer execution."""

    mode: str
    synonym_probability: float
    use_random_seed: bool
    domain: str
    protected_terms: set[str]
    is_ze: bool


def _parse_protected_terms(custom_terms_str: str, uploaded_json: Any) -> set[str]:
    """Parse comma-separated text input and uploaded JSON into a set of protected terms."""
    terms_list: List[str] = []
    if custom_terms_str.strip():
        for term in custom_terms_str.split(","):
            term_clean = term.strip()
            if term_clean:
                terms_list.append(term_clean)

    if uploaded_json is not None:
        try:
            data = json.load(uploaded_json)
            if isinstance(data, list):
                terms_list.extend([str(item).strip() for item in data if item])
            elif isinstance(data, dict):
                terms = data.get("protected_terms", [])
                if isinstance(terms, list):
                    terms_list.extend([str(item).strip() for item in terms if item])
        except Exception as exc:
            st.warning(f"Could not parse uploaded JSON terms: {exc}")

    return set(terms_list)


def _render_knobs_expander(is_ze: bool) -> tuple[str, Any]:
    """Render the 14 transformation knob cards and protected terms controls."""
    with st.expander(
        t("humanizer.cfg_expander", "⚙️ Advanced Transformation Settings & Protected Terms (14 Knobs)"),
        expanded=False,
    ):
        st.markdown(
            """
            <div style="font-size: 0.825rem; color: var(--th-text-secondary, #334155); margin-bottom: 12px;">
                Inspect and verify active modular transformation stages. In <b>Strict Zero-Expansion Mode</b>,
                stages that expand token counts are mathematically locked to preserve 0 net words added.
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">1. Phrase Rewrites (Stage 2)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Replaces multi-word AI cliches with concise academic equivalents.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">2. POS Synonyms (Stage 3)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">1:1 POS-validated lexical substitution.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">3. Clause Reordering (Stage 4)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Inverts subordinate and main clauses via dependency parsing.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">4. Determiner Swapping (Stage 5)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Swaps equivalent formal determiners (this/the/such).</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">5. Sentence Split (Stage 6)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Deconstructs overly verbose compound sentences.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            hedge_badge = "🔴 Disabled in ZE" if is_ze else "🔴 Adds Words"
            fusion_badge = "🔴 Disabled in ZE" if is_ze else "🔴 Adds Words"
            trans_badge = "🔴 Disabled in ZE" if is_ze else "🔴 Adds Words"
            st.markdown(
                f"""
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">6. Hedge Words (Stage 7)</b>
                        <span class="ze-badge ze-badge-expand">{hedge_badge}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Scientific softening hedges ("potentially", "suggests").</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">7. N-Gram Chain Breaker (Stage 8)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Disrupts contiguous 5-gram matches against source.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">8. Voice Transform (Stage 9)</b>
                        <span class="ze-badge ze-badge-drift">🟡 Bounded (±1-2)</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Rotates Active ↔ Passive constructions via nsubj/dobj.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">9. Sentence Fusion (Stage 10)</b>
                        <span class="ze-badge ze-badge-expand">{fusion_badge}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Merges short adjacent sentences with semicolons.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">10. Transition Injection (Stage 11)</b>
                        <span class="ze-badge ze-badge-expand">{trans_badge}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">FIFO-controlled discourse connectors.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            nom_badge = "🔴 Disabled in ZE" if is_ze else "🔴 Adds Words"
            app_badge = "🔴 Disabled in ZE" if is_ze else "🔴 Adds Words"
            st.markdown(
                f"""
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">11. Within-Clause (Stage 12)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Reorders prepositional phrases and adverbials.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">12. Nominalization (Stage 13)</b>
                        <span class="ze-badge ze-badge-expand">{nom_badge}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Converts verb phrases to formal academic nouns.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">13. Appositives (Stage 14)</b>
                        <span class="ze-badge ze-badge-expand">{app_badge}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Injects clarifying non-restrictive noun phrases.</div>
                </div>
                <div style="padding: 8px 10px; background: var(--th-bg-surface, #FFF); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 6px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size: 0.85rem;">14. Discourse Markers (Stage 15)</b>
                        <span class="ze-badge ze-badge-neutral">🟢 0 Words</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--th-text-muted, #64748B);">Rotates PDTB 2.0 discourse relation connectives.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("##### 🔒 Custom Protected Terms")
        c_terms_text, c_terms_file = st.columns([2, 1])

        with c_terms_text:
            custom_terms_str = st.text_input(
                "Protected Terms & Acronyms (Comma-Separated)",
                value="",
                placeholder="e.g., CNN, Backpropagation, CRISPR-Cas9, Monte Carlo, PyTorch",
                help="Terms in this list are guaranteed never to be substituted or modified by any stage.",
            )

        with c_terms_file:
            uploaded_json = st.file_uploader(
                "Upload Protected Terms JSON",
                type=["json"],
                help='Upload a JSON array of strings: ["Term1", "Term2"]',
            )

    return custom_terms_str, uploaded_json


def render_humanizer_controls() -> HumanizerConfig:
    """Render the primary top controls and advanced knobs for the humanizer workstation."""
    c_mode, c_prob, c_domain = st.columns([1.5, 1.2, 1.3])

    with c_mode:
        mode_option = st.radio(
            "Transformation Mode",
            ["zero_expansion", "full"],
            format_func=lambda x: (
                "🟢 Strict Zero-Expansion (0 Net Words)"
                if x == "zero_expansion"
                else "⚡ Full Humanization Pipeline"
            ),
            help=(
                "Strict Zero-Expansion guarantees output word count exactly matches input count (0 net words added). "
                "Expanding stages (hedge words, transitions, appositives, nominalizations, sentence fusion) are disabled."
            ),
        )

    with c_prob:
        syn_prob = st.slider(
            "Synonym Alignment Probability",
            min_value=0.50,
            max_value=1.00,
            value=0.80,
            step=0.05,
            help="Higher values substitute more adjectives/nouns while verifying POS tags.",
        )
        use_random_seed = st.checkbox(
            "Random Human Variation",
            value=True,
            help="Uses a dynamic seed for varied deterministic phrasing; uncheck for fixed deterministic output.",
        )

    with c_domain:
        domain_display_map = {
            "all": "All Disciplines (General)",
            "computer_science": "Computer Science",
            "engineering_physics": "Engineering & Physics",
            "mathematics_statistics": "Mathematics & Statistics",
            "medical_life_sciences": "Medical & Life Sciences",
            "quantitative_finance": "Quantitative Finance",
        }
        domain_choice = st.selectbox(
            "Academic Register / Domain",
            options=list(domain_display_map.keys()),
            format_func=lambda x: domain_display_map[x],
            help="Restricts synonym pools and phrase rewrites to the selected academic field.",
        )

    is_ze = mode_option == "zero_expansion"
    custom_terms_str, uploaded_json = _render_knobs_expander(is_ze)
    protected_terms = _parse_protected_terms(custom_terms_str, uploaded_json)

    return HumanizerConfig(
        mode=mode_option,
        synonym_probability=syn_prob,
        use_random_seed=use_random_seed,
        domain=domain_choice,
        protected_terms=protected_terms,
        is_ze=is_ze,
    )
