"""CrossRef REST API Client, Rate Limiter & Cache Manager (v3.0.1-MODULAR)."""

from __future__ import annotations

import collections
import json
import logging
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.error
import urllib.parse
import urllib.request

from TurnHuman.core.citation_formatter import _generate_citation_key

logger = logging.getLogger("TurnHuman.core.crossref_client")

CROSSREF_API_URL = "https://api.crossref.org/works"
DEFAULT_USER_AGENT = "TurnHuman/3.0 (mailto:engineering@turnhuman.org)"
DEFAULT_MAX_QUERIES_PER_MINUTE = 50
DEFAULT_TIMEOUT = 5.0

def _load_max_queries_config() -> int:
    """Load crossref_max_queries_per_minute from global_config.json."""
    config_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "configs"
        / "global_config.json"
    )
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            limits = data.get("rate_limits", {})
            return int(limits.get("crossref_max_queries_per_minute", DEFAULT_MAX_QUERIES_PER_MINUTE))
        except Exception:
            pass
    return DEFAULT_MAX_QUERIES_PER_MINUTE


class CrossRefRateLimiter:
    """Thread-safe sliding-window rate limiter honoring CrossRef API etiquette."""

    def __init__(self, max_queries: int = 50, window_seconds: float = 60.0) -> None:
        self.max_queries = max_queries
        self.window_seconds = window_seconds
        self._timestamps: collections.deque[float] = collections.deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Wait until a query slot is available within the sliding window."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_queries:
                sleep_time = self._timestamps[0] + self.window_seconds - now + 0.05
                if sleep_time > 0:
                    time.sleep(sleep_time)
            self._timestamps.append(time.time())

    def reset(self) -> None:
        """Clear recorded timestamps (primarily for test isolation)."""
        with self._lock:
            self._timestamps.clear()




class CrossRefClientMixin:
    """Mixin providing CrossRef REST API DOI resolution, searching, and caching."""


    def resolve_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Resolve metadata for a specific DOI using CrossRef REST API."""
        clean_doi = doi.strip()
        if clean_doi.startswith("https://doi.org/"):
            clean_doi = clean_doi[len("https://doi.org/"):]
        elif clean_doi.startswith("http://dx.doi.org/"):
            clean_doi = clean_doi[len("http://dx.doi.org/"):]

        cache_key = f"doi:{clean_doi.lower()}"
        with self._cache_lock:
            if cache_key in self._doi_cache:
                return dict(self._doi_cache[cache_key])

        # Rate limit compliance
        self.rate_limiter.acquire()

        encoded_doi = urllib.parse.quote(clean_doi, safe="/:")
        url = f"{CROSSREF_API_URL}/{encoded_doi}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    item = data.get("message", {})
                    paper = self._normalize_crossref_item(item)
                    with self._cache_lock:
                        self._doi_cache[cache_key] = paper
                    return paper
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as exc:
            logger.warning("CrossRef DOI lookup failed for '%s': %s", clean_doi, exc)

        return None

    def search_crossref(self, query: str, rows: int = 3) -> List[Dict[str, Any]]:
        """Search CrossRef for publications matching a title or bibliographic query.

        Implements graceful degradation: falls back to matching local taxonomy landmark
        papers or structured BibTeX templates on network failure or empty results.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        cache_key = f"query:{clean_query.lower()}:{rows}"
        with self._cache_lock:
            if cache_key in self._query_cache:
                return [dict(p) for p in self._query_cache[cache_key]]

        # Rate limit compliance
        self.rate_limiter.acquire()

        params = urllib.parse.urlencode({"query.bibliographic": clean_query, "rows": rows})
        url = f"{CROSSREF_API_URL}?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    items = data.get("message", {}).get("items", [])
                    results = [self._normalize_crossref_item(item) for item in items]
                    if results:
                        with self._cache_lock:
                            self._query_cache[cache_key] = results
                        return results
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception) as exc:
            logger.warning(
                "CrossRef search failed for query '%s' (%s). Triggering offline fallback.",
                clean_query,
                exc,
            )

        # Offline Fallback Mechanics
        fallback_results = self._fallback_search(clean_query, rows)
        with self._cache_lock:
            self._query_cache[cache_key] = fallback_results
        return fallback_results

    def _fallback_search(self, query: str, rows: int = 3) -> List[Dict[str, Any]]:
        """Offline fallback: search local taxonomy landmark papers or return valid template."""
        query_lower = query.lower()
        all_landmarks = self.get_landmark_papers()
        matched: List[Dict[str, Any]] = []

        # Find landmark papers matching title, authors, or key
        for p in all_landmarks:
            title = p.get("title", "").lower()
            key = p.get("key", "").lower()
            authors = " ".join([str(a).lower() for a in p.get("authors", [])])

            if any(term in title or term in key or term in authors for term in query_lower.split()):
                matched.append(p)
                if len(matched) >= rows:
                    break

        if matched:
            return matched

        # If no landmark matched, generate structured valid template
        template_key = re.sub(r"[^a-zA-Z0-9]", "", query_lower.split()[0] if query_lower else "ref")
        fallback_paper = {
            "key": f"{template_key}2026turnhuman",
            "title": query.capitalize(),
            "authors": ["TurnHuman Academic Reference"],
            "year": 2026,
            "journal": "Academic Working Papers",
            "doi": "",
            "note": "Offline fallback reference generated by TurnHuman v3.0",
            "_fallback": True,
        }
        return [fallback_paper]

    def _normalize_crossref_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert raw CrossRef JSON item into a standardized TurnHuman paper dict."""
        titles = item.get("title", [])
        title = titles[0] if titles else "Untitled Work"

        # Authors extraction
        raw_authors = item.get("author", [])
        authors = []
        for a in raw_authors:
            family = a.get("family", "")
            given = a.get("given", "")
            if family and given:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif "name" in a:
                authors.append(a["name"])

        # Journal / Container
        containers = item.get("container-title", [])
        journal = containers[0] if containers else ""

        # Year extraction
        pub_info = (
            item.get("published-print")
            or item.get("published-online")
            or item.get("created")
            or {}
        )
        date_parts = pub_info.get("date-parts", [[None]])
        year = date_parts[0][0] if date_parts and date_parts[0] else 2026

        doi = item.get("DOI", "")
        url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        volume = item.get("volume", "")
        issue = item.get("issue", "")
        page = item.get("page", "")
        work_type = item.get("type", "journal-article")

        paper = {
            "title": title,
            "authors": authors or ["Unknown Author"],
            "journal": journal,
            "year": year or 2026,
            "volume": volume,
            "issue": issue,
            "pages": page,
            "doi": doi,
            "url": url,
            "type": work_type,
        }
        paper["key"] = _generate_citation_key(paper)
        return paper

    # Citation Inserter & Risk-Driven Placement
