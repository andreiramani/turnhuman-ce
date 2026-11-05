"""TurnHuman Port Resolution & Dynamic Allocation Manager (v3.0.0-PROD).

Provides:
- Three-tier cascading port resolution (8501 -> 8502 -> random pool 8503..8600).
- Non-blocking socket probing with cross-platform exclusive binding.
- Asset decoupled configuration reading from configs/global_config.json.
- Adheres to Section 7 Code Standards (<= 450 LOC).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import random
import socket
from typing import Optional, Tuple

logger = logging.getLogger("TurnHuman.core.port_manager")

DEFAULT_PRIMARY_PORT = 8501
DEFAULT_SECONDARY_PORT = 8502
DEFAULT_FALLBACK_RANGE = (8503, 8600)
DEFAULT_BIND_HOST = "127.0.0.1"

__all__ = [
    "is_port_available",
    "resolve_server_port",
    "DEFAULT_PRIMARY_PORT",
    "DEFAULT_SECONDARY_PORT",
    "DEFAULT_FALLBACK_RANGE",
    "DEFAULT_BIND_HOST",
]


def is_port_available(port: int, host: str = DEFAULT_BIND_HOST) -> bool:
    """Check if a TCP port is available on the specified host by binding a temporary socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Cross-platform socket isolation:
        # On Windows, SO_EXCLUSIVEADDRUSE prevents port hijacking.
        # On POSIX, SO_REUSEADDR prevents lingering TIME_WAIT locking.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE") and os.name == "nt":
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            except OSError:
                pass
        elif hasattr(socket, "SO_REUSEADDR"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _load_port_config(config_path: Optional[str] = None) -> dict:
    """Load server port configuration from global_config.json with safe defaults."""
    if config_path:
        path = Path(config_path)
    else:
        path = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "global_config.json"

    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("server", {})
        except Exception as exc:
            logger.warning("Failed to load port config from %s: %s", path, exc)
    return {}


def resolve_server_port(
    config_path: Optional[str] = None,
    host: Optional[str] = None,
) -> Tuple[int, str]:
    """Resolve an available server port using the 3-tier cascade algorithm.

    Tiers:
    1. Primary port (8501)
    2. Secondary sequential fallback (8502)
    3. Randomized pool [8503..8600]
    4. Ephemeral OS fallback (port 0)

    Returns:
        tuple[int, str]: (resolved_port, allocation_type)
    """
    server_cfg = _load_port_config(config_path)
    primary = int(server_cfg.get("default_port", DEFAULT_PRIMARY_PORT))
    secondary = int(server_cfg.get("secondary_port", DEFAULT_SECONDARY_PORT))
    fb_range = server_cfg.get("fallback_port_range", list(DEFAULT_FALLBACK_RANGE))
    bind_host = host or server_cfg.get("bind_address", DEFAULT_BIND_HOST)

    # Tier 1: Check primary port (8501)
    if is_port_available(primary, host=bind_host):
        logger.info("Allocated primary port %d", primary)
        return primary, "primary"

    logger.warning("Primary port %d is occupied. Trying secondary port %d...", primary, secondary)

    # Tier 2: Check secondary port (8502)
    if is_port_available(secondary, host=bind_host):
        logger.info("Allocated secondary port %d", secondary)
        return secondary, "secondary"

    logger.warning("Secondary port %d is occupied. Resolving from randomized pool %s...", secondary, fb_range)

    # Tier 3: Randomized pool [8503..8600]
    start_p, end_p = int(fb_range[0]), int(fb_range[1])
    candidate_ports = list(range(start_p, end_p + 1))
    random.shuffle(candidate_ports)

    for cand_port in candidate_ports:
        if is_port_available(cand_port, host=bind_host):
            logger.info("Allocated randomized pool port %d", cand_port)
            return cand_port, "random_fallback"

    # Tier 4: Emergency OS ephemeral fallback (Port 0)
    logger.error("All ports in range %d-%d are exhausted. Falling back to OS ephemeral port 0.", start_p, end_p)
    return 0, "os_ephemeral"
