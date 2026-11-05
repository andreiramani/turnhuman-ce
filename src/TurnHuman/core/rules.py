"""TurnHuman Dynamic Rules Loader (v3.0.0-PROD).

Provides recursive, decoupled loading of academic JSON rule sets (en, id),
automatic filtering of '__prompt__' metadata blocks, i18n fallback mechanics,
and O(1) in-memory lookup for POS-tagged synonyms and transformations.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TurnHuman.core.rules")


def _strip_prompt(obj: Any) -> Any:
    """Recursively strip '__prompt__' metadata blocks from loaded JSON."""
    if isinstance(obj, dict):
        return {
            k: _strip_prompt(v)
            for k, v in obj.items()
            if k != "__prompt__"
        }
    if isinstance(obj, list):
        filtered: List[Any] = []
        for item in obj:
            if isinstance(item, dict) and "__prompt__" in item and len(item) == 1:
                continue
            filtered.append(_strip_prompt(item))
        return filtered
    return obj


class RuleLoader:
    """Singleton memoized loader for decoupled TurnHuman rules."""

    _instance: Optional[RuleLoader] = None

    def __init__(self, rules_dir: Optional[Path | str] = None) -> None:
        if rules_dir is None:
            env_dir = os.environ.get("TURNHUMAN_RULES_DIR")
            if env_dir:
                self.rules_dir = Path(env_dir).resolve()
            else:
                self.rules_dir = (
                    Path(__file__).resolve().parent.parent.parent.parent / "rules"
                )
        else:
            self.rules_dir = Path(rules_dir).resolve()

        self._cache: Dict[str, Any] = {}
        self._synonyms_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._phrases_index: Dict[str, Dict[str, str]] = {}
        self._taxonomy_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self._version_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls, rules_dir: Optional[Path | str] = None) -> RuleLoader:
        """Get or initialize singleton instance."""
        if cls._instance is None:
            cls._instance = cls(rules_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (primarily for testing)."""
        cls._instance = None

    def _load_json_file(self, file_path: Path) -> Any:
        """Load and parse JSON file, automatically stripping __prompt__."""
        if not file_path.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as fp:
            raw_data = json.load(fp)
        return _strip_prompt(raw_data)

    def load_lang_resource(self, lang: str, resource_name: str) -> Any:
        """Load a specific language resource with caching and English fallback."""
        cache_key = f"{lang}:{resource_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        target_file = self.rules_dir / lang / f"{resource_name}.json"
        if not target_file.exists():
            if lang != "en":
                fallback_file = self.rules_dir / "en" / f"{resource_name}.json"
                if fallback_file.exists():
                    logger.debug(
                        "Resource '%s' not found for '%s', falling back to 'en'",
                        resource_name,
                        lang,
                    )
                    data = self._load_json_file(fallback_file)
                    self._cache[cache_key] = data
                    return data
            raise FileNotFoundError(
                f"Resource '{resource_name}' not found for lang '{lang}'"
            )

        data = self._load_json_file(target_file)
        self._cache[cache_key] = data
        return data

    def _ensure_synonyms_index(self, lang: str) -> None:
        """Index synonyms for O(1) word lookup."""
        if lang in self._synonyms_index:
            return

        raw_synonyms = self.load_lang_resource(lang, "synonyms")
        index: Dict[str, Dict[str, Any]] = {}

        data_list = raw_synonyms.get("data", []) if isinstance(raw_synonyms, dict) else raw_synonyms
        if isinstance(data_list, list):
            for entry in data_list:
                if isinstance(entry, dict) and "word" in entry:
                    index[entry["word"].lower()] = entry

        self._synonyms_index[lang] = index

    def get_synonyms(
        self,
        word: str,
        pos: Optional[str] = None,
        domain: str = "all",
        lang: str = "en",
    ) -> List[Dict[str, Any]]:
        """Retrieve POS-tagged synonyms matching POS and domain restrictions."""
        self._ensure_synonyms_index(lang)
        target_word = word.strip().lower()
        entry = self._synonyms_index[lang].get(target_word)

        # Fallback to English if not found in target language
        if entry is None and lang != "en":
            self._ensure_synonyms_index("en")
            entry = self._synonyms_index["en"].get(target_word)

        if not entry:
            return []

        # Validate POS concordance
        if pos is not None and entry.get("pos") != pos.upper():
            return []

        # Validate domain restriction
        entry_domains = entry.get("domain", ["all"])
        if domain != "all" and "all" not in entry_domains and domain not in entry_domains:
            return []

        return list(entry.get("synonyms", []))

    def get_phrases(self, lang: str = "en") -> Dict[str, str]:
        """Retrieve multi-word AI cliche rewrites as a {pattern: replacement} dict."""
        if lang in self._phrases_index:
            return self._phrases_index[lang]

        raw_phrases = self.load_lang_resource(lang, "phrases")
        mapping: Dict[str, str] = {}
        if isinstance(raw_phrases, list):
            for item in raw_phrases:
                if isinstance(item, list) and len(item) == 2:
                    mapping[item[0]] = item[1]

        self._phrases_index[lang] = mapping
        return mapping

    def get_transitions(
        self, category: Optional[str] = None, lang: str = "en"
    ) -> List[str]:
        """Retrieve discourse transitions by PDTB category or flattened list."""
        raw_trans = self.load_lang_resource(lang, "transitions")
        if not isinstance(raw_trans, dict):
            return []

        if category is None:
            all_transitions: List[str] = []
            for cat_list in raw_trans.values():
                if isinstance(cat_list, list):
                    all_transitions.extend(cat_list)
            return all_transitions

        # Case-insensitive category lookup
        cat_lower = category.strip().lower()
        for cat_name, cat_list in raw_trans.items():
            if cat_name.lower() == cat_lower and isinstance(cat_list, list):
                return list(cat_list)

        # Graceful fallback to English if category not found in current language
        if lang != "en":
            return self.get_transitions(category, lang="en")
        return []

    def get_determiners(self, lang: str = "en") -> Dict[str, List[str]]:
        """Retrieve determiner rotation dictionary."""
        return dict(self.load_lang_resource(lang, "determiners"))

    def get_conjunctions(self, lang: str = "en") -> List[str]:
        """Retrieve subordinate / coordinating conjunctions list."""
        data = self.load_lang_resource(lang, "conjunctions")
        return list(data) if isinstance(data, list) else []

    def get_nominalizations(self, lang: str = "en") -> Dict[str, Any]:
        """Retrieve nominalization pairs (verbs_to_nouns, nouns_to_verbs)."""
        return dict(self.load_lang_resource(lang, "nominalizations"))

    def get_voice_patterns(self, lang: str = "en") -> Dict[str, Any]:
        """Retrieve active <-> passive voice transformations."""
        try:
            return dict(self.load_lang_resource(lang, "voice_patterns"))
        except FileNotFoundError:
            return {}

    def get_protected_terms(self, lang: str = "en") -> List[str]:
        """Retrieve protected entities and invariant symbols."""
        data = self.load_lang_resource(lang, "protected_terms")
        return list(data) if isinstance(data, list) else []

    def get_hedge_words(self, lang: str = "en") -> List[str]:
        """Retrieve epistemic hedge words."""
        try:
            data = self.load_lang_resource(lang, "hedge_words")
            return list(data) if isinstance(data, list) else []
        except FileNotFoundError:
            return []

    def get_appositives(self, lang: str = "en") -> Dict[str, List[str]]:
        """Retrieve appositives dictionary."""
        try:
            return dict(self.load_lang_resource(lang, "appositives"))
        except FileNotFoundError:
            return {}

    def get_discourse_markers(self, lang: str = "en") -> Dict[str, List[str]]:
        """Retrieve discourse markers dictionary."""
        try:
            return dict(self.load_lang_resource(lang, "discourse_markers"))
        except FileNotFoundError:
            return {}

    def get_academic_taxonomy(
        self, discipline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recursively load academic taxonomy across 5 disciplines."""
        if self._taxonomy_cache is None:
            taxonomy_dir = self.rules_dir / "academic" / "taxonomy"
            taxonomy: Dict[str, List[Dict[str, Any]]] = {}

            if taxonomy_dir.exists():
                for disc_dir in sorted(taxonomy_dir.iterdir()):
                    if disc_dir.is_dir():
                        disc_key = disc_dir.name
                        taxonomy[disc_key] = []
                        for sub_file in sorted(disc_dir.glob("*.json")):
                            sub_data = self._load_json_file(sub_file)
                            if isinstance(sub_data, list):
                                taxonomy[disc_key].extend(sub_data)
                            elif isinstance(sub_data, dict):
                                taxonomy[disc_key].append(sub_data)

            self._taxonomy_cache = taxonomy

        if discipline is None:
            return self._taxonomy_cache

        disc_normalized = discipline.strip().lower()
        return {
            disc_normalized: self._taxonomy_cache.get(disc_normalized, [])
        }

    def get_rules_version(self) -> Dict[str, Any]:
        """Retrieve versioning and changelog metadata from rules/VERSION.json."""
        if self._version_cache is None:
            ver_file = self.rules_dir / "VERSION.json"
            self._version_cache = self._load_json_file(ver_file)
        return dict(self._version_cache)


# Convenience Functional Interface
def get_synonyms(
    word: str,
    pos: Optional[str] = None,
    domain: str = "all",
    lang: str = "en",
) -> List[Dict[str, Any]]:
    return RuleLoader.get_instance().get_synonyms(word, pos, domain, lang)


def get_phrases(lang: str = "en") -> Dict[str, str]:
    return RuleLoader.get_instance().get_phrases(lang)


def get_transitions(
    category: Optional[str] = None, lang: str = "en"
) -> List[str]:
    return RuleLoader.get_instance().get_transitions(category, lang)


def get_determiners(lang: str = "en") -> Dict[str, List[str]]:
    return RuleLoader.get_instance().get_determiners(lang)


def get_conjunctions(lang: str = "en") -> List[str]:
    return RuleLoader.get_instance().get_conjunctions(lang)


def get_nominalizations(lang: str = "en") -> Dict[str, Any]:
    return RuleLoader.get_instance().get_nominalizations(lang)


def get_voice_patterns(lang: str = "en") -> Dict[str, Any]:
    return RuleLoader.get_instance().get_voice_patterns(lang)


def get_protected_terms(lang: str = "en") -> List[str]:
    return RuleLoader.get_instance().get_protected_terms(lang)


def get_academic_taxonomy(discipline: Optional[str] = None) -> Dict[str, Any]:
    return RuleLoader.get_instance().get_academic_taxonomy(discipline)


def get_rules_version() -> Dict[str, Any]:
    return RuleLoader.get_instance().get_rules_version()
