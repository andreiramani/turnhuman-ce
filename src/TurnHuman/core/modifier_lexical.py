"""Lexical Transformation Stages for TextModifier (v3.0.1-MODULAR)."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from TurnHuman.core.nlp_engine import get_pos_tags
from TurnHuman.core.rules import RuleLoader


class ModifierLexicalMixin:
    """Mixin providing lexical stages (1, 2, 3, 5, 7, 13, 16)."""

    def _preserve_case(self, source: str, target: str) -> str:
        """Preserve the capitalization casing of source onto target."""
        if not source or not target:
            return target
        if source.isupper():
            return target.upper()
        if source[0].isupper():
            return target[0].upper() + target[1:]
        return target.lower()


    # STAGE 1: Mask LaTeX Formulas, Environments & Citations
    # =========================================================================
    def _protect_latex(self, text: str) -> str:
        """Stage 1: Mask LaTeX math, environments, and citations into placeholder tokens."""
        self._latex_masks.clear()
        mask_counter = 0

        patterns = [
            # 1. LaTeX Environments: \begin{env}...\end{env}
            re.compile(r"\\begin\{([a-zA-Z*]+)\}.*?\\end\{\1\}", re.DOTALL),
            # 2. Display math: $$...$$ or \[...\]
            re.compile(r"\$\$.*?\$\$", re.DOTALL),
            re.compile(r"\\\[.*?\\\]", re.DOTALL),
            # 3. Inline math: $...$ or \(...\)
            re.compile(r"(?<!\\)\$(?!\$)[^\$\n\x00]+(?<!\\)\$", re.DOTALL),
            re.compile(r"\\\(.*?\\\)", re.DOTALL),
            # 4. Citations: \cite{...}, \citep{...}, etc.
            re.compile(r"\\cite[a-zA-Z*]*\{[^}]*\}"),
        ]

        def _replacer(match: re.Match) -> str:
            nonlocal mask_counter
            matched_str = match.group(0)
            k_words = len(matched_str.split())

            # Generate k_words mask tokens to preserve exact word count in intermediate stages
            primary_token = f"\x00MASK_{mask_counter}\x00"
            if k_words <= 1:
                token_str = primary_token
            else:
                sub_tokens = [f"\x00MASK_{mask_counter}_w{i}\x00" for i in range(1, k_words)]
                token_str = f"{primary_token} " + " ".join(sub_tokens)

            self._latex_masks[token_str] = matched_str
            mask_counter += 1
            return token_str

        modified = text
        for pat in patterns:
            modified = pat.sub(_replacer, modified)

        return modified

    # =========================================================================
    # STAGE 2: Multi-Word AI Cliche Rewrites
    # =========================================================================
    def _apply_phrase_rewrites(self, text: str) -> str:
        """Stage 2: Replace multi-word AI cliches via RuleLoader.get_phrases."""
        phrases_map = self.rule_loader.get_phrases(lang=self.lang)
        if not phrases_map:
            return text

        # Sort patterns by length descending for greedy matching
        sorted_patterns = sorted(phrases_map.keys(), key=lambda p: len(p), reverse=True)

        modified = text
        for pat_str in sorted_patterns:
            replacement = phrases_map[pat_str]
            is_ze = self.mode == "zero_expansion"

            try:
                # Compile regex if it includes boundaries or use word boundary
                if "\\b" in pat_str:
                    compiled = re.compile(pat_str, re.IGNORECASE)
                else:
                    compiled = re.compile(r"\b" + re.escape(pat_str) + r"\b", re.IGNORECASE)

                def _replace_phrase(match: re.Match) -> str:
                    orig = match.group(0)
                    # Check protected terms
                    if orig.lower() in self.protected_terms:
                        return orig
                    if "\x00" in orig:
                        return orig

                    # In zero_expansion mode, only apply if word count matches exactly
                    if is_ze and len(orig.split()) != len(replacement.split()):
                        return orig

                    return self._preserve_case(orig, replacement)

                modified = compiled.sub(_replace_phrase, modified)

            except Exception:
                continue

        return modified

    # =========================================================================

    # STAGE 3: POS-Aware 1:1 Synonym Substitution
    # =========================================================================
    def _apply_synonyms(self, text: str) -> str:
        """Stage 3: 1:1 synonym substitution matching POS tag and domain."""
        if not text.strip():
            return text

        pos_tags = get_pos_tags(text)
        if not pos_tags:
            return text

        # Tokenize preserving spaces & punctuation
        tokens = re.split(r"(\s+|[^\w\s\x00])", text)
        result_tokens: List[str] = []

        # Map word tokens to their POS tag
        word_pos_map: Dict[str, str] = {}
        for tok, ptag in pos_tags:
            word_pos_map[tok.lower()] = ptag

        for t in tokens:
            if not t or t.isspace() or "\x00" in t:
                result_tokens.append(t)
                continue

            lower_word = t.lower()
            if not re.match(r"^[a-zA-Z]+$", t):
                result_tokens.append(t)
                continue

            # Check protected terms
            if lower_word in self.protected_terms:
                result_tokens.append(t)
                continue

            # Check probability threshold
            if self._rng.random() > self.synonym_probability:
                result_tokens.append(t)
                continue

            ptag = word_pos_map.get(lower_word) if self.lang == "en" else None
            syn_candidates = self.rule_loader.get_synonyms(
                word=lower_word,
                pos=ptag,
                domain=self.domain,
                lang=self.lang,
            )

            # Strict 1:1 single-word filter
            valid_syns = [
                s for s in syn_candidates
                if isinstance(s, dict)
                and "term" in s
                and len(s["term"].split()) == 1
                and s["term"].lower() != lower_word
            ]

            if not valid_syns:
                result_tokens.append(t)
                continue

            # Pick highest-weight candidate or weighted choice
            best_syn = max(valid_syns, key=lambda x: x.get("weight", 0.0))
            chosen_term = best_syn["term"]
            result_tokens.append(self._preserve_case(t, chosen_term))

        return "".join(result_tokens)

    # =========================================================================

    # =========================================================================
    def _swap_determiners(self, text: str) -> str:
        """Stage 5: Rotate demonstratives and articles (the <-> this, these, such)."""
        determiners_dict = self.rule_loader.get_determiners(lang=self.lang)
        if not determiners_dict:
            return text

        tokens = re.split(r"(\s+|[^\w\s\x00])", text)
        result_tokens: List[str] = []
        is_ze = self.mode == "zero_expansion"

        for t in tokens:
            if not t or t.isspace() or "\x00" in t:
                result_tokens.append(t)
                continue

            lower_word = t.lower()
            if lower_word in determiners_dict and lower_word not in self.protected_terms:
                options = determiners_dict[lower_word]
                if is_ze:
                    options = [opt for opt in options if len(opt.split()) == 1]

                if options:
                    chosen = self._rng.choice(options)
                    result_tokens.append(self._preserve_case(t, chosen))
                    continue

            result_tokens.append(t)

        return "".join(result_tokens)

    # =========================================================================
    # STAGE 6: Split Long Compound Sentences (> 25 words)

    # STAGE 7: Insert Hedge Words [ZE-incompatible, auto-disabled in ZE]
    # =========================================================================
    def _insert_hedge_words(self, text: str) -> str:
        """Stage 7: Injects scientific qualifiers post-comma (e.g. ', arguably,')."""
        hedge_words = self.rule_loader.get_hedge_words(lang=self.lang)
        if not hedge_words:
            return text

        # Inject at most 2 hedge words per text to avoid overuse
        max_injections = 2
        injections = 0

        def _hedge_sub(match: re.Match) -> str:
            nonlocal injections
            if injections >= max_injections:
                return match.group(0)

            chosen_hedge = self._rng.choice(hedge_words)
            injections += 1
            return f", {chosen_hedge},"

        # Target natural commas not already followed by hedge words
        return re.sub(r",\s+(?=[a-zA-Z]{4,})", _hedge_sub, text, count=max_injections)

    # =========================================================================

    # =========================================================================
    def _nominalize(self, text: str) -> str:
        """Stage 13: Verbs <-> abstract nouns bidirectional transformation."""
        nominal_dict = self.rule_loader.get_nominalizations(lang=self.lang)
        v2n = nominal_dict.get("verbs_to_nouns", {})
        if not v2n:
            return text

        modified = text
        for verb, noun_phrase in v2n.items():
            pattern = r"\b" + re.escape(verb) + r"\b"
            if re.search(pattern, modified, re.IGNORECASE):
                modified = re.sub(
                    pattern,
                    lambda m: self._preserve_case(m.group(0), noun_phrase),
                    modified,
                    count=1,
                )
                break

        return modified

    # =========================================================================
    # STAGE 14: Inject Appositives [ZE-incompatible, auto-disabled in ZE]

    # STAGE 16: Restore LaTeX & Citations
    # =========================================================================
    def _restore_latex(self, text: str) -> str:
        """Stage 16: Accurately restore all masked LaTeX & citation tokens."""
        if not self._latex_masks:
            return text

        restored = text
        for mask_str in sorted(self._latex_masks.keys(), key=len, reverse=True):
            restored = restored.replace(mask_str, self._latex_masks[mask_str])

        return restored

    # =========================================================================
