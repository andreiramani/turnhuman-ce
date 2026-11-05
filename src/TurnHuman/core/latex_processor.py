"""TurnHuman LaTeX Manuscript Zone Parser & Sentinel Masker (v3.0.1-MODULAR)."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, List, Optional, Union

from TurnHuman.core.modifier import humanize_text, strip_zero_width_chars

logger = logging.getLogger("TurnHuman.core.latex_processor")

__all__ = ["process_latex"]

# =============================================================================
# LaTeX Manuscript (.tex) Zone Parser
# =============================================================================

def process_latex(
    latex_input: Union[str, bytes],
    transform_fn: Optional[Callable[[str], str]] = None,
    protected_commands: Optional[List[str]] = None,
    **kwargs: Any,
) -> str:
    """Process a LaTeX document, protecting preamble, math, citations, and structural tags.

    Args:
        latex_input: LaTeX source code as a string or utf-8 encoded bytes.
        transform_fn: Optional string transformer. If None, uses humanize_text with kwargs.
        protected_commands: Additional LaTeX command names or regex patterns to protect.
        **kwargs: Extra parameters passed to humanize_text if transform_fn is None.

    Returns:
        Transformed LaTeX document string with all formulas and macros 100% restored.
    """
    if isinstance(latex_input, bytes):
        latex_str = latex_input.decode("utf-8", errors="replace")
    else:
        latex_str = str(latex_input)

    latex_str = strip_zero_width_chars(latex_str)

    if transform_fn is None:
        from TurnHuman.core.modifier import humanize_text

        transform_fn = lambda text: humanize_text(text, **kwargs)[0]

    # Step 1: Zone separation: Preamble vs Body
    match_doc_begin = re.search(r"\\begin\{document\}", latex_str)
    match_doc_end = re.search(r"\\end\{document\}", latex_str)

    if match_doc_begin:
        preamble_end = match_doc_begin.end()
        preamble = latex_str[:preamble_end]
        if match_doc_end:
            body_end = match_doc_end.start()
            body = latex_str[preamble_end:body_end]
            postamble = latex_str[body_end:]
        else:
            body = latex_str[preamble_end:]
            postamble = ""
    else:
        preamble = ""
        body = latex_str
        postamble = ""

    # Step 2: Protection masks
    masks: Dict[str, str] = {}
    mask_counter = 0

    def _mask_replacer(m: re.Match[str]) -> str:
        nonlocal mask_counter
        matched = m.group(0)
        tok = f"\x00TEX_ZONE_MASK_{mask_counter}\x00"
        masks[tok] = matched
        mask_counter += 1
        return tok

    # Build regex patterns in priority order
    patterns: List[re.Pattern[str]] = [
        # 1. LaTeX comments (% ...)
        re.compile(r"(?<!\\)%.*$", re.MULTILINE),
        # 2. Math environments
        re.compile(
            r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|split\*?|eqnarray\*?|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|cases)\}.*?\\end\{(?:equation\*?|align\*?|gather\*?|multline\*?|split\*?|eqnarray\*?|matrix|pmatrix|bmatrix|vmatrix|Vmatrix|cases)\}",
            re.DOTALL,
        ),
        # 3. Structural blocks (tables, figures, code listings, algorithms)
        re.compile(
            r"\\begin\{(?:table\*?|figure\*?|lstlisting|algorithm)\}.*?\\end\{(?:table\*?|figure\*?|lstlisting|algorithm)\}",
            re.DOTALL,
        ),
        # 4. Display math
        re.compile(r"\$\$[\s\S]*?\$\$"),
        re.compile(r"\\\[[\s\S]*?\\\]"),
        # 5. Inline math
        re.compile(r"(?<!\\)\$(?!\$)[^\$\n\x00]+(?<!\\)\$"),
        re.compile(r"\\\(.*?\\\)"),
        # 6. Citations
        re.compile(r"\\cite[a-zA-Z*]*\{[^}]*\}"),
        # 7. Cross-references, labels, equation numbers
        re.compile(r"\\(?:ref|pageref|label|autoref|eqref|nameref)\{[^}]*\}"),
        # 8. Sectioning commands
        re.compile(
            r"\\(?:section|subsection|subsubsection|chapter|paragraph|subparagraph)\*?\{[^}]*\}"
        ),
        # 9. LaTeX structure tags & bibliography
        re.compile(
            r"\\(?:maketitle|tableofcontents|bibliographystyle\{[^}]*\}|bibliography\{[^}]*\}|begin\{abstract\}|end\{abstract\}|begin\{itemize\}|end\{itemize\}|begin\{enumerate\}|end\{enumerate\}|item(?:\s*\[[^\]]*\])?)"
        ),
    ]

    # Add custom protected commands if provided
    if protected_commands:
        for cmd in protected_commands:
            escaped = re.escape(cmd.strip("\\"))
            patterns.append(re.compile(rf"\\{escaped}(?:\{{[^}}]*\}})?"))

    masked_body = body
    for pat in patterns:
        masked_body = pat.sub(_mask_replacer, masked_body)

    # Step 3: Transform narrative text
    try:
        transformed_body = transform_fn(masked_body)
    except Exception as exc:
        logger.error(f"Error transforming LaTeX body: {exc}; preserving original text.")
        transformed_body = masked_body

    # Step 4: Restore all masks with 100% character precision
    for tok, original_str in masks.items():
        transformed_body = transformed_body.replace(tok, original_str)

    # Safety audit: ensure no sentinel tokens leaked into the output
    leftover = re.findall(r"\x00TEX_ZONE_MASK_\d+\x00", transformed_body)
    if leftover:
        logger.critical(
            f"Leftover mask tokens detected in LaTeX output: {leftover}. Forcing fallback."
        )
        return latex_str

    return f"{preamble}{transformed_body}{postamble}"


