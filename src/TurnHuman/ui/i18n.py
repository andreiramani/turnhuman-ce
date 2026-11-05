"""TurnHuman UI Internationalization (i18n) Engine.

Authoritative Specification: PLAN_UI_I18N.md (v3.0.0-PROD).
Provides lazy-loaded, in-memory string localization with English fallback.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger("TurnHuman.ui.i18n")

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "🇺🇸 English (US)",
    "id": "🇮🇩 Bahasa Indonesia",
}

# In-memory dictionary cache to prevent disk reads on re-renders
_TRANSLATION_CACHE: Dict[str, Dict[str, Any]] = {}


def load_locale(lang: str) -> Dict[str, Any]:
    """Load JSON translation locale into memory RAM once."""
    if lang in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[lang]

    locale_path = LOCALES_DIR / f"{lang}.json"
    if not locale_path.exists():
        logger.warning("Locale file '%s' not found. Using fallback dictionary.", locale_path)
        return {}

    try:
        with open(locale_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            _TRANSLATION_CACHE[lang] = data
            return data
    except Exception as exc:
        logger.error("Failed to parse locale '%s': %s", locale_path, exc)
        return {}


def get_current_language() -> str:
    """Retrieve current UI language code from session state (defaults to 'en')."""
    if "ui_lang" not in st.session_state:
        st.session_state["ui_lang"] = DEFAULT_LANGUAGE
    return st.session_state["ui_lang"]


def set_current_language(lang: str) -> None:
    """Update current active UI language code in session state."""
    if lang in SUPPORTED_LANGUAGES:
        st.session_state["ui_lang"] = lang


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """Retrieve localized text for a dot-notation key with fallback and interpolation.

    Resolution order:
    1. Look up key in active language dictionary (e.g. 'id').
    2. Fall back to default language dictionary ('en') if not found in active.
    3. Fall back to supplied `default` or the raw `key`.
    4. Interpolate kwargs using str.format(**kwargs) if present.
    """
    lang = get_current_language()
    val = _resolve_key(lang, key)

    if val is None and lang != DEFAULT_LANGUAGE:
        val = _resolve_key(DEFAULT_LANGUAGE, key)

    if val is None:
        val = default if default is not None else key

    if kwargs and isinstance(val, str):
        try:
            return val.format(**kwargs)
        except Exception as exc:
            logger.debug("Failed to interpolate format arguments in '%s': %s", key, exc)
            return val
    return val


def _resolve_key(lang: str, key: str) -> Optional[str]:
    """Traverse nested dictionary using dot-separated keys."""
    data = load_locale(lang)
    parts = key.split(".")
    curr: Any = data
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return str(curr) if curr is not None else None
