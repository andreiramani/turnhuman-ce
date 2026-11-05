"""TurnHuman UI Common Utilities & Presentation Helpers (v3.0.0-PROD).

Provides:
- Design system CSS loader (assets/style.css).
- Session-based Rate Limiter (max 30 requests/min).
- Traffic Offload Guard & Cluster Status telemetry.
- Standardized Andrei Ramani Footer with QuillBot AI Content Detector link.
- Side-by-side HTML diff visualization with WCAG AA compliance.
- Session state initialization and configuration loaders.
"""

from __future__ import annotations

import difflib
import html
import json
import logging
import os
import signal
import threading
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import streamlit as st

from TurnHuman.ui import i18n

logger = logging.getLogger("TurnHuman.ui.common")

# Project root calculation
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "global_config.json"
CSS_PATH = PROJECT_ROOT / "assets" / "style.css"

# Default configuration fallback
DEFAULT_CONFIG = {
    "rate_limits": {
        "max_requests_per_minute": 30,
        "max_file_size_mb": 10,
        "max_batch_size_mb": 50,
        "crossref_max_queries_per_minute": 50,
    },
    "project": {
        "name": "TurnHuman Community Edition",
        "version": "3.1.0",
    },
}


# =============================================================================
# 1. Configuration & Session State
# =============================================================================

