"""TurnHuman Document Similarity & Plagiarism Shielding Engine (v3.0.1-MODULAR)."""

from __future__ import annotations

import collections
import hashlib
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from TurnHuman.core.similarity_algorithms import (
    _load_similarity_config,
    _word_hash,
    compute_cosine_tfidf,
    compute_karp_rabin_hashes,
    compute_lcs_length,
    compute_ngram_overlap,
    compute_winnowing_fingerprints,
    extract_matching_passages,
    tokenize_words,
)

__all__ = [
    "compare_documents",
    "tokenize_words",
    "compute_karp_rabin_hashes",
    "compute_winnowing_fingerprints",
    "compute_ngram_overlap",
    "compute_cosine_tfidf",
    "compute_lcs_length",
    "extract_matching_passages",
]

def compare_documents(
    doc_a: str,
    doc_b: str,
    k: Optional[int] = None,
    w: Optional[int] = None,
) -> Dict[str, Any]:
    """Pairwise similarity comparison between Document A and Document B.

    Evaluates:
    - 5-Gram Contiguous Match Overlap
    - Winnowing Karp-Rabin Fingerprint Jaccard Similarity (8-word guarantee)
    - Cosine TF-IDF Term Overlap
    - Longest Common Subsequence (LCS) Ratio

    Args:
        doc_a: Text of Document A.
        doc_b: Text of Document B.
        k: Optional k-gram size override (defaults to global_config.json or 5).
        w: Optional window size override (defaults to global_config.json or 4).

    Returns:
        Structured dictionary with combined score, individual metrics,
        winnowing details, and synchronized matching passages.
    """
    default_k, default_w, default_ngram = _load_similarity_config()
    win_k = k if k is not None else default_k
    win_w = w if w is not None else default_w

    words_a = tokenize_words(doc_a)
    words_b = tokenize_words(doc_b)

    len_a = len(words_a)
    len_b = len(words_b)

    # Edge cases
    if len_a == 0 and len_b == 0:
        return {
            "combined_score": 100.0,
            "risk_category": "HIGH",
            "metrics": {
                "ngram_5_ratio": 1.0,
                "winnowing_jaccard": 1.0,
                "cosine_tfidf": 1.0,
                "lcs_ratio": 1.0,
                "lcs_length": 0,
            },
            "winnowing_details": {
                "k": win_k,
                "w": win_w,
                "doc_a_fingerprints_count": 0,
                "doc_b_fingerprints_count": 0,
                "shared_fingerprints_count": 0,
            },
            "matching_ngrams": [],
            "matching_passages": [],
            "doc_a_word_count": 0,
            "doc_b_word_count": 0,
        }

    if len_a == 0 or len_b == 0:
        return {
            "combined_score": 0.0,
            "risk_category": "LOW",
            "metrics": {
                "ngram_5_ratio": 0.0,
                "winnowing_jaccard": 0.0,
                "cosine_tfidf": 0.0,
                "lcs_ratio": 0.0,
                "lcs_length": 0,
            },
            "winnowing_details": {
                "k": win_k,
                "w": win_w,
                "doc_a_fingerprints_count": 0,
                "doc_b_fingerprints_count": 0,
                "shared_fingerprints_count": 0,
            },
            "matching_ngrams": [],
            "matching_passages": [],
            "doc_a_word_count": len_a,
            "doc_b_word_count": len_b,
        }

    # Identity shortcut
    if words_a == words_b:
        fp_identical = compute_winnowing_fingerprints(words_a, k=win_k, w=win_w)
        return {
            "combined_score": 100.0,
            "risk_category": "HIGH",
            "metrics": {
                "ngram_5_ratio": 1.0,
                "winnowing_jaccard": 1.0,
                "cosine_tfidf": 1.0,
                "lcs_ratio": 1.0,
                "lcs_length": len_a,
            },
            "winnowing_details": {
                "k": win_k,
                "w": win_w,
                "doc_a_fingerprints_count": len(fp_identical),
                "doc_b_fingerprints_count": len(fp_identical),
                "shared_fingerprints_count": len(fp_identical),
            },
            "matching_ngrams": [" ".join(words_a[i:i+default_ngram]) for i in range(min(5, max(1, len_a - default_ngram + 1)))],
            "matching_passages": [{
                "passage": " ".join(words_a),
                "start_idx_a": 0,
                "end_idx_a": len_a,
                "start_idx_b": 0,
                "end_idx_b": len_b,
                "length_words": len_a,
            }],
            "doc_a_word_count": len_a,
            "doc_b_word_count": len_b,
        }

    # 1. Metric 1: 5-Gram Contiguous Match
    ngram_ratio, matching_ngrams = compute_ngram_overlap(words_a, words_b, n=default_ngram)

    # 2. Metric 2: Winnowing Karp-Rabin Rolling Hash
    fp_a = compute_winnowing_fingerprints(words_a, k=win_k, w=win_w)
    fp_b = compute_winnowing_fingerprints(words_b, k=win_k, w=win_w)

    shared_fp = fp_a.intersection(fp_b)
    union_fp = fp_a.union(fp_b)
    winnowing_jaccard = round(len(shared_fp) / len(union_fp), 4) if union_fp else 0.0

    # 3. Metric 3: Cosine TF-IDF Term Overlap
    cosine_tfidf = compute_cosine_tfidf(words_a, words_b)

    # 4. Metric 4: Longest Common Subsequence (LCS)
    lcs_len = compute_lcs_length(words_a, words_b)
    lcs_ratio = round((2.0 * lcs_len) / (len_a + len_b), 4)

    # Synchronized matching passages
    matching_passages = extract_matching_passages(words_a, words_b, min_tokens=3)

    # Weighted combined similarity index
    combined = (
        0.30 * ngram_ratio
        + 0.30 * winnowing_jaccard
        + 0.20 * cosine_tfidf
        + 0.20 * lcs_ratio
    )
    combined_score = round(max(0.0, min(100.0, combined * 100.0)), 1)

    if combined_score >= 70.0:
        risk_category = "HIGH"
    elif combined_score >= 30.0:
        risk_category = "MODERATE"
    else:
        risk_category = "LOW"

    return {
        "combined_score": combined_score,
        "risk_category": risk_category,
        "metrics": {
            "ngram_5_ratio": ngram_ratio,
            "winnowing_jaccard": winnowing_jaccard,
            "cosine_tfidf": cosine_tfidf,
            "lcs_ratio": lcs_ratio,
            "lcs_length": lcs_len,
        },
        "winnowing_details": {
            "k": win_k,
            "w": win_w,
            "doc_a_fingerprints_count": len(fp_a),
            "doc_b_fingerprints_count": len(fp_b),
            "shared_fingerprints_count": len(shared_fp),
        },
        "matching_ngrams": matching_ngrams,
        "matching_passages": matching_passages,
        "doc_a_word_count": len_a,
        "doc_b_word_count": len_b,
    }
