"""TurnHuman 16-Stage Deterministic Modifier Pipeline & Facade Runner (v3.0.1-MODULAR)."""

from __future__ import annotations

import datetime
import logging
import random
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from TurnHuman.core.modifier_lexical import ModifierLexicalMixin
from TurnHuman.core.modifier_syntactic import ModifierSyntacticMixin
from TurnHuman.core.nlp_engine import NLPEngine, is_spacy_available
from TurnHuman.core.rules import RuleLoader
from TurnHuman.core.word_budget import (
    ZERO_WIDTH_TRACKING_CHARS,
    WordBudgetController,
    strip_zero_width_chars,
)

logger = logging.getLogger("TurnHuman.core.modifier")

__all__ = [
    "ZERO_WIDTH_TRACKING_CHARS",
    "TextModifier",
    "WordBudgetController",
    "strip_zero_width_chars",
    "humanize_text",
]


class TextModifier(ModifierLexicalMixin, ModifierSyntacticMixin):
    """Orchestrates the 16-stage deterministic programmatic transformation pipeline."""

    """The 16-Stage Deterministic Transformation Pipeline."""

    def __init__(
        self,
        mode: str = "full",
        synonym_probability: float = 0.8,
        domain: str = "all",
        lang: str = "en",
        seed: Optional[int] = None,
        custom_protected_terms: Optional[List[str]] = None,
        rules_dir: Optional[str] = None,
    ) -> None:
        self.mode = mode.strip().lower()
        self.synonym_probability = max(0.5, min(1.0, synonym_probability))
        self.domain = domain
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)

        self.wbc = WordBudgetController(mode=self.mode)
        self.rule_loader = RuleLoader.get_instance(rules_dir)
        self.nlp = NLPEngine.get_instance()

        # Build protected terms set (case-insensitive for fast lookup)
        base_protected = self.rule_loader.get_protected_terms(lang=self.lang)
        all_protected = list(base_protected)
        if custom_protected_terms:
            all_protected.extend(custom_protected_terms)
        self.protected_terms_raw = all_protected
        self.protected_terms = {t.strip().lower() for t in all_protected if t.strip()}

        # Runtime state per execution
        self._latex_masks: Dict[str, str] = {}
        self._appositives_used: Set[str] = set()
        self._transition_fifo: List[str] = []
        self._stage_telemetry: Dict[str, Dict[str, Any]] = {}
        self._warnings: List[str] = []


    def _execute_stage(
        self,
        stage_num: int,
        stage_name: str,
        stage_func: Callable[[str], str],
        text: str,
    ) -> str:
        """Execute a single pipeline stage with strict fault isolation and WBC telemetry."""
        if not self.wbc.is_stage_enabled(stage_num):
            self.wbc.record_delta(stage_name, len(text.split()), len(text.split()))
            self._stage_telemetry[stage_name] = {
                "status": "SKIPPED",
                "delta": 0,
                "time_ms": 0.0,
                "reason": "Disabled by WordBudgetController (ZE Mode)",
            }
            return text

        t0 = time.perf_counter()
        words_before = len(text.split())

        try:
            result = stage_func(text)
            words_after = len(result.split())

            # Strict ZE invariant safeguard for active stages:
            if self.mode == "zero_expansion" and words_after != words_before:
                logger.warning(
                    "Stage %s altered word count in zero_expansion mode (%d -> %d). Reverting stage.",
                    stage_name,
                    words_before,
                    words_after,
                )
                self.wbc.record_delta(stage_name, words_before, words_before)
                self._warnings.append(
                    f"Stage {stage_name} altered word count ({words_before} -> {words_after}) and was reverted."
                )
                self._stage_telemetry[stage_name] = {
                    "status": "REVERTED_ZE",
                    "delta": 0,
                    "time_ms": round((time.perf_counter() - t0) * 1000, 3),
                }
                return text

            self.wbc.record_delta(stage_name, words_before, words_after)
            self._stage_telemetry[stage_name] = {
                "status": "SUCCESS",
                "delta": words_after - words_before,
                "time_ms": round((time.perf_counter() - t0) * 1000, 3),
            }
            return result

        except Exception as exc:
            logger.warning("Stage %s failed with error: %s. Gracefully skipping.", stage_name, exc)
            self._warnings.append(f"Stage {stage_name} skipped due to error: {exc}")
            self.wbc.record_delta(stage_name, words_before, words_before)
            self._stage_telemetry[stage_name] = {
                "status": "SKIPPED",
                "delta": 0,
                "time_ms": round((time.perf_counter() - t0) * 1000, 3),
                "error": str(exc),
            }
            return text

    # =========================================================================

    # Main Pipeline Execution
    # =========================================================================
    def transform(self, text: str, original_text: Optional[str] = None) -> str:
        """Execute the full 16-stage transformation pipeline."""
        # Sanitize steganographic zero-width tracking characters at entry
        text = strip_zero_width_chars(text)
        if not text or not text.strip():
            return text

        t_start = time.perf_counter()
        initial_words = len(text.split())
        current_text = text
        orig_text = strip_zero_width_chars(original_text) if original_text is not None else text

        # 16-Stage sequential execution
        current_text = self._execute_stage(1, "protect_latex", self._protect_latex, current_text)
        current_text = self._execute_stage(2, "apply_phrase_rewrites", self._apply_phrase_rewrites, current_text)
        current_text = self._execute_stage(3, "apply_synonyms", self._apply_synonyms, current_text)
        current_text = self._execute_stage(4, "reorder_clauses", self._reorder_clauses, current_text)
        current_text = self._execute_stage(5, "swap_determiners", self._swap_determiners, current_text)
        current_text = self._execute_stage(6, "split_compound_sentences", self._split_compound_sentences, current_text)
        current_text = self._execute_stage(7, "insert_hedge_words", self._insert_hedge_words, current_text)
        current_text = self._execute_stage(
            8, "break_ngram_chains", lambda t: self._break_ngram_chains(t, orig_text), current_text
        )
        current_text = self._execute_stage(9, "transform_voice", self._transform_voice, current_text)
        current_text = self._execute_stage(10, "fuse_sentences", self._fuse_sentences, current_text)
        current_text = self._execute_stage(11, "inject_transitions", self._inject_transitions, current_text)
        current_text = self._execute_stage(12, "reorder_within_clause", self._reorder_within_clause, current_text)
        current_text = self._execute_stage(13, "nominalize", self._nominalize, current_text)
        current_text = self._execute_stage(14, "inject_appositives", self._inject_appositives, current_text)
        current_text = self._execute_stage(15, "rotate_discourse_markers", self._rotate_discourse_markers, current_text)
        current_text = self._execute_stage(16, "restore_latex", self._restore_latex, current_text)

        total_time_ms = round((time.perf_counter() - t_start) * 1000, 3)
        final_words = len(current_text.split())

        self._telemetry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "language": self.lang,
            "mode": self.mode,
            "stages": dict(self._stage_telemetry),
            "total_delta": final_words - initial_words,
            "total_time_ms": total_time_ms,
            "spacy_available": is_spacy_available(),
            "warnings": list(self._warnings),
            "word_count_initial": initial_words,
            "word_count_final": final_words,
        }

        current_text = strip_zero_width_chars(current_text)
        return current_text

    def get_telemetry(self) -> Dict[str, Any]:
        """Retrieve full in-memory execution telemetry."""
        return dict(self._telemetry)


def humanize_text(
    text: str,
    mode: str = "full",
    synonym_probability: float = 0.8,
    domain: str = "all",
    lang: str = "en",
    seed: Optional[int] = None,
    custom_protected_terms: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Convenience functional wrapper for TextModifier."""
    modifier = TextModifier(
        mode=mode,
        synonym_probability=synonym_probability,
        domain=domain,
        lang=lang,
        seed=seed,
        custom_protected_terms=custom_protected_terms,
    )
    result = modifier.transform(text)
    return result, modifier.get_telemetry()
