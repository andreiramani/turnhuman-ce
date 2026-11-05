# TurnHuman Community Edition — End-User Guide (v3.1)

Welcome to **TurnHuman Community Edition (CE)**, a fast, privacy-first linguistic desktop application designed to humanize academic papers, research essays, code comments, and technical documents. 

TurnHuman operates on deterministic grammatical rules rather than generative AI (like ChatGPT), meaning it will **never invent facts, alter your empirical data, or leak your private files**. Everything happens directly in your computer's RAM. When you close the app, your text leaves no trace.

---

## 🧭 Navigation & Overview: The 5 Academic Features & Tools

TurnHuman CE features 5 dedicated tools accessible from the left sidebar navigation:

| Feature & Tool | Primary Function | Best For |
| :--- | :--- | :--- |
| **1. Plagiarism & AI Humanizer** | Rewrites robotic or stiff text and documents into natural human phrasing. | Academic essays, thesis chapters, research papers (`.docx`, `.tex`, `.txt`). |
| **2. Code Comment Humanizer** | Polishes comments in source code while leaving code logic 100% untouched. | Developers sharing code, coursework, or open-source repositories. |
| **3. Citation & BibTeX Inserter** | Resolves official DOIs from CrossRef and formats instant citations. | Researchers gathering references in BibTeX, APA, or IEEE. |
| **4. ZipPy Entropy Checker** | Scans text for repetitive patterns often flagged by AI detectors. | Pre-checking your papers before submission. |
| **5. Document Similarity Comparator** | Compares two texts side-by-side to highlight identical or modified sections. | Checking draft revisions or verifying originality. |

---

## 1. Plagiarism & AI Humanizer

This is the core workstation for transforming robotic, repetitive, or machine-generated text into fluid, natural writing.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HOW THE HUMANIZER WORKS                         │
│                                                                        │
│  [Your Original Text] ────► [16-Stage Linguistic Engine] ────► [Human] │
│      or Upload File               (In-Memory Only)             Output  │
│  (.docx, .tex, .txt)        Preserves Math & Citations        Download │
└────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Instructions:
1. **Choose Your Input Method**:
   - **Textarea**: Paste your text directly into the input box.
   - **File Upload**: Upload one or more `.docx` (Word), `.tex` (LaTeX), or `.txt` files.
2. **Select Academic Domain**:
   - Pick the topic that matches your paper (e.g., *Computer Science, Biomedical, Economics, Humanities, or General*). This ensures that technical terminology is preserved accurately.
3. **Adjust Transformation Intensity**:
   - **Synonym Replacement Rate (50% - 100%)**: Higher values replace more common AI buzzwords. 70%–80% is recommended for a balanced, natural tone.
4. **Choose Mode: Full vs. Zero-Expansion**:
   - **Full Transformation (Default)**: Restructures clauses, splits long run-on sentences, and injects varied transitions.
   - **Strict Zero-Expansion**: Guarantees that the **exact word count remains identical (0 net words added)**. Perfect when you must strictly adhere to a journal or publisher word limit.
5. **Set Protected Terms (Optional)**:
   - Type in names, proprietary product titles, brand names, or specific jargon separated by commas (e.g., `ResNet-50, PyTorch, CRISPR-Cas9`). TurnHuman will never modify these words.
6. **Click "⚡ Humanize Text" / "⚡ Process Documents"**:
   - Review the result in the **Interactive Side-by-Side Diff Viewer**:
     - <mark style="background-color: #fee2e2; color: #991b1b;">Red highlight</mark>: Removed or modified original words.
     - <mark style="background-color: #dcfce7; color: #166534;">Green highlight</mark>: New humanized alternatives.
     - <mark style="background-color: #fef9c3; color: #854d0e;">Yellow highlight</mark>: Protected technical terms.
7. **Download**:
   - Download the humanized text as `.txt` or grab the processed `.docx` / `.tex` file with all bolding, italics, headings, and equations intact.

---

## 2. Code Comment Humanizer

