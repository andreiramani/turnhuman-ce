"""Developer Persona Vocabulary & Modulation Rules (v3.0.1-MODULAR)."""

from __future__ import annotations

import re
from typing import List, Tuple

# =============================================================================
# Developer Persona Vocabulary Rules
# =============================================================================

PERSONA_VOCABULARY: dict[str, List[Tuple[str, str]]] = {
    "beginner": [
        (r"\bcompute\s+factorial\b", "calculate the factorial"),
        (r"\bcomputations\b", "calculations"),
        (r"\bcompute\b", "calculate"),
        (r"\bensure\s+input\s+is\b", "make sure input is"),
        (r"\bensure\b", "make sure"),
        (r"\bvalidate\b", "check"),
        (r"\bvalidates\b", "checks"),
        (r"\biterate\s+through\b", "loop through"),
        (r"\biterate\b", "loop"),
        (r"\baccumulate\s+product\b", "add up product"),
        (r"\baccumulate\b", "add up"),
        (r"\bguard\s+against\b", "watch out for"),
        (r"\bguard\b", "check"),
        (r"\barithmetic\s+mean\b", "average (mean)"),
        (r"\bmean\b", "average"),
        (r"\bvariance\b", "spread (variance)"),
        (r"\bpopulation\s+variance\b", "variance spread"),
        (r"\bbase\s+case\b", "starting case"),
        (r"\binstantiate\b", "create"),
        (r"\binitialize\b", "set up"),
        (r"\binitializes\b", "sets up"),
        (r"\bterminate\b", "stop"),
        (r"\bobtain\b", "get"),
        (r"\bretrieve\b", "get"),
        (r"\bpersist\b", "save"),
        (r"\bparameters\b", "inputs"),
        (r"\bparameter\b", "input"),
        (r"\bexecute\b", "run"),
        (r"\bexecutes\b", "runs"),
        (r"\bexecution\b", "running"),
        (r"\baggregated\b", "collected"),
        (r"\bmetadata\b", "info"),
        (r"\bsequence\b", "list"),
        (r"\binvariant\b", "rule"),
    ],
    "intermediate": [
        (r"\bfigure\s+out\b", "calculate"),
        (r"\bmake\s+sure\b", "validate"),
        (r"\bcheck\s+that\b", "verify that"),
        (r"\bloop\s+through\b", "iterate through"),
        (r"\bgo\s+through\b", "traverse"),
        (r"\bset\s+up\b", "initialize"),
        (r"\badd\s+up\b", "accumulate"),
        (r"\bwatch\s+out\s+for\b", "guard against"),
        (r"\bstarting\s+case\b", "base case"),
        (r"\bget\b", "retrieve"),
        (r"\bsave\b", "store"),
        (r"\brun\b", "execute"),
        (r"\binfo\b", "metadata"),
    ],
    "senior": [
        (r"\bcalculate\s+the\s+factorial\b", "evaluate factorial"),
        (r"\bcalculate\b", "evaluate"),
        (
            r"\bensure\s+input\s+is\s+a\s+non-negative\s+integer\b",
            "assert invariant: non-negative integer input required",
        ),
        (r"\bensure\s+input\s+is\b", "verify precondition: input must be"),
        (r"\bensure\b", "assert invariant"),
        (r"\bvalidate\b", "verify invariant constraint"),
        (r"\bvalidates\b", "verifies precondition"),
        (
            r"\biterate\s+through\s+numbers\s+up\s+to\s+n\s+to\s+accumulate\s+the\s+product\b",
            "sequentially accumulate product across range [2, n]",
        ),
        (r"\biterate\s+through\b", "sequentially traverse"),
        (r"\baccumulate\s+the\s+product\b", "accumulate product aggregation"),
        (r"\baccumulate\s+product\b", "aggregate iterative product"),
        (r"\baccumulate\b", "aggregate"),
        (
            r"\bguard\s+against\s+empty\s+sequence\b",
            "enforce boundary constraint: guard against empty sequence",
        ),
        (r"\bguard\s+against\b", "enforce boundary invariant: guard against"),
        (r"\bbase\s+case\b", "boundary condition"),
        (r"\binitialize\s+test\s+variables\b", "allocate and initialize test state"),
        (r"\binitialize\b", "allocate and initialize"),
        (r"\barithmetic\s+mean\b", "centroid expectation (mean)"),
        (r"\bsum\s+squared\s+differences\b", "accumulate squared deviations from expectation"),
        (r"\bexecute\s+sample\s+test\s+computations\b", "dispatch test execution suite"),
        (r"\bexecute\b", "dispatch execution of"),
        (r"\breturn\s+aggregated\s+metadata\s+dictionary\b", "yield assembled metadata mapping"),
        (r"\bstandard\s+iterative\s+algorithm\b", "standard O(N) iterative procedure"),
        (r"\bforward\s+declaration\b", "pre-symbol declaration"),
    ],
}


def _preserve_case(source: str, target: str) -> str:
    """Preserve source capitalization casing when applying replacement."""
    if not source or not target:
        return target
    if source.isupper():
        return target.upper()
    if source[0].isupper():
        return target[0].upper() + target[1:]
    return target.lower()


def apply_developer_persona(text: str, persona: str = "intermediate") -> str:
    """Adjust comment vocabulary according to developer persona tone.

    Args:
        text: Natural language comment text.
        persona: One of 'beginner', 'intermediate', 'senior' (or 'senior_architect').

    Returns:
        Adapted comment text.
    """
    key = persona.strip().lower()
    if key in ("senior", "senior_architect", "expert"):
        rules = PERSONA_VOCABULARY["senior"]
    elif key in ("beginner", "junior"):
        rules = PERSONA_VOCABULARY["beginner"]
    else:
        rules = PERSONA_VOCABULARY["intermediate"]

    result = text
    for pat_str, repl in rules:

        def _repl(match: re.Match[str]) -> str:
            return _preserve_case(match.group(0), repl)

        result = re.sub(pat_str, _repl, result, flags=re.IGNORECASE)

    return result

