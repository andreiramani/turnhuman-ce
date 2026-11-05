"""TurnHuman Singleton NLP Engine (v3.0.0-PROD).

Provides lazy initialization for spaCy (en_core_web_sm) with graceful degradation
to heuristic regex modes when spaCy is unavailable or disabled.
Exposes universal POS tagging, dependency tree extraction, sentence span
segmentation, and passive voice detection.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Tuple

logger = logging.getLogger("TurnHuman.core.nlp_engine")

# Universal POS tag constants
POS_VERB = "VERB"
POS_NOUN = "NOUN"
POS_ADJ = "ADJ"
POS_ADV = "ADV"
POS_PRON = "PRON"
POS_DET = "DET"
POS_ADP = "ADP"
POS_CCONJ = "CCONJ"
POS_SCONJ = "SCONJ"
POS_AUX = "AUX"
POS_NUM = "NUM"
POS_PUNCT = "PUNCT"
POS_PROPN = "PROPN"
POS_X = "X"

# Regex heuristic fallback dictionaries
_COMMON_DET = {
    "the", "a", "an", "this", "that", "these", "those", "each", "every",
    "either", "neither", "some", "any", "no", "all", "both", "such",
    "sang", "si", "para", "sebuah", "suatu", "seekor", "seorang"
}
_COMMON_PRON = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "mine",
    "yours", "hers", "ours", "theirs", "myself", "yourself", "himself",
    "herself", "itself", "ourselves", "themselves", "who", "whom",
    "saya", "kami", "kita", "kamu", "anda", "dia", "mereka", "ia", "beliau"
}
_COMMON_ADP = {
    "in", "on", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "of", "off", "over", "under", "via",
    "across", "among", "per", "upon", "without", "within", "toward",
    "towards", "di", "ke", "dari", "pada", "dalam", "untuk", "dengan",
    "oleh", "tentang", "antara", "hingga", "sampai", "seperti"
}
_COMMON_CCONJ = {
    "and", "but", "or", "nor", "yet", "so", "dan", "atau", "tetapi",
    "namun", "melainkan", "sedangkan"
}
_COMMON_SCONJ = {
    "although", "because", "since", "unless", "while", "whereas", "if",
    "as", "whether", "though", "even", "despite", "karena", "sebab",
    "jika", "kalau", "apabila", "meskipun", "walaupun", "sementara"
}
_COMMON_AUX = {
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did",
    "will", "would", "shall", "should", "can", "could", "may",
    "might", "must", "adalah", "ialah", "merupakan", "dapat", "bisa", "harus"
}


class NLPEngine:
    """Singleton lazy-loading wrapper for spaCy with resilient regex fallback."""

    _instance: Optional[NLPEngine] = None

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self._model_name = model_name
        self._nlp: Optional[Any] = None
        self._initialized = False
        self._spacy_enabled = True

    @classmethod
    def get_instance(cls, model_name: str = "en_core_web_sm") -> NLPEngine:
        """Get or initialize singleton NLPEngine instance."""
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing and lifecycle management)."""
        cls._instance = None

    def set_spacy_enabled(self, enabled: bool) -> None:
        """Enable or disable spaCy dynamically (enables regex fallback testing)."""
        self._spacy_enabled = enabled

    def get_nlp(self) -> Optional[Any]:
        """Lazy load and return spaCy model, or None if unavailable/disabled."""
        if not self._initialized:
            self._initialized = True
            if self._spacy_enabled:
                try:
                    import spacy
                    self._nlp = spacy.load(self._model_name)
                    logger.info("spaCy model '%s' successfully loaded.", self._model_name)
                except Exception as exc:
                    logger.warning(
                        "spaCy model '%s' unavailable: %s. Operating in degraded regex mode.",
                        self._model_name,
                        exc,
                    )
                    self._nlp = None
            else:
                self._nlp = None

        if not self._spacy_enabled:
            return None
        return self._nlp

    def is_spacy_available(self) -> bool:
        """Check whether spaCy is successfully initialized and enabled."""
        return (self.get_nlp() is not None) and self._spacy_enabled

    def get_pos_tags(self, text: str) -> List[Tuple[str, str]]:
        """Extract Universal POS tags for tokens in text.

        When spaCy is available, returns actual UPOS tags (VERB, NOUN, ADJ, etc.).
        When spaCy is disabled/missing, uses robust regex morphological heuristics.
        """
        if not text or not text.strip():
            return []

        if self.is_spacy_available():
            nlp = self.get_nlp()
            if nlp is not None:
                doc = nlp(text)
                return [(token.text, token.pos_) for token in doc]

        # Heuristic regex-based POS tagger fallback
        tokens = re.findall(r"\w+(?:'\w+)?|[^\w\s]", text)
        results: List[Tuple[str, str]] = []

        for tok in tokens:
            lower = tok.lower()

            if re.match(r"^[^\w\s]+$", tok):
                results.append((tok, POS_PUNCT))
            elif re.match(r"^\d+(?:\.\d+)?$", tok):
                results.append((tok, POS_NUM))
            elif lower in _COMMON_DET:
                results.append((tok, POS_DET))
            elif lower in _COMMON_PRON:
                results.append((tok, POS_PRON))
            elif lower in _COMMON_AUX:
                results.append((tok, POS_AUX))
            elif lower in _COMMON_CCONJ:
                results.append((tok, POS_CCONJ))
            elif lower in _COMMON_SCONJ:
                results.append((tok, POS_SCONJ))
            elif lower in _COMMON_ADP:
                results.append((tok, POS_ADP))
            elif lower.endswith("ly"):
                results.append((tok, POS_ADV))
            elif any(
                lower.endswith(sfx)
                for sfx in ("able", "ible", "al", "ful", "ic", "ive", "ous", "less", "ish")
            ):
                results.append((tok, POS_ADJ))
            elif any(
                lower.endswith(sfx)
                for sfx in ("tion", "sion", "ment", "ness", "ity", "ance", "ence", "ist", "ism", "ship")
            ):
                results.append((tok, POS_NOUN))
            elif any(
                lower.endswith(sfx)
                for sfx in ("ing", "ed", "ize", "ise", "ify", "ate")
            ):
                results.append((tok, POS_VERB))
            elif tok[0].isupper() and not lower.startswith("the"):
                results.append((tok, POS_PROPN))
            else:
                results.append((tok, POS_NOUN))

        return results

    def get_dependency_tree(self, text: str) -> Optional[Any]:
        """Parse text into spaCy Doc with dependency relations, or None if fallback."""
        if not text or not text.strip():
            return None

        if self.is_spacy_available():
            nlp = self.get_nlp()
            if nlp is not None:
                return nlp(text)

        logger.debug("Dependency parse requested but spaCy is unavailable; returning None.")
        return None

    def get_sentence_spans(self, text: str) -> List[str]:
        """Segment input text into clean sentence strings."""
        if not text or not text.strip():
            return []

        if self.is_spacy_available():
            nlp = self.get_nlp()
            if nlp is not None:
                doc = nlp(text)
                return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        # Heuristic regex sentence splitter fallback
        raw_spans = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", text.strip())
        return [s.strip() for s in raw_spans if s.strip()]

    def is_passive_voice(self, span_or_text: Any) -> bool:
        """Detect passive voice syntax via dependency tree relations or regex heuristics.

        Supports spaCy Doc/Span directly or raw strings.
        Checks for nsubjpass, auxpass, or aux:pass dependency relations.
        """
        if span_or_text is None:
            return False

        # If already a spaCy Doc or Span
        if hasattr(span_or_text, "__iter__") and not isinstance(span_or_text, str):
            for token in span_or_text:
                dep = getattr(token, "dep_", "")
                if dep in ("nsubjpass", "auxpass", "aux:pass"):
                    return True
            return False

        text = str(span_or_text).strip()
        if not text:
            return False

        if self.is_spacy_available():
            nlp = self.get_nlp()
            if nlp is not None:
                doc = nlp(text)
                return any(
                    tok.dep_ in ("nsubjpass", "auxpass", "aux:pass")
                    for tok in doc
                )

        # Regex heuristic fallback
        # English: be-verb + participle (e.g. was analyzed, were conducted, is evaluated, has been shown)
        en_passive = bool(
            re.search(
                r"\b(?:is|am|are|was|were|be|been|being)\b\s+(?:\w+\s+)?\b\w+(?:ed|en|wn|t)\b",
                text,
                re.IGNORECASE,
            )
        )
        if en_passive:
            return True

        # Indonesian: prefix di- or ter- on verbs (e.g. dianalisis, dilakukan, terbukti)
        id_passive = bool(
            re.search(
                r"\b(?:di[a-z]{3,}|ter[a-z]{3,})\b",
                text,
                re.IGNORECASE,
            )
        )
        return id_passive


# Module-level convenience functions
def get_nlp(model_name: str = "en_core_web_sm") -> Optional[Any]:
    """Retrieve singleton spaCy model or None."""
    return NLPEngine.get_instance(model_name).get_nlp()


def is_spacy_available() -> bool:
    """Check if spaCy is loaded and operational."""
    return NLPEngine.get_instance().is_spacy_available()


def get_pos_tags(text: str) -> List[Tuple[str, str]]:
    """Get universal POS tags for text."""
    return NLPEngine.get_instance().get_pos_tags(text)


def get_dependency_tree(text: str) -> Optional[Any]:
    """Get dependency parse tree (Doc) for text."""
    return NLPEngine.get_instance().get_dependency_tree(text)


def get_sentence_spans(text: str) -> List[str]:
    """Segment text into sentence spans."""
    return NLPEngine.get_instance().get_sentence_spans(text)


def is_passive_voice(span_or_text: Any) -> bool:
    """Detect whether span or text is in passive voice."""
    return NLPEngine.get_instance().is_passive_voice(span_or_text)
