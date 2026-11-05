"""TurnHuman Module 2: Code Comment Humanizer UI (v3.0.0-PROD).

Provides:
- Multi-language selection: Python, C/C++, Java, JS/TS, Rust, Go, SQL, Bash/HTML.
- Developer Persona vocabulary tuning: Beginner, Intermediate, Senior Architect.
- Stateful Quote-Aware comment transformation guarantee.
- Side-by-side code editor display and file export.
"""

from __future__ import annotations

import logging
from typing import Dict

import streamlit as st

from TurnHuman.core.code_processor import process_code
from TurnHuman.ui.common import check_rate_limit
from TurnHuman.ui.i18n import t

logger = logging.getLogger("TurnHuman.ui.code_ui")

# Language definitions and file extensions
LANGUAGE_OPTIONS = {
    "Python (.py)": ("python", ".py"),
    "C/C++ (.cpp, .c)": ("cpp", ".cpp"),
    "Java (.java)": ("java", ".java"),
    "JavaScript / TypeScript (.ts, .js)": ("typescript", ".ts"),
    "Rust (.rs)": ("rust", ".rs"),
    "Go (.go)": ("go", ".go"),
    "SQL (.sql)": ("sql", ".sql"),
    "Bash Script (.sh)": ("bash", ".sh"),
    "HTML / XML (.html)": ("html", ".html"),
}

SAMPLE_CODES: Dict[str, str] = {
    "python": '''def compute_factorial(n: int) -> int:
    # Computes the factorial of input number
    # Ensure input is non-negative before proceeding
    if n < 0:
        raise ValueError("n must be non-negative, got #invalid value")

    # Base case: factorial of 0 is 1
    if n == 0:
        return 1

    # Accumulate product iteratively
    result = 1
    # Iterate through numbers from 1 to n
    for i in range(1, n + 1):
        result *= i

    # Obtain and return final aggregated result
    return result
''',
    "cpp": '''// Computes the arithmetic mean of an array
double calculate_mean(const double arr[], int size) {
    // Ensure size is strictly positive
    if (size <= 0) return 0.0;

    // Accumulate total sum iteratively
    double sum = 0.0;
    for (int i = 0; i < size; ++i) {
        sum += arr[i]; /* Add current element */
    }

    // Return aggregated average
    return sum / size;
}
''',
    "java": '''public class MathUtils {
    // Computes the factorial of input
    public static long factorial(int n) {
        // Ensure input is non-negative
        if (n < 0) throw new IllegalArgumentException("n >= 0");

        // Initialize accumulator product
        long result = 1;
        // Loop through sequence
        for (int i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }
}
''',
    "typescript": '''// Computes the sum of all elements in array
function sumArray(values: number[]): number {
    // Validate input array is not empty
    if (!values || values.length === 0) {
        return 0;
    }

    // Accumulate product or sum across elements
    let total = 0;
    for (const val of values) {
        total += val; // Add current value to accumulator
    }

    return total;
}
''',
}


def render_code_page() -> None:
    """Render the Code Comment Humanizer workstation."""
    st.markdown(f"## {t('code.title', '💻 Module 2: Code Comment Humanizer')}")
    st.caption(
        t(
            "code.subtitle",
            "Stateful Quote-Aware comment transformation. Guarantees 0% modification to program syntax, code variables, or execution logic.",
        )
    )

    # 1. Top Controls
    c_lang, c_persona = st.columns([1.5, 1.5])

    with c_lang:
        selected_lang_label = st.selectbox(
            t("code.select_lang", "Programming Language"),
            options=list(LANGUAGE_OPTIONS.keys()),
            index=0,
            help="Select the language syntax parser for quote-state machine.",
        )
        canon_lang, file_ext = LANGUAGE_OPTIONS[selected_lang_label]

    with c_persona:
        persona_choice = st.radio(
            t("code.select_persona", "Developer Persona"),
            ["intermediate", "beginner", "senior"],
            index=0,
            format_func=lambda p: {
                "beginner": "🐣 Beginner (Conversational, Direct, Simple)",
                "intermediate": "🛠️ Intermediate (Standard Idiomatic Engineering)",
                "senior": "🏛️ Senior Architect (Concise, Systems Rationale)",
            }[p],
            horizontal=True,
            help="Modulates comment vocabulary from simple explanations to architectural rationale.",
        )

    # 2. Quote-Aware Integrity Guarantee Banner
    st.markdown(
        """
        <div style="padding: 10px 14px; background: rgba(16, 185, 129, 0.08); border: 1px solid #10B981; border-radius: 8px; margin: 12px 0 16px 0; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2rem;">🛡️</span>
            <div style="font-size: 0.825rem; color: var(--th-text-secondary, #334155); line-height: 1.4;">
                <b style="color: #065F46;">Quote-Aware Scanner Guarantee Active:</b>
                String literals (e.g. <code style="font-family:monospace;">"URL: #frag"</code>, <code style="font-family:monospace;">'//not a comment'</code>), 
                regex expressions, and code keywords are <b>100% protected</b>. 
                Only genuine inline (<code style="font-family:monospace;">#</code>, <code style="font-family:monospace;">//</code>, <code style="font-family:monospace;">--</code>) 
                and block (<code style="font-family:monospace;">/* */</code>, <code style="font-family:monospace;">&lt;!-- --&gt;</code>) comments are humanized.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Code Editor Input
    default_sample = SAMPLE_CODES.get(canon_lang, SAMPLE_CODES["python"])

    c_edit1, c_edit2 = st.columns([1, 1])

    with c_edit1:
        st.markdown(f"##### {t('code.input_header', '📄 Source Code (with AI-Generated Comments)')}")
        source_code = st.text_area(
            t("code.input_label", "Input Code"),
            value=default_sample,
            height=340,
            key="input_code_area",
            help="Paste source code with formulaic or AI-generated comments.",
        )

        run_btn = st.button(t("code.btn_run", "🚀 Humanize Comments"), type="primary")

    output_code = ""
    if run_btn:
        if not source_code.strip():
            st.warning(t("code.warn_empty", "Please provide source code."))
        elif not check_rate_limit():
            st.stop()
        else:
            with st.spinner(t("code.spinner", "Scanning tokens and humanizing comments in-memory...")):
                output_code = process_code(
                    source_code,
                    language=canon_lang,
                    persona=persona_choice,
                )
            st.session_state["_last_output_code"] = output_code
    elif "_last_output_code" in st.session_state:
        output_code = st.session_state["_last_output_code"]

    with c_edit2:
        st.markdown(f"##### {t('code.output_header', '✨ Humanized Source Code Output')}")
        if output_code:
            st.code(output_code, language=canon_lang if canon_lang != "bash" else "bash")
            st.download_button(
                label=t("code.btn_download", f"📥 Download Code ({file_ext})", ext=file_ext),
                data=output_code.encode("utf-8"),
                file_name=f"humanized_code{file_ext}",
                mime="text/plain",
                type="primary",
            )
        else:
            st.info("Click **'🚀 Humanize Comments'** to inspect transformed source code.")