Automated coding assistants often write overly formal, repetitive comments (e.g., *"This function calculates the sum of two integers by adding them together"*). This module humanizes those comments while **guaranteeing that your actual code, variable names, and logic remain untouched**.

### Supported Languages:
Python (`#`), C/C++/Java/Go/Rust/JS/TS (`//` and `/* */`), SQL (`--`), Bash (`#`), R (`#`), and HTML/XML (`<!-- -->`).

### Step-by-Step Instructions:
1. Paste your code snippet or upload your script file.
2. Select your **Developer Persona**:
   - **Beginner**: Uses simple, accessible everyday words (*"loop through items"*, *"set up"*).
   - **Intermediate**: Standard, clean idiomatic developer language.
   - **Senior**: Concise, pragmatic, engineering-focused tone (*"guard against nil"*, *"accumulate"*).
3. Click **"Transform Comments"** and copy or download the refreshed code.

> [!NOTE]
> TurnHuman uses a stateful quote-aware scanner. It knows the difference between a real comment (`# note`) and a hashtag inside a text string (`url = "https://site.com#section"`). Your string literals and code logic are 100% safe.

---

## 3. Citation & BibTeX Inserter

Need to verify an academic paper or format a reference quickly? This module connects directly to the official **CrossRef DOI registry**.

### Step-by-Step Instructions:
1. Enter a **DOI** (e.g., `10.1038/nature12373`) or search by paper title and author.
2. Select your target **Discipline** (e.g., *Medicine, Computer Science, Physics*).
3. Click **"Resolve Citation"**.
4. The system will retrieve the verified title, journal, publication year, and authors directly from CrossRef.
5. Copy or download your citation in your desired format:
   - **BibTeX** (for LaTeX documents)
   - **APA 7th Edition**
   - **IEEE Format**

---

## 4. ZipPy Entropy Checker

AI detectors flag text that has low "perplexity" and low "burstiness" — meaning the text is too predictable and uses identical sentence lengths. The **ZipPy Entropy Checker** runs a mathematical compression scan to measure how predictable your text is.

### How to Read the Results:
- **Entropy Score (Gauge)**:
  - 🟢 **High Entropy / Safe (> 0.65)**: Diverse vocabulary, varied sentence structures, high human likelihood.
  - 🟡 **Moderate Entropy (0.45 - 0.65)**: Somewhat uniform phrasing; consider using the Humanizer on complex sections.
  - 🔴 **Low Entropy / High Risk (< 0.45)**: Stiff, highly predictable sentence patterns typical of raw AI output.
- **Risk Spans Table**:
  - Highlights specific paragraphs or sentences that show repetitive n-gram structures so you can edit them directly.

---

## 5. Document Similarity Comparator

Use this tool to compare two versions of an essay, article, or source file side-by-side.

### Step-by-Step Instructions:
1. Input **Document A** (Original) and **Document B** (Revised).
2. Click **"Compare Documents"**.
3. View the **Similarity Score (%)**:
   - Uses the Winnowing ($k=5, w=4$) and Karp-Rabin fingerprinting algorithms to detect identical paragraphs, restructured sentences, and swapped phrases.
4. Browse the synchronized diff viewer to verify that your revisions improved the text without losing important points.

---

## 💡 Practical Tips for Best Results

> [!TIP]
> 1. **Protect Your Jargon**: Always list product names, mathematical variables, and dataset names in the **Protected Terms** box.
> 2. **Keep Zero-Expansion ON for Strict Word Limits**: If your journal submission has a hard cap of 3,000 words, toggle on **Strict Zero-Expansion** mode to ensure the word count never increases.
> 3. **Run ZipPy Before and After**: Test your text in the *ZipPy Entropy Checker* before humanizing, then re-check afterwards to see the measurable increase in entropy and sentence variety.
> 4. **Bilingual Support**: TurnHuman CE supports English (`en`) and Indonesian (`id`). You can toggle the UI language anytime from the left sidebar settings.