def get_global_config() -> Dict[str, Any]:
    """Load configuration from configs/global_config.json with graceful fallback."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            logger.warning("Failed to load global_config.json: %s; using default.", exc)
    return DEFAULT_CONFIG


def init_session_state() -> None:
    """Initialize necessary session state keys if not already present."""
    if "_request_timestamps" not in st.session_state:
        st.session_state["_request_timestamps"] = []
    if "_custom_protected_terms" not in st.session_state:
        st.session_state["_custom_protected_terms"] = []
    if "_current_module" not in st.session_state:
        st.session_state["_current_module"] = "1. Plagiarism & AI Humanizer"


# =============================================================================
# 2. CSS Injector
# =============================================================================

def inject_custom_css() -> None:
    """Inject assets/style.css into the Streamlit app.

    Enforces Modern Academic Design Language and WCAG 2.1 AA tokens.
    """
    if CSS_PATH.exists():
        try:
            css_content = CSS_PATH.read_text(encoding="utf-8")
            st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
            return
        except Exception as exc:
            logger.error("Failed to read assets/style.css: %s", exc)

    # Fallback minimal CSS
    st.markdown(
        """
        <style>
        :root {
            --th-cobalt: #2563EB;
            --th-emerald-safe: #10B981;
            --th-amber-warning: #F59E0B;
            --th-crimson-risk: #EF4444;
        }
        .diff-del { background-color: #FEE2E2; color: #991B1B; text-decoration: line-through; }
        .diff-add { background-color: #D1FAE5; color: #065F46; font-weight: 600; }
        .diff-prot { background-color: #EFF6FF; color: #1E40AF; border-radius: 4px; padding: 2px 4px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 3. Rate Limiter & Abuse Guard
# =============================================================================

def check_session_rate_limit(max_rpm: Optional[int] = None) -> Tuple[bool, int]:
    """Sliding-window rate limiter enforcing max requests/minute per session.

    Args:
        max_rpm: Maximum requests allowed in a 60-second window.
                 Defaults to value in configs/global_config.json (30).

    Returns:
        Tuple of (is_allowed: bool, current_request_count: int).
    """
    if max_rpm is None:
        cfg = get_global_config()
        max_rpm = int(cfg.get("rate_limits", {}).get("max_requests_per_minute", 30))

    if "_request_timestamps" not in st.session_state:
        st.session_state["_request_timestamps"] = []

    now = time.time()
    window_start = now - 60.0

    # Prune timestamps older than 60 seconds
    timestamps = [t for t in st.session_state["_request_timestamps"] if t >= window_start]

    if len(timestamps) >= max_rpm:
        st.session_state["_request_timestamps"] = timestamps
        return False, len(timestamps)

    # Record current request
    timestamps.append(now)
    st.session_state["_request_timestamps"] = timestamps
    return True, len(timestamps)


def check_rate_limit() -> bool:
    """Convenience gatekeeper: checks rate limit and renders warning if quota exceeded."""
    allowed, count = check_session_rate_limit()
    if not allowed:
        cfg = get_global_config()
        max_rpm = cfg.get("rate_limits", {}).get("max_requests_per_minute", 30)
        st.error(
            i18n.t(
                "common.rate_limit_exceeded",
                max=max_rpm,
                count=count,
                default=f"⚠️ **Rate Limit Exceeded:** You have reached the quota of {max_rpm} requests/minute ({count} requests recorded). Please wait a few moments before trying again.",
            )
        )
        return False
    return True


# =============================================================================
# 4. Language Selector & Traffic Offload Guard
# =============================================================================

def render_language_selector() -> str:
    """Render the language switcher in the sidebar (Option A with US and ID flags)."""
    current_lang = i18n.get_current_language()
    lang_keys = list(i18n.SUPPORTED_LANGUAGES.keys())
    current_idx = lang_keys.index(current_lang) if current_lang in lang_keys else 0

    selected_label = st.selectbox(
        label=i18n.t("brand.lang_selector_label", "🌐 Interface Language:"),
        options=[i18n.SUPPORTED_LANGUAGES[k] for k in lang_keys],
        index=current_idx,
        key="ui_language_selector",
    )

    label_to_code = {v: k for k, v in i18n.SUPPORTED_LANGUAGES.items()}
    selected_code = label_to_code.get(selected_label, "en")
    if selected_code != current_lang:
        i18n.set_current_language(selected_code)
        st.rerun()

    return selected_code


def render_traffic_offload_guard() -> None:
    """Render Local System Telemetry and RAM zero-retention health in sidebar."""
    cfg = get_global_config()
    version = cfg.get("project", {}).get("version", "3.0")

    # Dynamic status checks
    from TurnHuman.core.nlp_engine import is_spacy_available
    spacy_status = "spaCy en_core_web_sm (Active)" if is_spacy_available() else "Regex Fallback Mode"

    # Request meter
    timestamps = st.session_state.get("_request_timestamps", [])
    now = time.time()
    active_reqs = len([t for t in timestamps if t >= now - 60.0])
    max_rpm = cfg.get("rate_limits", {}).get("max_requests_per_minute", 30)

    title = i18n.t("telemetry.title", "🖥️ System Telemetry (Local)")
    status_lbl = i18n.t("telemetry.status_label", "Status:")
    status_val = i18n.t("telemetry.status_val", "🟢 Operational (Localhost)")
    host_text = i18n.t("telemetry.host", "• Host: <b>Local Workstation (Standalone)</b>")
    nlp_text = i18n.t("telemetry.nlp_engine", "• NLP Engine: <b>{status}</b>", status=spacy_status)
    rules_text = i18n.t("telemetry.rules_db", "• Rules Database: <b>(EN + ID)</b>")
    services_text = i18n.t("telemetry.core_services", "• Core Services: <b>8/8 Modules Active</b>")
    quota_text = i18n.t("telemetry.quota", "• Session Quota: <b>{active}/{max} req/min</b>", active=active_reqs, max=max_rpm)
    storage_text = i18n.t("telemetry.storage", "• Storage: <b>RAM Ephemeral (0 KB Disk)</b>")
    crossref_text = i18n.t("telemetry.crossref", "• CrossRef API: <b>Polite Pool (50 rpm)</b>")

    st.markdown(
        f"""
        <div class="traffic-guard-box" style="padding: 10px 12px; background: rgba(37,99,235,0.05); border: 1px solid var(--th-border-subtle, #E2E8F0); border-radius: 8px; margin-bottom: 14px;">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--th-cobalt, #2563EB); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                {title}
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--th-text-secondary, #334155); margin-bottom: 6px;">
                <span>{status_lbl}</span>
                <span style="font-weight: 700; color: #10B981;">{status_val}</span>
            </div>
            <div style="font-size: 0.72rem; color: var(--th-text-muted, #64748B); line-height: 1.5;">
                {host_text}<br>
                {nlp_text}<br>
                {rules_text}<br>
                {services_text}<br>
                {quota_text}<br>
                {storage_text}<br>
                {crossref_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 5. Standardized Andrei Ramani Footer & QuillBot Verification
# =============================================================================

def render_footer() -> None:
    """Render the standard Andrei Ramani footer with author attribution

    and prominent QuillBot AI Content Detector verification link.
    """
    brand_text = i18n.t("footer.brand", "🛡️ TurnHuman <span>CE</span> - Academic Linguistic Engineering")
    verify_title = i18n.t("footer.verify_title", "🔍 Paste your paragraph")
    verify_link = i18n.t("footer.verify_link", "on QuillBot AI Content Detector ↗")
    verify_tail = i18n.t("footer.verify_tail", "to check the AI content independently.")
    by_text = i18n.t("footer.by", "by: Andrei Ramani")
    meta_text = i18n.t("footer.meta", "TurnHuman • Zero Generative AI LLM Hallucination Risk")

    st.markdown(
        f"""
        <footer class="turnhuman-footer">
            <div class="footer-brand">
                {brand_text}
            </div>
            <div class="footer-verifier-box">
                {verify_title}
                <a href="https://quillbot.com/ai-content-detector" target="_blank" rel="noopener noreferrer" class="footer-quillbot-link">
                    {verify_link}
                </a>
                {verify_tail}
            </div>
            <div class="footer-badges-row">
                <a href="mailto:andreiramani@gmail.com" class="footer-pill-tag">{by_text}</a>
            </div>
            <div class="footer-meta">
                {meta_text}
            </div>
        </footer>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 6. Interactive Side-by-Side Diff Builder
# =============================================================================

def _tokenize_for_diff(text: str) -> List[str]:
    """Tokenize text into words, punctuation, and whitespace tokens."""
    import re

    return re.findall(r"\s+|\w+|[^\w\s]", text)


def _highlight_protected_terms(text: str, prot_set: Set[str]) -> str:
    """Highlight protected terms with a pill tag in already escaped text."""
    import re

    if not prot_set:
        return text

    sorted_terms = sorted(prot_set, key=len, reverse=True)
    res = text
    for term in sorted_terms:
        if not term:
            continue
        escaped_term = html.escape(term)
        if re.match(r"^\w+(?:\s+\w+)*$", escaped_term):
            pattern = re.compile(rf"\b({re.escape(escaped_term)})\b", re.IGNORECASE)
        else:
            pattern = re.compile(rf"({re.escape(escaped_term)})", re.IGNORECASE)
        res = pattern.sub(r'<span class="diff-prot">\1 🔒</span>', res)
    return res


def build_diff_html(
    original_text: str,
    modified_text: str,
    protected_terms: Optional[Set[str]] = None,
) -> Tuple[str, str]:
    """Generate high-contrast, WCAG AA compliant side-by-side HTML diff representations.

    - Original text displays deleted spans wrapped in <span class="diff-del">...</span>.
    - Modified text displays added spans wrapped in <span class="diff-add">...</span>.
    - Protected terms are highlighted with <span class="diff-prot">... 🔒</span>.

    Returns:
        Tuple of (original_column_html, modified_column_html).
    """
    if not original_text and not modified_text:
        return "", ""

    prot_set = {t.strip().lower() for t in (protected_terms or set()) if t.strip()}

    tokens_orig = _tokenize_for_diff(original_text)
    tokens_mod = _tokenize_for_diff(modified_text)

    matcher = difflib.SequenceMatcher(None, tokens_orig, tokens_mod)

    orig_html_parts: List[str] = []
    mod_html_parts: List[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        orig_chunk = "".join(tokens_orig[i1:i2])
        mod_chunk = "".join(tokens_mod[j1:j2])

        if tag == "equal":
            orig_html_parts.append(html.escape(orig_chunk))
            mod_chunk_escaped = html.escape(mod_chunk)
            mod_html_parts.append(_highlight_protected_terms(mod_chunk_escaped, prot_set))

        elif tag == "delete":
            escaped_chunk = html.escape(orig_chunk)
            orig_html_parts.append(f'<span class="diff-del">{escaped_chunk}</span>')

        elif tag == "insert":
            escaped_chunk = html.escape(mod_chunk)
            highlighted = _highlight_protected_terms(escaped_chunk, prot_set)
            mod_html_parts.append(f'<span class="diff-add">{highlighted}</span>')

        elif tag == "replace":
            escaped_orig = html.escape(orig_chunk)
            escaped_mod = html.escape(mod_chunk)

            orig_html_parts.append(f'<span class="diff-del">{escaped_orig}</span>')
            highlighted = _highlight_protected_terms(escaped_mod, prot_set)
            mod_html_parts.append(f'<span class="diff-add">{highlighted}</span>')

    orig_out = "".join(orig_html_parts).replace("\n", "<br>")
    mod_out = "".join(mod_html_parts).replace("\n", "<br>")

    return orig_out, mod_out
# =============================================================================
# 7. Graceful Server Shutdown Controller
# =============================================================================

def _trigger_delayed_shutdown(delay_sec: float = 0.8) -> None:
    """Gracefully terminate the Streamlit server process after delivering response to client."""
    time.sleep(delay_sec)
    try:
        from streamlit.runtime import Runtime
        runtime = Runtime.instance()
        if runtime:
            runtime.stop()
    except Exception as exc:
        logger.warning("Runtime.stop() error: %s", exc)
    finally:
        # Give a brief moment for WebSocket to flush close frame, then force process exit
        time.sleep(0.2)
        try:
            if os.name != "nt":
                os.kill(os.getpid(), signal.SIGINT)
                time.sleep(0.2)
        except Exception:
            pass
        # Unconditional clean exit (code 0) guarantees process dies and terminal returns to prompt
        os._exit(0)


def render_shutdown_button() -> None:
    """Render a 1-click icon power shutdown button with dynamic version tooltip in sidebar."""
    from TurnHuman.core.version import get_project_version

    version = get_project_version()
    tooltip_text = i18n.t(
        "common.shutdown_tooltip",
        f"Shutdown TurnHuman CE (v{version})",
        version=version,
    )
    progress_msg = i18n.t(
        "common.shutdown_in_progress",
        "🛑 TurnHuman server is shutting down. You may now close this browser tab.",
    )

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button(
        "",
        icon=":material/power_settings_new:",
        help=tooltip_text,
        key="btn_shutdown_power",
        use_container_width=True,
    ):
        st.sidebar.warning(progress_msg)
        threading.Thread(target=_trigger_delayed_shutdown, daemon=True).start()
