"""TurnHuman Main Application Entrypoint & Modular Navigation Router.

Authoritative Specification: PLAN.md (PROD).
Features:
- Streamlit wide-layout page setup.
- Modern Academic WCAG AA design system injection.
- Zero file-watcher invariant compliance (dynamic lazy importing).
- Sliding-window rate limiter & traffic offload cluster guard.
- Full 5-module workstation routing:
  1. Plagiarism & AI Humanizer
  2. Code Comment Humanizer
  3. Citation & BibTeX Inserter
  4. ZipPy Entropy Checker
  5. Document Similarity Comparator
- Standardized Andrei Ramani Footer & QuillBot AI Detector verification.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
import sys

# Ensure src/ is on sys.path for robust standalone execution
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

# Core dynamic resolution not needed for static CE brand
from TurnHuman.ui import common
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.app")

app_version_short = "CE"

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="TurnHuman CE - Academic Linguistic Engineering",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. Design System Injection & Session State Initializer
# -----------------------------------------------------------------------------
common.inject_custom_css()
common.init_session_state()

# -----------------------------------------------------------------------------
# 3. Sidebar Shell: Brand Banner, Traffic Guard & Navigation
# -----------------------------------------------------------------------------
with st.sidebar:
    brand_title = t("brand.title", "🛡️ TurnHuman <span>CE</span>")
    brand_meta = html.escape(t("brand.meta", "Zero-Retention In-Memory Core"))
    st.markdown(
        f"""
        <div class="sidebar-brand-box">
            <h3 class="sidebar-brand-title">{brand_title}</h3>
            <div class="sidebar-brand-meta">
                {brand_meta}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Language Switcher (Option A: 🇺🇸 English (US) / 🇮🇩 Bahasa Indonesia)
    common.render_language_selector()

    # Rate Limiter Gatekeeper
    rate_ok, req_count = common.check_session_rate_limit(max_rpm=30)
    if not rate_ok:
        st.error(t("common.rate_limit_stop", "⚠️ Rate limit reached (30 requests/minute). Please slow down."))
        st.stop()

    # Module Navigation Selector
    st.markdown(f"##### {t('nav.workstations_header', '📚 Features & Tools')}")
    nav_options = [
        t("nav.humanizer", "1. Plagiarism & AI Humanizer"),
        t("nav.code", "2. Code Comment Humanizer"),
        t("nav.citation", "3. Citation & BibTeX Inserter"),
        t("nav.checker", "4. ZipPy Entropy Checker"),
        t("nav.similarity", "5. Document Similarity Comparator"),
    ]
    page_selection = st.radio(
        label=t("nav.select_label", "Select Engineering Module"),
        options=nav_options,
        index=0,
        key="main_nav_radio",
        label_visibility="collapsed",
    )

    # Traffic Offload Guard (System Telemetry Local) placed below Features & Tools
    common.render_traffic_offload_guard()


    # Graceful Local Server Shutdown Popover
    common.render_shutdown_button()


# -----------------------------------------------------------------------------
# 4. Lazy Page Dispatcher (Zero File-Watcher Invariant)
# -----------------------------------------------------------------------------
if page_selection.startswith("1"):
    from TurnHuman.ui import humanizer_ui

    humanizer_ui.render_humanizer_page()

elif page_selection.startswith("2"):
    from TurnHuman.ui import code_ui

    code_ui.render_code_page()

elif page_selection.startswith("3"):
    from TurnHuman.ui import citation_ui

    citation_ui.render_citation_page()

elif page_selection.startswith("4"):
    from TurnHuman.ui import checker_ui

    checker_ui.render_checker_page()

elif page_selection.startswith("5"):
    from TurnHuman.ui import similarity_ui

    similarity_ui.render_similarity_page()


# -----------------------------------------------------------------------------
# 5. Global Standardized Andrei Ramani Footer
# -----------------------------------------------------------------------------
common.render_footer()
