"""Mathematical Similarity Algorithms (Winnowing, Karp-Rabin, TF-IDF, LCS) (v3.0.1-MODULAR)."""

from __future__ import annotations

import collections
import difflib
import hashlib
import json
import logging
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("TurnHuman.core.similarity")

# Constants for Karp-Rabin polynomial rolling hash
_KR_BASE = 313
_KR_MOD = (1 << 32) - 1


def _load_similarity_config() -> Tuple[int, int, int]:
    """Load k, w, and ngram_length from configs/global_config.json."""
    config_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "configs"
        / "global_config.json"
    )
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            sim = data.get("similarity", {})
            win = sim.get("winnowing", {})
            k = int(win.get("k", 5))
            w = int(win.get("w", 4))
            ngram_len = int(sim.get("ngram_contiguous_length", 5))
            return k, w, ngram_len
        except Exception as exc:
            logger.warning("Failed to parse global_config.json: %s. Using defaults.", exc)
    return 5, 4, 5


def tokenize_words(text: str) -> List[str]:
    """Normalize and tokenize text into clean lowercase words."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_\-\u00C0-\u024F]+\b", text.lower())


def _word_hash(word: str) -> int:
    """Compute polynomial hash for a single word."""
    h = 0
    for ch in word:
        h = (h * 31 + ord(ch)) % _KR_MOD
    return h


def compute_karp_rabin_hashes(words: List[str], k: int = 5) -> List[int]:
    """Compute Karp-Rabin rolling hashes for sequential k-grams in O(N)."""
    n = len(words)
    if n < k:
        return []

    word_hashes = [_word_hash(w) for w in words]
    base_k_minus_1 = pow(_KR_BASE, k - 1, _KR_MOD)

    # Compute initial window hash
    h = 0
    for j in range(k):
        h = (h * _KR_BASE + word_hashes[j]) % _KR_MOD

    hashes = [h]

    # Roll window across remainder of tokens
    for i in range(n - k):
        h = (h - word_hashes[i] * base_k_minus_1) % _KR_MOD
        h = (h * _KR_BASE + word_hashes[i + k]) % _KR_MOD
        h = (h + _KR_MOD) % _KR_MOD
        hashes.append(h)

    return hashes


def compute_winnowing_fingerprints(
    words: List[str],
    k: int = 5,
    w: int = 4,
) -> Set[int]:
    """Extract Winnowing fingerprint set using rolling Karp-Rabin hashes.

    Guarantee: In any sequence of k + w - 1 identical words (e.g. 5 + 4 - 1 = 8),
    at least one identical fingerprint is guaranteed to be chosen.
    """
    n = len(words)
    if n < k:
        return set()

    k_hashes = compute_karp_rabin_hashes(words, k)
    if not k_hashes:
        return set()

    m = len(k_hashes)
    if m < w:
        return {min(k_hashes)}

    fingerprints: Set[int] = set()

    # Sliding window of size w over k-gram hashes
    for i in range(m - w + 1):
        window = k_hashes[i : i + w]
        min_val = min(window)
        # Select rightmost minimum in window per Winnowing specification
        fingerprints.add(min_val)

    return fingerprints


def compute_ngram_overlap(
    words_a: List[str],
    words_b: List[str],
    n: int = 5,
) -> Tuple[float, List[str]]:
    """Compute contiguous n-gram overlap ratio and list of matching n-grams."""
    if not words_a and not words_b:
        return 1.0, []
    if not words_a or not words_b:
        return 0.0, []

    if len(words_a) < n or len(words_b) < n:
        if words_a == words_b:
            return 1.0, [" ".join(words_a)]
        # For short sequences below n words, check shared tokens
        shared = set(words_a).intersection(set(words_b))
        ratio = (2.0 * len(shared)) / (len(set(words_a)) + len(set(words_b)))
        return round(ratio, 4), [" ".join(shared)] if shared else []

    ngrams_a = [tuple(words_a[i : i + n]) for i in range(len(words_a) - n + 1)]
    ngrams_b = [tuple(words_b[i : i + n]) for i in range(len(words_b) - n + 1)]

    set_a = set(ngrams_a)
    set_b = set(ngrams_b)
    shared = set_a.intersection(set_b)

    total_unique = len(set_a) + len(set_b)
    ratio = (2.0 * len(shared)) / total_unique if total_unique > 0 else 0.0

    matching_strings = [" ".join(gram) for gram in list(shared)[:50]]
    return round(ratio, 4), matching_strings


def compute_cosine_tfidf(words_a: List[str], words_b: List[str]) -> float:
    """Compute Cosine TF-IDF term overlap between two tokenized documents."""
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    if words_a == words_b:
        return 1.0

    vocab = sorted(set(words_a).union(set(words_b)))
    len_a = len(words_a)
    len_b = len(words_b)

    counts_a: Dict[str, int] = {}
    for w in words_a:
        counts_a[w] = counts_a.get(w, 0) + 1

    counts_b: Dict[str, int] = {}
    for w in words_b:
        counts_b[w] = counts_b.get(w, 0) + 1

    # In two-document comparison: DF is 2 if term in both, 1 if term in one
    # IDF: ln(2 / DF) + 1.0
    dot_product = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0

    for term in vocab:
        in_a = term in counts_a
        in_b = term in counts_b
        df = (1 if in_a else 0) + (1 if in_b else 0)
        idf = math.log(2.0 / df) + 1.0

        tfidf_a = (counts_a.get(term, 0) / len_a) * idf
        tfidf_b = (counts_b.get(term, 0) / len_b) * idf

        dot_product += tfidf_a * tfidf_b
        norm_a_sq += tfidf_a * tfidf_a
        norm_b_sq += tfidf_b * tfidf_b

    if norm_a_sq == 0.0 or norm_b_sq == 0.0:
        return 0.0

    cosine = dot_product / (math.sqrt(norm_a_sq) * math.sqrt(norm_b_sq))
    return round(max(0.0, min(1.0, cosine)), 4)


def compute_lcs_length(words_a: List[str], words_b: List[str]) -> int:
    """Compute word-level Longest Common Subsequence length using 2-row DP."""
    if not words_a or not words_b:
        return 0

    if words_a == words_b:
        return len(words_a)

    # Space-optimized 2-row dynamic programming
    if len(words_a) < len(words_b):
        short, long_ = words_a, words_b
    else:
        short, long_ = words_b, words_a

    n = len(short)
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)

    for w_l in long_:
        for j in range(1, n + 1):
            if w_l == short[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = curr[j - 1] if curr[j - 1] > prev[j] else prev[j]
        prev = list(curr)

    return prev[n]


def extract_matching_passages(
    words_a: List[str],
    words_b: List[str],
    min_tokens: int = 3,
) -> List[Dict[str, Any]]:
    """Extract contiguous matching passages between Doc A and Doc B."""
    if not words_a or not words_b:
        return []

    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    blocks = matcher.get_matching_blocks()
    passages: List[Dict[str, Any]] = []

    for block in blocks:
        if block.size >= min_tokens:
            passage_tokens = words_a[block.a : block.a + block.size]
            passages.append({
                "passage": " ".join(passage_tokens),
                "start_idx_a": block.a,
                "end_idx_a": block.a + block.size,
                "start_idx_b": block.b,
                "end_idx_b": block.b + block.size,
                "length_words": block.size,
            })

    return passages


