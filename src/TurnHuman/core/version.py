"""TurnHuman Dynamic Project Version Resolver (v3.0.0-PROD).

Provides:
- Dynamic resolution of project version from configs/global_config.json (SSOT).
- Graceful fallback to rules/VERSION.json.
- Full zero-hardcoding compliance across CLI launchers and UI presentation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("TurnHuman.core.version")

DEFAULT_VERSION = "3.1.0"

__all__ = ["get_project_version", "DEFAULT_VERSION"]


def get_project_version(
    short: bool = False,
    config_path: Optional[str] = None,
) -> str:
    """Dynamically resolve the TurnHuman project version.

    Reads from configs/global_config.json (Single Source of Truth).
    If short is True, transforms semantic version '3.1.0' into '3.1'.

    Args:
        short: If True, returns major.minor (e.g. '3.1').
        config_path: Optional custom path to global_config.json.

    Returns:
        str: Resolved version string (e.g. '3.1.0' or '3.1').
    """
    version_str: Optional[str] = None
    root_dir = Path(__file__).resolve().parent.parent.parent.parent

    # 1. Primary SSOT: configs/global_config.json
    cfg_file = Path(config_path) if config_path else root_dir / "configs" / "global_config.json"
    if cfg_file.is_file():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                val = data.get("project", {}).get("version")
                if val:
                    version_str = str(val).strip()
        except Exception as exc:
            logger.debug("Failed to read version from %s: %s", cfg_file, exc)

    # 2. Secondary fallback: rules/VERSION.json
    if not version_str:
        rules_ver_file = root_dir / "rules" / "VERSION.json"
        if rules_ver_file.is_file():
            try:
                with open(rules_ver_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = data.get("version")
                    if val:
                        version_str = str(val).strip()
            except Exception:
                pass

    if not version_str:
        version_str = DEFAULT_VERSION

    if short:
        parts = version_str.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"

    return version_str
