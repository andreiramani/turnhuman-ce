"""Syntactic & Structural Transformation Stages for TextModifier (v3.0.1-MODULAR)."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from TurnHuman.core.nlp_engine import (
    get_sentence_spans,
    is_passive_voice,
    is_spacy_available,
)
from TurnHuman.core.rules import RuleLoader


class ModifierSyntacticMixin:
    """Mixin providing syntactic stages (4, 6, 8, 9, 10, 11, 12, 14, 15)."""

    # =========================================================================
    def _reorder_clauses(self, text: str) -> str:
        """Stage 4: Invert opening subordinate clauses using conjunctions and punctuation."""
        conjunctions = set(self.rule_loader.get_conjunctions(lang=self.lang))
        if not conjunctions:
            return text

        sentences = get_sentence_spans(text)
        if not sentences:
            return text

        modified_sentences: List[str] = []

        for sent in sentences:
            # Check if sentence starts with a subordinate conjunction
            words = sent.split()
            if len(words) < 6:
                modified_sentences.append(sent)
                continue

            # Check opening 1-2 words against conjunctions
            matched_conj = None
            for conj in conjunctions:
                conj_words = conj.split()
                if len(words) >= len(conj_words):
                    opening = " ".join(words[: len(conj_words)]).lower()
                    if opening == conj.lower():
                        matched_conj = conj
                        break

            if not matched_conj:
                modified_sentences.append(sent)
                continue

            # Find comma separating dependent clause and main clause
            comma_idx = sent.find(",")
            if comma_idx == -1 or comma_idx >= len(sent) - 10:
                modified_sentences.append(sent)
                continue

            clause_dep = sent[:comma_idx].strip()
            clause_main = sent[comma_idx + 1:].strip()

            # Ending punctuation
            punct = ""
            if clause_main and clause_main[-1] in ".!?":
                punct = clause_main[-1]
                clause_main = clause_main[:-1].strip()

            # Reconstruct: [Main clause], [dep clause].
            main_reordered = self._preserve_case("Main", clause_main)
            dep_words = clause_dep.split()
            conj_len = len(matched_conj.split())

            conj_lower = matched_conj.lower()
            rest_of_dep = " ".join(dep_words[conj_len:])

            new_sent = f"{main_reordered}, {conj_lower} {rest_of_dep}{punct}"

            # Strict word count check
            if len(new_sent.split()) == len(sent.split()):
                modified_sentences.append(new_sent)
            else:
                modified_sentences.append(sent)

        return " ".join(modified_sentences)

    # =========================================================================
    # STAGE 5: Swap Determiners

    # =========================================================================
    def _split_compound_sentences(self, text: str) -> str:
        """Stage 6: Split long compound sentences with coordinating conjunctions."""
        sentences = get_sentence_spans(text)
        if not sentences:
            return text

        # 1-to-1 replacements that preserve word count exactly
        coordinating_splits = {
            ", and ": ". Furthermore, ",
            ", but ": ". However, ",
            ", so ": ". Consequently, ",
            ", yet ": ". Nonetheless, ",
            ", while ": ". Meanwhile, ",
            ", dan ": ". Selanjutnya, ",
            ", tetapi ": ". Namun, ",
            ", namun ": ". Akan tetapi, ",
        }

        modified_sentences: List[str] = []

        for sent in sentences:
            words = sent.split()
            if len(words) <= 25:
                modified_sentences.append(sent)
                continue

            split_applied = False
            for pattern, replacement in coordinating_splits.items():
                if pattern in sent:
                    # Apply single split
                    new_sent = sent.replace(pattern, replacement, 1)
                    if len(new_sent.split()) == len(words):
                        modified_sentences.append(new_sent)
                        split_applied = True
                        break

            if not split_applied:
                modified_sentences.append(sent)

        return " ".join(modified_sentences)

    # =========================================================================

    # STAGE 8: Break N-gram Chains (5-gram Chains)
    # =========================================================================
    def _break_ngram_chains(self, text: str, original_text: Optional[str] = None) -> str:
        """Stage 8: Identify and break identical 5-gram chains against original text."""
        if not original_text:
            return text

        orig_words = original_text.split()
        if len(orig_words) < 5:
            return text

        orig_5grams = set()
        for idx in range(len(orig_words) - 4):
            gram = " ".join(w.lower() for w in orig_words[idx : idx + 5])
            orig_5grams.add(gram)

        curr_words = text.split()
        if len(curr_words) < 5:
            return text

        modified_words = list(curr_words)
        determiners_dict = self.rule_loader.get_determiners(lang=self.lang)
        i = 0
        while i <= len(modified_words) - 5:
            gram = " ".join(w.lower() for w in modified_words[i : i + 5])
            if gram in orig_5grams:
                # Try candidate positions in the 5-gram to find a replaceable word
                replaced = False
                for offset in [2, 3, 1, 4, 0]:
                    target_idx = i + offset
                    if target_idx >= len(modified_words):
                        continue
                    target_word = modified_words[target_idx]
                    if "\x00" in target_word:
                        continue

                    clean_target = re.sub(r"[^\w]", "", target_word).lower()
                    if not clean_target or clean_target in self.protected_terms:
                        continue

                    # 1. Try synonym
                    syns = self.rule_loader.get_synonyms(word=clean_target, lang=self.lang)
                    single_word_syns = [
                        s["term"]
                        for s in syns
                        if isinstance(s, dict)
                        and "term" in s
                        and len(s["term"].split()) == 1
                        and s["term"].lower() != clean_target
                    ]
                    if single_word_syns:
                        chosen_syn = self._rng.choice(single_word_syns)
                        rep = self._preserve_case(clean_target, chosen_syn)
                        if target_word.endswith(","):
                            rep += ","
                        elif target_word.endswith("."):
                            rep += "."
                        modified_words[target_idx] = rep
                        replaced = True
                        break

                    # 2. Try determiner rotation
                    if clean_target in determiners_dict:
                        opts = [
                            o
                            for o in determiners_dict[clean_target]
                            if len(o.split()) == 1 and o.lower() != clean_target
                        ]
                        if opts:
                            chosen_det = self._rng.choice(opts)
                            rep = self._preserve_case(clean_target, chosen_det)
                            if target_word.endswith(","):
                                rep += ","
                            elif target_word.endswith("."):
                                rep += "."
                            modified_words[target_idx] = rep
                            replaced = True
                            break

                i += 5 if replaced else 1
            else:
                i += 1

        return " ".join(modified_words)

    # =========================================================================
    # STAGE 9: Active <-> Passive Voice Transformation
    # =========================================================================
    def _transform_voice(self, text: str) -> str:
        """Stage 9: Active <-> Passive voice transformation."""
        sentences = get_sentence_spans(text)
        if not sentences:
            return text

        modified_sentences: List[str] = []

        for sent in sentences:
            if "\x00" in sent:
                modified_sentences.append(sent)
                continue

            words = sent.split()
            transformed = sent

            # Check if passive voice
            if is_passive_voice(sent):
                # Attempt passive -> active conversion
                # Pattern: "The data were analyzed by the researchers." -> "The researchers analyzed the data."
                m = re.match(
                    r"^(The\s+[\w\s]+?)\s+(?:was|were|is|are)\s+([\w]+(?:ed|en))\s+by\s+(the\s+[\w\s]+?)(\.|\?|!)$",
                    sent.strip(),
                    re.IGNORECASE,
                )
                if m:
                    subj, verb, agent, punct = m.group(1), m.group(2), m.group(3), m.group(4)
                    agent_cap = self._preserve_case("The", agent)
                    subj_lower = subj.lower()
                    transformed = f"{agent_cap} {verb} {subj_lower}{punct}"
            else:
                # Attempt active -> passive conversion
                # Pattern: "The researchers analyzed the results." -> "The results were analyzed by the researchers."
                m = re.match(
                    r"^(The\s+[\w\s]+?)\s+([\w]+(?:ed))\s+(the\s+[\w\s]+?)(\.|\?|!)$",
                    sent.strip(),
                    re.IGNORECASE,
                )
                if m:
                    agent, verb, obj, punct = m.group(1), m.group(2), m.group(3), m.group(4)
                    obj_cap = self._preserve_case("The", obj)
                    agent_lower = agent.lower()
                    transformed = f"{obj_cap} were {verb} by {agent_lower}{punct}"

            # Indonesian voice patterns support
            if self.lang == "id":
                voice_data = self.rule_loader.get_voice_patterns(lang="id")
                a2p = voice_data.get("active_to_passive", {})
                for act_verb, pas_verb in a2p.items():
                    if act_verb in sent:
                        candidate = sent.replace(act_verb, pas_verb, 1)
                        if self.mode != "zero_expansion" or len(candidate.split()) == len(words):
                            transformed = candidate
                            break

            # In ZE mode, only apply if word count delta == 0
            if self.mode == "zero_expansion" and len(transformed.split()) != len(words):
                modified_sentences.append(sent)
            else:
                modified_sentences.append(transformed)

        return " ".join(modified_sentences)

    # =========================================================================
    # STAGE 10: Fuse Adjacent Short Sentences [ZE-incompatible, auto-disabled in ZE]
    # =========================================================================
    def _fuse_sentences(self, text: str) -> str:
        """Stage 10: Merge adjacent short sentences (< 10 words) with conjunctions."""
        sentences = get_sentence_spans(text)
        if len(sentences) < 2:
            return text

        result: List[str] = []
        i = 0

        while i < len(sentences):
            sent1 = sentences[i]
            if i + 1 < len(sentences):
                sent2 = sentences[i + 1]
                w1 = sent1.split()
                w2 = sent2.split()

                if len(w1) < 10 and len(w2) < 10 and "\x00" not in sent1 and "\x00" not in sent2:
                    clean1 = sent1.rstrip(".!?")
                    clean2 = sent2[0].lower() + sent2[1:]
                    connector = "while" if self.lang == "en" else "sedangkan"
                    fused = f"{clean1}, {connector} {clean2}"
                    result.append(fused)
                    i += 2
                    continue

            result.append(sent1)
            i += 1

        return " ".join(result)

    # =========================================================================
    # STAGE 11: Inject PDTB 2.0 Transitions [ZE-incompatible, auto-disabled in ZE]
    # =========================================================================
    def _inject_transitions(self, text: str) -> str:
        """Stage 11: Inject PDTB 2.0 transitions with FIFO anti-repetition memory."""
        categories = ["Addition", "Contrast", "Cause_Effect"]
        category = self._rng.choice(categories)
        candidates = self.rule_loader.get_transitions(category=category, lang=self.lang)
        if not candidates:
            return text

        # Filter out recently used transitions from FIFO memory
        available = [t for t in candidates if t not in self._transition_fifo]
        if not available:
            available = candidates

        chosen = self._rng.choice(available)
        self._transition_fifo.append(chosen)
        if len(self._transition_fifo) > 5:
            self._transition_fifo.pop(0)

        # Inject at paragraph opening if not already starting with transition
        if text.startswith("\x00"):
            return text

        return f"{chosen}, {text[0].lower() + text[1:]}"

    # =========================================================================
    # STAGE 12: Reorder Within Clause (Prepositional / Adverbial Phrases)
    # =========================================================================
    def _reorder_within_clause(self, text: str) -> str:
        """Stage 12: Reorder adverbial modifiers inside clauses in-place."""
        tokens = text.split()
        if len(tokens) < 4:
            return text

        # Swap adverb placed at end of clause before the verb:
        # e.g. "performs efficiently" -> "efficiently performs"
        modified_tokens = list(tokens)
        for i in range(len(modified_tokens) - 1):
            w1 = modified_tokens[i].lower()
            w2 = modified_tokens[i + 1].lower()

            if w1 not in self.protected_terms and w2.endswith("ly") and w2 not in self.protected_terms:
                if "\x00" not in modified_tokens[i] and "\x00" not in modified_tokens[i + 1]:
                    # Swap positions
                    casing1 = modified_tokens[i]
                    casing2 = modified_tokens[i + 1]
                    modified_tokens[i] = casing2
                    modified_tokens[i + 1] = casing1
                    break

        return " ".join(modified_tokens)

    # =========================================================================
    # STAGE 13: Nominalizations [ZE-incompatible, auto-disabled in ZE]

    # =========================================================================
    def _inject_appositives(self, text: str) -> str:
        """Stage 14: Insert explanatory appositives (max 1x per unique term)."""
        appositives_map = self.rule_loader.get_appositives(lang=self.lang)
        if not appositives_map:
            return text

        modified = text
        for term, appositive in appositives_map.items():
            if term in self._appositives_used:
                continue

            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, modified, re.IGNORECASE):
                # Inject parenthetical appositive directly after the term
                replacement = f"{term}{appositive}"
                modified = re.sub(
                    pattern,
                    replacement,
                    modified,
                    count=1,
                    flags=re.IGNORECASE,
                )
                self._appositives_used.add(term)
                break

        return modified

    # =========================================================================
    # STAGE 15: Rotate Discourse Markers
    # =========================================================================
    def _rotate_discourse_markers(self, text: str) -> str:
        """Stage 15: Rotate paragraph discourse markers."""
        markers_dict = self.rule_loader.get_discourse_markers(lang=self.lang)
        if not markers_dict:
            return text

        is_ze = self.mode == "zero_expansion"
        modified = text

        for category, markers in markers_dict.items():
            for marker in markers:
                if modified.startswith(marker):
                    # Pick an alternative from same category
                    candidates = [m for m in markers if m != marker]
                    if is_ze:
                        candidates = [m for m in candidates if len(m.split()) == len(marker.split())]

                    if candidates:
                        replacement = self._rng.choice(candidates)
                        modified = replacement + modified[len(marker):]
                        return modified

        return modified

    # =========================================================================
