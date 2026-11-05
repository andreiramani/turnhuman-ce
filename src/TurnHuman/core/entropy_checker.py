"""TurnHuman ZipPy Entropic Perplexity Calculator (v3.0.0-PROD).

Evaluates text predictability, lexical compression ratios, and entropic perplexity
using dual zlib (level 9) and lzma (preset 9) compression on sliding windows.
Features:
- Composite Risk Percentage (0.0% to 100.0%)
- Trilateral Split (ai_generated_pct, ai_refined_pct, human_written_pct) summing to 100.0%
- Span Highlighting / Risk Segmentation (HIGH, MODERATE, LOW)
- Domain-Aware Thresholds (general, computer_science, mathematics_statistics,
  engineering_physics, medical_life_sciences, quantitative_finance)
"""

from __future__ import annotations

import logging
import lzma
import math
import re
import zlib
from typing import Any, Dict, List, Optional, Tuple

from TurnHuman.core.nlp_engine import NLPEngine

logger = logging.getLogger("TurnHuman.core.entropy_checker")

# Domain calibration offsets for compression ratio thresholds.
# Highly formulaic domains (CS, math, physics) naturally exhibit repeated
# technical syntax (e.g. 'let', 'function', 'equation', 'where'), so thresholds
# are adjusted downward to avoid false positives.
DOMAIN_CALIBRATION: Dict[str, Dict[str, float]] = {
    "general": {
        "low_cr": 0.50,   # Below this CR -> HIGH AI risk
        "high_cr": 0.76,  # Above this CR -> LOW AI risk (Human)
        "formulaic_factor": 1.0,
    },
    "computer_science": {
        "low_cr": 0.42,
        "high_cr": 0.68,
        "formulaic_factor": 0.88,
    },
    "mathematics_statistics": {
        "low_cr": 0.40,
        "high_cr": 0.65,
        "formulaic_factor": 0.84,
    },
    "engineering_physics": {
        "low_cr": 0.43,
        "high_cr": 0.69,
        "formulaic_factor": 0.90,
    },
    "medical_life_sciences": {
        "low_cr": 0.46,
        "high_cr": 0.72,
        "formulaic_factor": 0.94,
    },
    "quantitative_finance": {
        "low_cr": 0.44,
        "high_cr": 0.70,
        "formulaic_factor": 0.92,
    },
}


def compute_compression_ratios(text: str) -> Tuple[float, float, float]:
    """Calculate zlib, lzma, and mean compression ratios for a string.

    Returns:
        Tuple of (zlib_ratio, lzma_ratio, mean_ratio).
    """
    raw_bytes = text.encode("utf-8")
    raw_len = len(raw_bytes)
    if raw_len == 0:
        return 1.0, 1.0, 1.0

    zlib_comp = zlib.compress(raw_bytes, level=9)
    lzma_comp = lzma.compress(raw_bytes, preset=9)

    zlib_ratio = len(zlib_comp) / raw_len
    lzma_ratio = len(lzma_comp) / raw_len
    mean_ratio = (zlib_ratio + lzma_ratio) / 2.0

    return zlib_ratio, lzma_ratio, mean_ratio


def _calculate_score_from_cr(
    cr: float,
    raw_len: int,
    low_cr: float,
    high_cr: float,
    formulaic_factor: float = 1.0,
) -> float:
    """Map compression ratio to an AI risk score from 0.0 (Human) to 100.0 (AI).

    Adjusts for short string container header overhead.
    """
    if raw_len == 0:
        return 0.0

    effective_cr = cr

    if effective_cr <= low_cr:
        # High AI risk: 60.0 - 100.0
        normalized = max(0.0, effective_cr / max(0.01, low_cr))
        score = 100.0 - (normalized * 40.0)
    elif effective_cr >= high_cr:
        # Low AI risk (Human): 0.0 - 30.0
        span = max(0.01, 1.10 - high_cr)
        diff = min(span, effective_cr - high_cr)
        score = max(0.0, 30.0 - (diff / span * 30.0))
    else:
        # Moderate AI-refined risk: 30.0 - 60.0
        span = high_cr - low_cr
        progress = (effective_cr - low_cr) / max(0.01, span)
        score = 60.0 - (progress * 30.0)

    # Apply domain formulaic scaling
    adjusted_score = score * formulaic_factor
    return round(max(0.0, min(100.0, adjusted_score)), 1)


def _compute_span_contextual_cr(
    context_text: str,
    span_text: str,
) -> float:
    """Compute the contextual compression ratio of a span given preceding context.

    Uses information-theoretic delta compression:
    L(context + span) - L(context) divided by len(span).
    """
    raw_span = span_text.encode("utf-8")
    len_span = len(raw_span)
    if len_span == 0:
        return 1.0

    # Standalone net ratio with container header compensation
    zlib_span = zlib.compress(raw_span, level=9)
    net_zlib_len = max(1, len(zlib_span) - 6)
    standalone_cr = net_zlib_len / len_span

    if not context_text:
        return standalone_cr

    raw_ctx = context_text.encode("utf-8")
    comp_ctx = len(zlib.compress(raw_ctx, level=9))
    comp_comb = len(zlib.compress(raw_ctx + b" " + raw_span, level=9))
    incremental_ratio = max(0.01, (comp_comb - comp_ctx)) / len_span

    # Blend standalone and contextual ratios
    return 0.35 * standalone_cr + 0.65 * incremental_ratio


def evaluate_entropy(
    text: str,
    domain: str = "general",
    window_size: int = 200,
    step_size: int = 50,
) -> Dict[str, Any]:
    """Evaluate text predictability and compression perplexity.

    Args:
        text: The text to analyze.
        domain: Academic domain calibration key.
        window_size: Character size for sliding window analysis.
        step_size: Step size for sliding window strides.

    Returns:
        Structured evaluation dictionary containing:
        - composite_score: Overall AI risk percentage (0.0 to 100.0).
        - risk_level: "LOW", "MODERATE", or "HIGH".
        - trilateral_split: ai_generated_pct, ai_refined_pct, human_written_pct (sum == 100.0).
        - compression_metrics: Detailed raw/compressed byte counts and ratios.
        - spans: Sentence-level risk classifications for visual highlighting.
        - word_count and sentence_count.
    """
    clean_text = text.strip() if text else ""
    if not clean_text:
        return {
            "composite_score": 0.0,
            "risk_level": "LOW",
            "trilateral_split": {
                "ai_generated_pct": 0.0,
                "ai_refined_pct": 0.0,
                "human_written_pct": 100.0,
            },
            "domain": domain,
            "compression_metrics": {
                "raw_bytes": 0,
                "zlib_bytes": 0,
                "lzma_bytes": 0,
                "zlib_ratio": 1.0,
                "lzma_ratio": 1.0,
                "mean_ratio": 1.0,
                "entropy_perplexity": 0.0,
            },
            "spans": [],
            "word_count": 0,
            "sentence_count": 0,
        }

    domain_key = domain.strip().lower()
    calibration = DOMAIN_CALIBRATION.get(domain_key, DOMAIN_CALIBRATION["general"])
    low_cr = calibration["low_cr"]
    high_cr = calibration["high_cr"]
    formulaic_factor = calibration["formulaic_factor"]

    raw_bytes = clean_text.encode("utf-8")
    raw_len = len(raw_bytes)
    zlib_comp = zlib.compress(raw_bytes, level=9)
    lzma_comp = lzma.compress(raw_bytes, preset=9)

    zlib_ratio = round(len(zlib_comp) / raw_len, 4)
    lzma_ratio = round(len(lzma_comp) / raw_len, 4)
    mean_ratio = round((zlib_ratio + lzma_ratio) / 2.0, 4)

    # Entropic perplexity surrogate: higher mean_ratio implies higher entropy
    entropy_perplexity = round(mean_ratio * 100.0, 2)

    # Sentence segmentation and span-level risk scoring
    nlp = NLPEngine.get_instance()
    sentence_spans = nlp.get_sentence_spans(clean_text)
    if not sentence_spans:
        sentence_spans = [clean_text]

    spans_data: List[Dict[str, Any]] = []
    search_cursor = 0
    words_high = 0
    words_moderate = 0
    words_low = 0
    span_scores: List[float] = []

    for i, sent in enumerate(sentence_spans):
        sent_clean = sent.strip()
        if not sent_clean:
            continue

        sent_words = len(sent_clean.split())
        idx_start = clean_text.find(sent_clean, search_cursor)
        if idx_start == -1:
            idx_start = search_cursor
        idx_end = idx_start + len(sent_clean)
        search_cursor = idx_end

        # Context is preceding text up to idx_start
        context_prefix = clean_text[:idx_start].strip()
        s_cr = _compute_span_contextual_cr(context_prefix, sent_clean)

        s_score = _calculate_score_from_cr(
            s_cr, len(sent_clean.encode("utf-8")), low_cr, high_cr, formulaic_factor
        )
        span_scores.append(s_score)

        if s_score >= 60.0:
            risk = "HIGH"
            words_high += sent_words
        elif s_score >= 35.0:
            risk = "MODERATE"
            words_moderate += sent_words
        else:
            risk = "LOW"
            words_low += sent_words

        spans_data.append({
            "start": idx_start,
            "end": idx_end,
            "text": sent_clean,
            "risk": risk,
            "score": s_score,
            "compression_ratio": round(s_cr, 3),
        })

    # Overall document score: combination of full-doc compression and span average
    doc_cr_score = _calculate_score_from_cr(mean_ratio, raw_len, low_cr, high_cr, formulaic_factor)
    avg_span_score = sum(span_scores) / max(1, len(span_scores)) if span_scores else doc_cr_score
    composite_score = round(0.55 * doc_cr_score + 0.45 * avg_span_score, 1)
    composite_score = max(0.0, min(100.0, composite_score))

    if composite_score >= 60.0:
        overall_risk = "HIGH"
    elif composite_score >= 35.0:
        overall_risk = "MODERATE"
    else:
        overall_risk = "LOW"

    # Trilateral split calculation: strictly guaranteed to sum to 100.0%
    total_words = words_high + words_moderate + words_low
    if total_words == 0:
        ai_gen = 0.0
        ai_ref = 0.0
        human_w = 100.0
    else:
        ai_gen = round((words_high / total_words) * 100.0, 1)
        ai_ref = round((words_moderate / total_words) * 100.0, 1)
        # Force exact 100.0% sum
        human_w = round(100.0 - ai_gen - ai_ref, 1)
        if human_w < 0.0:
            human_w = 0.0
            ai_ref = round(100.0 - ai_gen, 1)

    words_count = len(clean_text.split())

    return {
        "composite_score": composite_score,
        "risk_level": overall_risk,
        "trilateral_split": {
            "ai_generated_pct": ai_gen,
            "ai_refined_pct": ai_ref,
            "human_written_pct": human_w,
        },
        "domain": domain_key,
        "compression_metrics": {
            "raw_bytes": raw_len,
            "zlib_bytes": len(zlib_comp),
            "lzma_bytes": len(lzma_comp),
            "zlib_ratio": zlib_ratio,
            "lzma_ratio": lzma_ratio,
            "mean_ratio": mean_ratio,
            "entropy_perplexity": entropy_perplexity,
        },
        "spans": spans_data,
        "word_count": words_count,
        "sentence_count": len(spans_data),
    }
