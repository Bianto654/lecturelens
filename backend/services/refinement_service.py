from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Fuzzy Glossary Matcher (Levenshtein + n-gram sliding window)
# ---------------------------------------------------------------------------

STOPWORDS = {
    "yang", "dan", "atau", "dari", "untuk", "dengan", "pada", "dalam", "adalah",
    "ini", "itu", "kita", "kami", "anda", "mereka", "akan", "bisa", "dapat",
    "tidak", "bukan", "juga", "sudah", "belum", "harus", "karena", "sehingga",
    "jika", "kalau", "maka", "agar", "tentang", "seperti", "oleh", "antara",
    "setelah", "sebelum", "sampai", "hingga", "sebuah", "suatu", "lebih",
    "kurang", "sama", "sangat", "hanya", "masih", "sedang", "telah", "setiap",
    "nilai", "fungsi", "rumus", "hitung", "lihat", "perhatikan", "misalnya",
    "the", "and", "for", "with", "that", "this", "from", "have", "were", "been",
    "will", "would", "could", "should", "about", "into", "over", "after",
    "before", "between", "through", "during", "above", "below", "under", "then",
    "here", "there", "when", "where", "which", "while", "their", "these", "those",
    "value", "function", "result", "example", "compute", "calculate", "consider",
}


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _norm(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^a-z0-9\s-]", "", stripped)
    return re.sub(r"\s+", " ", cleaned).strip()


@dataclass
class GlossarySpan:
    start: int
    end: int
    original: str
    matched_term: str
    was_corrected: bool
    similarity: float


def find_glossary_spans(text: str, glossary: list[str]) -> list[GlossarySpan]:
    unique_terms = list(dict.fromkeys(t.strip() for t in glossary if t.strip()))
    if not text.strip() or not unique_terms:
        return []

    prepared = []
    for term in unique_terms:
        nt = _norm(term)
        if nt:
            prepared.append((term, nt, len(nt.split())))
    prepared.sort(key=lambda x: (-x[2], -len(x[1])))

    tokens = [
        (m.group(0), _norm(m.group(0)), m.start(), m.end())
        for m in re.finditer(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*", text)
    ]
    if not tokens:
        return []

    spans: list[GlossarySpan] = []
    used: set[int] = set()

    for term, norm_term, k in prepared:
        if k > len(tokens):
            continue
        for i in range(len(tokens) - k + 1):
            if any(j in used for j in range(i, i + k)):
                continue
            window = tokens[i : i + k]
            span_start = window[0][2]
            span_end = window[-1][3]
            original = text[span_start:span_end]
            cand = " ".join(w[1] for w in window)
            if not cand:
                continue

            if cand == norm_term:
                spans.append(
                    GlossarySpan(span_start, span_end, original, term, False, 1.0)
                )
                used.update(range(i, i + k))
                continue

            if len(norm_term) < 4:
                continue
            if k == 1 and cand in STOPWORDS:
                continue
            if k > 1 and re.search(r"[.!?;:\n]", original):
                continue

            max_len = max(len(cand), len(norm_term))
            if abs(len(cand) - len(norm_term)) > max(2, int(max_len * 0.3)):
                continue

            dist = levenshtein(cand, norm_term)
            sim = 1.0 - dist / max_len
            max_dist = (
                (3 if len(norm_term) >= 10 else 2 if len(norm_term) >= 5 else 1)
                if k == 1
                else min(4, max(2, int(max_len * 0.25)))
            )
            min_sim = 0.72 if k == 1 else 0.75
            first_ok = k > 1 or cand[0] == norm_term[0] or sim >= 0.8

            if dist <= max_dist and sim >= min_sim and first_ok:
                spans.append(
                    GlossarySpan(
                        span_start, span_end, original, term, True, round(sim, 2)
                    )
                )
                used.update(range(i, i + k))

    return sorted(spans, key=lambda s: s.start)


# ---------------------------------------------------------------------------
# 2. Rule-Based Spoken + ASR Math -> LaTeX Formatter (Indonesian & English)
#    Handles both spoken math ("integral dari nol sampai satu x kuadrat dx",
#    "de per de ex", "2x pangkat 5") AND Google Web Speech ASR shorthands
#    ("5x²", "2x ^ 5", "√5", "√5x^3", "5/3", "x² + 3 = 5").
# ---------------------------------------------------------------------------

NUMBER_WORDS = {
    "nol": "0", "kosong": "0", "satu": "1", "dua": "2", "tiga": "3", "empat": "4",
    "lima": "5", "enam": "6", "tujuh": "7", "delapan": "8", "sembilan": "9",
    "sepuluh": "10", "sebelas": "11", "duabelas": "12", "seratus": "100",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "hundred": "100",
}

SPOKEN_VAR_MAP = {
    "ex": "x", "eks": "x", "x": "x",
    "ye": "y", "y": "y",
    "zet": "z", "zed": "z", "z": "z",
    "te": "t", "t": "t",
    "u": "u", "v": "v",
    "ef": "f", "f": "f",
    "ge": "g", "g": "g",
    "ha": "h", "h": "h",
    "en": "n", "n": "n",
}

GREEK_WORDS = {
    "alfa": r"\alpha", "alpha": r"\alpha", "beta": r"\beta", "gamma": r"\gamma",
    "delta": r"\delta", "epsilon": r"\epsilon", "theta": r"\theta", "teta": r"\theta",
    "lambda": r"\lambda", "lamda": r"\lambda", "mu": r"\mu", "pi": r"\pi",
    "phi": r"\phi", "sigma": r"\sigma", "omega": r"\omega",
}

UNICODE_SUPERSCRIPTS = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "ⁿ": "n", "ⁱ": "i", "⁺": "+", "⁻": "-",
}
SUP_CHARS = "".join(UNICODE_SUPERSCRIPTS.keys())

NON_MATH_PER = {
    "hari", "minggu", "bulan", "tahun", "jam", "menit", "detik", "sekon",
    "orang", "siswa", "mahasiswa", "dosen", "unit", "item", "persen",
    "meter", "kilometer", "liter", "gram", "kilogram", "day", "week", "month",
    "year", "hour", "minute", "second", "person", "student", "percent", "satu",
}


def _fmt_exp(exp: str) -> str:
    c = exp.strip()
    return f"^{c}" if len(c) == 1 else f"^{{{c}}}"


def _fmt_sub(sub: str) -> str:
    c = sub.strip()
    return f"_{c}" if len(c) == 1 else f"_{{{c}}}"


def _normalize_var(raw: str) -> str:
    low = raw.strip().lower()
    return SPOKEN_VAR_MAP.get(low, raw.strip())


def _replace_unicode_superscripts(s: str) -> str:
    def _conv(m: re.Match[str]) -> str:
        digits = "".join(UNICODE_SUPERSCRIPTS[ch] for ch in m.group(0))
        return _fmt_exp(digits)

    return re.sub(f"[{re.escape(SUP_CHARS)}]+", _conv, s)


def spoken_expr_to_latex(raw: str) -> str:
    s = raw.strip()

    # Convert Unicode superscripts (e.g. 5x² -> 5x^2, x³ -> x^3)
    s = _replace_unicode_superscripts(s)

    # Convert Unicode roots inside expressions (e.g. √5x^3 -> \sqrt{5x^3}, √(x+1) -> \sqrt{x+1})
    s = re.sub(r"√\(([^)]+)\)", lambda m: rf"\sqrt{{{spoken_expr_to_latex(m.group(1))}}}", s)
    s = re.sub(
        r"√\s*([0-9]*[a-zA-Z0-9]+(?:\s*\^\s*\{?-?[a-zA-Z0-9]+\}?)?)",
        lambda m: rf"\sqrt{{{re.sub(r'\s*\^\s*', '^', m.group(1))}}}",
        s,
    )

    # Multi-word symbols first
    s = re.sub(r"\b(tak\s+hingga|tak\s+terhingga|infinity)\b", r"\\infty", s, flags=re.I)
    s = re.sub(r"\b(lebih\s+besar\s+sama\s+dengan|greater\s+than\s+or\s+equal\s+to)\b", r"\\ge", s, flags=re.I)
    s = re.sub(r"\b(kurang\s+dari\s+sama\s+dengan|less\s+than\s+or\s+equal\s+to)\b", r"\\le", s, flags=re.I)
    s = re.sub(r"\b(tidak\s+sama\s+dengan|not\s+equal\s+to)\b", r"\\neq", s, flags=re.I)
    s = re.sub(r"\b(sama\s+dengan|equals)\b", "=", s, flags=re.I)

    # Spoken negative before number/var (e.g. "pangkat negatif 2", "minus satu")
    s = re.sub(r"\b(?:negatif|negative)\s+", "-", s, flags=re.I)

    def _replace_word(m: re.Match[str]) -> str:
        w = m.group(1)
        lw = w.lower()
        if lw in NUMBER_WORDS:
            return NUMBER_WORDS[lw]
        if lw in GREEK_WORDS:
            return GREEK_WORDS[lw]
        return w

    s = re.sub(r"\b([A-Za-z]+)\b", _replace_word, s)
    s = re.sub(r"\b([fghp])\s+(?:dari|of)\s+([a-zA-Z0-9])\b", r"\1(\2)", s, flags=re.I)
    s = re.sub(r"\b(sin|cos|tan|csc|sec|cot|log|ln)\b", lambda m: "\\" + m.group(1).lower(), s, flags=re.I)

    # Tighten spaced coefficients like "5 x" -> "5x" (when followed by power/op/end)
    s = re.sub(r"\b([0-9]+)\s+([a-zA-Z])\b", r"\1\2", s)

    # Tighten ASCII caret spaces: "2x ^ 5" -> "2x^5", "x ^ -2" -> "x^{-2}"
    s = re.sub(
        r"(\\[a-z]+|[0-9]*[a-zA-Z0-9)(]+)\s*\^\s*(-?[a-zA-Z0-9]+)",
        lambda m: f"{m.group(1)}{_fmt_exp(m.group(2))}",
        s,
    )

    # Spoken powers inside expressions: "2x kuadrat", "5x pangkat 3", "x pangkat 5"
    s = re.sub(r"(\\[a-z]+|[0-9]*[a-zA-Z0-9)(]+)\s+(?:kuadrat|squared)\b", r"\1^2", s, flags=re.I)
    s = re.sub(r"(\\[a-z]+|[0-9]*[a-zA-Z0-9)(]+)\s+(?:kubik|cubed)\b", r"\1^3", s, flags=re.I)
    s = re.sub(
        r"(\\[a-z]+|[0-9]*[a-zA-Z0-9)(]+)\s+(?:pangkat|to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?)\s+(-?\\[a-z]+|-?[a-zA-Z0-9]+)",
        lambda m: f"{m.group(1)}{_fmt_exp(m.group(2))}",
        s,
        flags=re.I,
    )

    # Inline slash or spoken fractions inside expressions: "sin x per x", "5/3"
    s = re.sub(
        r"(\\[a-z]+\s+[a-zA-Z0-9]+|[0-9]*[a-zA-Z0-9^_{}]+)\s*(?:/|\b(?:per|dibagi|over|divided\s+by)\b)\s*(\\[a-z]+\s+[a-zA-Z0-9]+|[0-9]*[a-zA-Z0-9^_{}]+)",
        r"\\frac{\1}{\2}",
        s,
        flags=re.I,
    )

    # Operators
    s = re.sub(r"\s*\b(ditambah|tambah|plus)\b\s*", "+", s, flags=re.I)
    s = re.sub(r"\s*\b(dikurangi|dikurang|kurang|minus)\b\s*", "-", s, flags=re.I)
    s = re.sub(r"\s*\b(dikali|kali|times)\b\s*", r" \\cdot ", s, flags=re.I)
    s = re.sub(r"\s*\+\s*", "+", s)
    s = re.sub(r"(?<=[a-zA-Z0-9})])\s*-\s*(?=[a-zA-Z0-9\\(])", "-", s)
    s = re.sub(r"\s*=\s*", " = ", s)
    s = re.sub(r"\s+d([xyztuv])\b", r"\\,d\1", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def _norm_bound(raw: str) -> str:
    return spoken_expr_to_latex(re.sub(r"^(?:negatif|minus|negative)\s+", "-", raw, flags=re.I))


# Core math building blocks supporting:
#  - optional coefficient ("5x", "2x", "5 x")
#  - Unicode superscripts ("5x²", "x³")
#  - ASCII carets ("2x ^ 5", "5 x ^ 3")
#  - Unicode roots ("√5", "√5x^3")
#  - spoken powers ("x pangkat 5", "2x pangkat tiga", "x kuadrat")
NUMBER_WORD_ALT = (
    r"tak\s+hingga|tak\s+terhingga|infinity|"
    r"nol|kosong|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh|sebelas|seratus|"
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred"
)
GREEK_WORD_ALT = r"alfa|alpha|beta|gamma|delta|epsilon|theta|teta|lambda|lamda|mu|pi|phi|sigma|omega"
MATH_SCALAR = rf"(?:(?:negatif|minus|negative)\s+)?(?:{NUMBER_WORD_ALT}|{GREEK_WORD_ALT}|[0-9]+|[a-zA-Z])"

# Variable or coefficient+variable or number, optionally with Unicode superscript or ^ exp
MATH_BASE = (
    rf"(?:(?:negatif|minus|negative)\s+)?"
    rf"(?:√\s*\([^)]+\)|√\s*[0-9]*[a-zA-Z0-9]+|"
    rf"(?:{NUMBER_WORD_ALT}|{GREEK_WORD_ALT})|"
    rf"[0-9]+\s*[a-zA-Z]|[0-9]+|[a-zA-Z])"
    rf"(?:[{re.escape(SUP_CHARS)}]+)?"
)

POWER_SUFFIX = (
    rf"(?:\s*(?:\^\s*-?(?:{NUMBER_WORD_ALT}|[0-9]+|[a-zA-Z])|"
    rf"kuadrat|squared|kubik|cubed|"
    rf"(?:pangkat|to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?)\s+{MATH_SCALAR}))?"
)

EXPR_ATOM = rf"(?:(?:sin|cos|tan|log|ln)\s+)?{MATH_BASE}{POWER_SUFFIX}"
EXPR_OP = r"(?:\+|-|\*|/|ditambah|tambah|plus|dikurangi|dikurang|kurang|minus|dikali|kali|times|per|over)"
EXPR_CHAIN = rf"{EXPR_ATOM}(?:\s*{EXPR_OP}\s*{EXPR_ATOM}){{0,4}}"

SPOKEN_VAR_ALT = r"ex|eks|ye|zet|zed|te|ef|ge|ha|en|[a-zA-Z]"


@dataclass
class FormulaSpan:
    start: int
    end: int
    original_text: str
    latex: str
    ambiguous: bool
    rule_name: str


def find_formula_spans(text: str) -> list[FormulaSpan]:
    if not text.strip():
        return []

    spans: list[FormulaSpan] = []

    def overlaps(s: int, e: int) -> bool:
        return any(s < sp.end and e > sp.start for sp in spans)

    rules = [
        # 1. Definite integral (with OR without trailing dx/dy/dt)
        (
            "definite-integral",
            re.compile(
                rf"\bintegral\s+(?:dari|from)\s+({MATH_SCALAR})\s+(?:sampai|hingga|to)\s+({MATH_SCALAR})\s+(?:(?:dari|of)\s+)?({EXPR_CHAIN})(?:\s*(d[xyztuv]))?(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: _build_definite_integral(m),
        ),
        # 2. Indefinite integral (with OR without trailing dx! Handles "Integral dari 5x²", "Integral 2x ^ 5", "integral dari 5 x ^ 3")
        (
            "indefinite-integral",
            re.compile(
                rf"\bintegral\s+(?:(?:dari|of)\s+)?({EXPR_CHAIN})(?:\s*(d[xyztuv]))?(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: _build_indefinite_integral(m),
        ),
        # 3. Spoken & symbolic derivatives:
        #    "de per de ex", "d per dx", "de ye per de ex", "dy per dx", "d/dx", "dy/dx",
        #    "de per de ex dari x pangkat 3", "turunan dari y terhadap x"
        (
            "derivative-operator",
            re.compile(
                rf"\b(?:(?:de|d)\s+(?:({SPOKEN_VAR_ALT})\s+)?(?:per|/)\s+(?:de|d)\s*({SPOKEN_VAR_ALT})|"
                rf"d([a-zA-Z])?\s*(?:per|/)\s*d([a-zA-Z]))(?:\s+(?:(?:dari|of)\s+)?({EXPR_CHAIN}))?(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: _build_derivative_op(m),
        ),
        (
            "derivative-words",
            re.compile(
                rf"\b(?:turunan|derivatif|derivative)\s+(?:(?:dari|of)\s+)?({EXPR_CHAIN})\s+(?:terhadap|with\s+respect\s+to)\s+({SPOKEN_VAR_ALT})\b",
                re.I,
            ),
            lambda m: _build_derivative_words(m),
        ),
        # 4. Prime notation: "f aksen x", "f double aksen x", "f prime of x"
        (
            "prime-derivative",
            re.compile(
                r"\b([fghy])\s+(double\s+aksen|dobel\s+aksen|double\s+prime|aksen|prime)(?:\s+(?:(?:dari|of)\s+)?([a-zA-Z]))?\b",
                re.I,
            ),
            lambda m: _build_prime(m),
        ),
        # 5. Limit (ID & EN)
        (
            "limit",
            re.compile(
                rf"\blimit\s+(?:as\s+)?([a-zA-Z])\s+(?:menuju|mendekati|approaches)\s+({MATH_SCALAR})(?:\s+(?:dari|of)\s+({EXPR_CHAIN}))?",
                re.I,
            ),
            lambda m: (
                rf"\lim_{{{m.group(1)} \to {_norm_bound(m.group(2))}}}"
                + (f" {spoken_expr_to_latex(m.group(3))}" if m.group(3) else ""),
                bool(m.group(3) and re.search(r"[+-]", spoken_expr_to_latex(m.group(3)))),
            ),
        ),
        # 6. Summation / Sigma (ID & EN)
        (
            "summation",
            re.compile(
                rf"\b(?:sigma|sum|summation)\s+(?:dari|from)\s+([a-zA-Z])\s+(?:sama\s+dengan|equals|=)\s+({MATH_SCALAR})\s+(?:sampai|hingga|to)\s+({MATH_SCALAR})\b",
                re.I,
            ),
            lambda m: (
                rf"\sum_{{{m.group(1)}={_norm_bound(m.group(2))}}}^{{{_norm_bound(m.group(3))}}}",
                False,
            ),
        ),
        # 7. Spoken roots: "akar dari x tambah satu", "akar pangkat tiga dari 8", "square root of x plus one"
        (
            "root",
            re.compile(
                rf"\b(akar\s+pangkat\s+tiga|cube\s+root|akar\s+kuadrat|square\s+root|akar)\s+(?:(?:dari|of)\s+)?({EXPR_CHAIN})(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: (
                (
                    rf"\sqrt[3]{{{spoken_expr_to_latex(m.group(2))}}}"
                    if ("tiga" in m.group(1).lower() or "cube" in m.group(1).lower())
                    else rf"\sqrt{{{spoken_expr_to_latex(m.group(2))}}}"
                ),
                bool(re.search(r"[+-]", spoken_expr_to_latex(m.group(2)))),
            ),
        ),
        # 8. Inline equations with math symbols (e.g. "x² + 3 = 5", "2x^3 - 1 = 0", "y = 5x^2 + 1")
        (
            "equation",
            re.compile(
                rf"(?<![A-Za-z0-9])({EXPR_CHAIN})\s*(=|<=|>=|!=|sama\s+dengan|equals)\s*({EXPR_CHAIN})(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: _build_equation(m),
        ),
        # 9. Unicode root expressions emitted by Google STT: "√5", "√5 x² √5x^3", "√(x+1)"
        (
            "unicode-root",
            re.compile(
                rf"√\s*(?:\([^)]+\)|[0-9]*[a-zA-Z0-9]+(?:[{re.escape(SUP_CHARS)}]+|\s*\^\s*-?[a-zA-Z0-9]+)?)"
                rf"(?:\s+(?:√\s*[0-9]*[a-zA-Z0-9]+|[0-9]*[a-zA-Z]+)(?:[{re.escape(SUP_CHARS)}]+|\s*\^\s*-?[a-zA-Z0-9]+)?)*",
                re.I,
            ),
            lambda m: (spoken_expr_to_latex(m.group(0)), False),
        ),
        # 10. Slash fractions (e.g. "5/3", "x/2", avoiding dates like 25/11/2026)
        (
            "slash-fraction",
            re.compile(
                r"(?<![0-9/A-Za-z])([0-9]+|[a-zA-Z]|[0-9]+[a-zA-Z])\s*/\s*([0-9]+|[a-zA-Z]|[0-9]+[a-zA-Z])(?![0-9/A-Za-z])"
            ),
            lambda m: (rf"\frac{{{m.group(1)}}}{{{m.group(2)}}}", True),
        ),
        # 11. Spoken fractions ("a per b", "x tambah satu dibagi y", "one over x")
        (
            "fraction",
            re.compile(
                rf"\b({EXPR_ATOM}(?:\s+(?:ditambah|tambah|plus|dikurangi|dikurang|kurang|minus)\s+{EXPR_ATOM})?)\s+(per|dibagi|over|divided\s+by)\s+({EXPR_ATOM})\b",
                re.I,
            ),
            lambda m: _build_fraction(m),
        ),
        # 12. Spoken OR caret/superscript powers:
        #     "x kuadrat", "x pangkat 3", "2x pangkat 5", "5 x ^ 3", "2x ^ 5", "5x²", "x^5"
        (
            "power",
            re.compile(
                rf"(?<![A-Za-z0-9])({MATH_BASE})\s*(?:"
                rf"(kuadrat|squared|kubik|cubed)|"
                rf"(\^\s*-?(?:{NUMBER_WORD_ALT}|[0-9]+|[a-zA-Z]))|"
                rf"((?:pangkat|to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?)\s+{MATH_SCALAR}(?:\s+(?:tambah|plus|kurang|minus)\s+{MATH_SCALAR})?)"
                rf")(?=$|[\s.,!?;:)])",
                re.I,
            ),
            lambda m: _build_power(m),
        ),
        # 13. Standalone Unicode superscript term emitted by STT (e.g. "5x²", "x³")
        (
            "unicode-power",
            re.compile(rf"(?<![A-Za-z0-9])([0-9]*[a-zA-Z0-9]+[{re.escape(SUP_CHARS)}]+)(?=$|[\s.,!?;:)])"),
            lambda m: (spoken_expr_to_latex(m.group(1)), False),
        ),
    ]

    for rule_name, regex, builder in rules:
        for m in regex.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            built = builder(m)
            if not built:
                continue
            latex, ambig = built
            if not latex:
                continue
            spans.append(
                FormulaSpan(m.start(), m.end(), m.group(0), latex, ambig, rule_name)
            )

    return sorted(spans, key=lambda s: s.start)


def _looks_like_math_expr(expr_raw: str) -> bool:
    """Prevents matching plain prose words like 'Integral dari materi ini'."""
    s = expr_raw.strip()
    if not s:
        return False
    # Contains digits, math operators, superscripts, roots, or single-letter math variable
    if re.search(rf"[0-9^√+\-*/={re.escape(SUP_CHARS)}]", s):
        return True
    if re.search(r"\b(kuadrat|squared|kubik|cubed|pangkat|sin|cos|tan|log|ln|akar|per|tambah|kurang|kali)\b", s, re.I):
        return True
    if re.fullmatch(r"[a-zA-Z](?:\s*\([a-zA-Z]\))?", s):
        return True
    return False


def _build_definite_integral(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    lower = _norm_bound(m.group(1))
    upper = _norm_bound(m.group(2))
    body_raw = m.group(3)
    if not _looks_like_math_expr(body_raw):
        return None
    body = spoken_expr_to_latex(body_raw)
    diff = m.group(4).lower() if m.group(4) else None
    suffix = rf"\,{diff}" if diff else ""
    ambig = bool(re.search(r"[+-]", body)) or diff is None
    return (rf"\int{_fmt_sub(lower)}{_fmt_exp(upper)} {body}{suffix}", ambig)


def _build_indefinite_integral(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    body_raw = m.group(1)
    if not _looks_like_math_expr(body_raw):
        return None
    body = spoken_expr_to_latex(body_raw)
    diff = m.group(2).lower() if m.group(2) else None
    suffix = rf"\,{diff}" if diff else ""
    ambig = bool(re.search(r"[+-]", body)) or diff is None
    return (rf"\int {body}{suffix}", ambig)


def _build_derivative_op(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    if m.group(2):
        # Spoken form: "de per de ex" or "de ye per de ex"
        num_var = _normalize_var(m.group(1)) if m.group(1) else ""
        den_var = _normalize_var(m.group(2))
    else:
        # Compact form: "d/dx" or "dy/dx" or "df per dx"
        num_var = m.group(3) or ""
        den_var = m.group(4) or "x"

    if len(den_var) != 1 or (num_var and len(num_var) != 1):
        return None

    expr_raw = m.group(5)
    frac = rf"\frac{{d{num_var}}}{{d{den_var}}}"
    if expr_raw and _looks_like_math_expr(expr_raw):
        body = spoken_expr_to_latex(expr_raw)
        return (rf"{frac}\left({body}\right)", bool(re.search(r"[+-]", body)))
    return (frac, False)


def _build_derivative_words(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    target_raw = m.group(1).strip()
    var = _normalize_var(m.group(2))
    if len(var) != 1 or not _looks_like_math_expr(target_raw):
        return None
    if re.fullmatch(r"[a-zA-Z]", target_raw):
        return (rf"\frac{{d{target_raw}}}{{d{var}}}", False)
    body = spoken_expr_to_latex(target_raw)
    return (rf"\frac{{d}}{{d{var}}}\left({body}\right)", bool(re.search(r"[+-]", body)))


def _build_prime(m: re.Match[str]) -> tuple[str, bool]:
    fn = m.group(1)
    kind = m.group(2).lower()
    arg = m.group(3)
    primes = "''" if ("double" in kind or "dobel" in kind) else "'"
    latex = f"{fn}{primes}({arg})" if arg else f"{fn}{primes}"
    return (latex, False)


def _build_equation(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    lhs_raw, op_raw, rhs_raw = m.group(1), m.group(2), m.group(3)
    if not (_looks_like_math_expr(lhs_raw) and _looks_like_math_expr(rhs_raw)):
        return None
    # Require at least one math symbol/variable/number on both sides (avoid plain text)
    if not re.search(rf"[0-9^√+\-*/{re.escape(SUP_CHARS)}]", lhs_raw + rhs_raw):
        return None
    op_map = {
        "=": "=",
        "sama dengan": "=",
        "equals": "=",
        "<=": r"\le",
        ">=": r"\ge",
        "!=": r"\neq",
    }
    op = op_map.get(re.sub(r"\s+", " ", op_raw.lower().strip()), "=")
    lhs = spoken_expr_to_latex(lhs_raw)
    rhs = spoken_expr_to_latex(rhs_raw)
    return (f"{lhs} {op} {rhs}", False)


def _build_fraction(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    num_raw = m.group(1).strip()
    prep = m.group(2).lower()
    den_raw = m.group(3).strip()
    if prep == "per" and (
        den_raw.lower() in NON_MATH_PER
        or (num_raw.lower() == "satu" and den_raw.lower() == "satu")
    ):
        return None
    if not (_looks_like_math_expr(num_raw) and _looks_like_math_expr(den_raw)):
        return None
    num_l = spoken_expr_to_latex(num_raw)
    den_l = spoken_expr_to_latex(den_raw)
    if len(num_l) > 22 or len(den_l) > 22:
        return None
    ambig = bool(re.search(r"[+-]", num_l)) or prep in ("per", "over")
    return (rf"\frac{{{num_l}}}{{{den_l}}}", ambig)


def _build_power(m: re.Match[str]) -> Optional[tuple[str, bool]]:
    base_raw = m.group(1).strip()
    if not _looks_like_math_expr(base_raw):
        return None
    base = spoken_expr_to_latex(base_raw)

    if m.group(2):  # kuadrat / squared / kubik / cubed
        kw = m.group(2).lower()
        return (f"{base}^2" if kw in ("kuadrat", "squared") else f"{base}^3", False)

    if m.group(3):  # ASCII caret "^ 5", "^3", "^ -2"
        exp_raw = m.group(3).lstrip("^").strip()
        exp_l = spoken_expr_to_latex(exp_raw)
        return (f"{base}{_fmt_exp(exp_l)}", False)

    if m.group(4):  # "pangkat 3", "pangkat 5", "to the power of n"
        exp_raw = re.sub(
            r"^(?:pangkat|to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?)\s+",
            "",
            m.group(4),
            flags=re.I,
        )
        exp_l = spoken_expr_to_latex(exp_raw)
        return (f"{base}{_fmt_exp(exp_l)}", bool(re.search(r"[+-]", exp_l)))

    return None


# ---------------------------------------------------------------------------
# 3. Unified Context & Math Refinement (Rule Engine + Google Gemini Flash API)
# ---------------------------------------------------------------------------

UNCLEAR_REGEX = re.compile(r"\[(?:unclear|inaudible|tidak\s+jelas)\]", re.I)


@dataclass
class RefinedCaption:
    raw_text: str
    processed_text: str
    segments: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[dict[str, Any]] = field(default_factory=list)
    glossary_matches: list[dict[str, Any]] = field(default_factory=list)
    is_unclear: bool = False
    refined_by: str = "rules"


def _run_rule_pipeline(
    raw_text: str,
    glossary: list[str],
    confidence: Optional[float] = None,
) -> RefinedCaption:
    cleaned = raw_text.strip()
    low_conf = confidence is not None and 0 < confidence < 0.45

    if not cleaned or (low_conf and len(cleaned.split()) <= 5):
        return RefinedCaption(
            raw_text=cleaned,
            processed_text="[unclear]",
            segments=[{"type": "unclear", "text": "[unclear]", "original_text": cleaned}],
            is_unclear=True,
            refined_by="rules",
        )

    chunks: list[tuple[str, str]] = []
    last_idx = 0
    has_unclear = low_conf
    for m in UNCLEAR_REGEX.finditer(cleaned):
        if m.start() > last_idx:
            chunks.append(("text", cleaned[last_idx : m.start()]))
        chunks.append(("unclear", "[unclear]"))
        has_unclear = True
        last_idx = m.end()
    if last_idx < len(cleaned):
        chunks.append(("text", cleaned[last_idx:]))

    segments: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    glossary_matches: list[dict[str, Any]] = []

    def emit_plain(plain: str) -> None:
        if not plain:
            return
        g_spans = find_glossary_spans(plain, glossary)
        if not g_spans:
            segments.append({"type": "text", "text": plain})
            return
        g_cur = 0
        for gs in g_spans:
            if gs.start > g_cur:
                segments.append({"type": "text", "text": plain[g_cur : gs.start]})
            segments.append(
                {
                    "type": "glossary",
                    "text": gs.matched_term,
                    "original": gs.original,
                    "matched_term": gs.matched_term,
                    "was_corrected": gs.was_corrected,
                }
            )
            glossary_matches.append(
                {
                    "original": gs.original,
                    "matched_term": gs.matched_term,
                    "was_corrected": gs.was_corrected,
                    "similarity": gs.similarity,
                }
            )
            g_cur = gs.end
        if g_cur < len(plain):
            segments.append({"type": "text", "text": plain[g_cur:]})

    for kind, value in chunks:
        if kind == "unclear":
            segments.append({"type": "unclear", "text": "[unclear]"})
            continue
        f_spans = find_formula_spans(value)
        cur = 0
        for fs in f_spans:
            if fs.start > cur:
                emit_plain(value[cur : fs.start])
            formulas.append(
                {
                    "original_text": fs.original_text,
                    "latex": fs.latex,
                    "ambiguous": fs.ambiguous,
                    "rule_name": fs.rule_name,
                }
            )
            segments.append(
                {
                    "type": "formula",
                    "original_text": fs.original_text,
                    "latex": fs.latex,
                    "ambiguous": fs.ambiguous,
                    "rule_name": fs.rule_name,
                }
            )
            cur = fs.end
        if cur < len(value):
            emit_plain(value[cur:])

    if low_conf and not any(k == "unclear" for k, _ in chunks):
        segments.append({"type": "text", "text": " "})
        segments.append({"type": "unclear", "text": "[unclear]"})

    processed = "".join(
        seg["text"]
        if seg["type"] == "text"
        else seg["matched_term"]
        if seg["type"] == "glossary"
        else f"{seg['original_text']} [{seg['latex']}]"
        if seg["type"] == "formula"
        else "[unclear]"
        for seg in segments
    )

    return RefinedCaption(
        raw_text=cleaned,
        processed_text=processed,
        segments=segments,
        formulas=formulas,
        glossary_matches=glossary_matches,
        is_unclear=has_unclear,
        refined_by="rules",
    )


def _refine_with_gemini(
    raw_text: str,
    course_title: str,
    topic: str,
    glossary: list[str],
    language: str,
) -> Optional[dict[str, Any]]:
    settings = get_settings()
    if not settings.is_gemini_configured:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        prompt = (
            "You are LectureLens Math & Context Refinement Engine.\n"
            f"Course: {course_title}\n"
            f"Topic: {topic}\n"
            f"Language: {language}\n"
            f"Session Glossary: {json.dumps(glossary, ensure_ascii=False)}\n"
            f"Spoken utterance: {json.dumps(raw_text, ensure_ascii=False)}\n\n"
            "Indonesian & English Spoken Math Examples:\n"
            '- "integral dari 5x²" -> latex: "\\\\int 5x^2"\n'
            '- "integral 2x ^ 5" -> latex: "\\\\int 2x^5"\n'
            '- "de per de ex" / "d per dx" -> latex: "\\\\frac{d}{dx}"\n'
            '- "de ye per de ex" -> latex: "\\\\frac{dy}{dx}"\n'
            '- "2x pangkat 5" / "5 x pangkat 3" -> latex: "2x^5" / "5x^3"\n'
            '- "akar dari x tambah satu" -> latex: "\\\\sqrt{x+1}" (ambiguous: true)\n'
            '- "f aksen x" -> latex: "f\'(x)"\n\n'
            "Rules:\n"
            "1. Fix near-miss technical terms ONLY against the glossary or obvious ASR typos.\n"
            "2. Identify any spoken or ASR-shorthand math phrases and return their exact "
            "substring `original_text`, clean KaTeX-compatible `latex`, and boolean `ambiguous`.\n"
            "3. NEVER invent facts or silently drop spoken words.\n"
            "Return strict JSON with keys:\n"
            '{"refined_text": str, "formulas": [{"original_text": str, "latex": str, "ambiguous": bool}], '
            '"glossary_fixes": [{"original": str, "matched_term": str}]}'
        )
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        if not response.text:
            return None
        return json.loads(response.text)
    except Exception as exc:
        logger.warning("Gemini Flash refinement skipped (falling back to rules): %s", exc)
        return None


def refine_caption(
    raw_text: str,
    course_title: str,
    topic: str,
    glossary: list[str],
    language: str = "id-ID",
    confidence: Optional[float] = None,
    use_gemini: bool = True,
) -> RefinedCaption:
    """
    Runs fast deterministic rule-based refinement, and enhances with Google Gemini Flash API
    when GEMINI_API_KEY is configured. Always preserves original spoken words alongside formulas.
    """
    baseline = _run_rule_pipeline(raw_text, glossary, confidence=confidence)
    if not use_gemini or baseline.is_unclear or not get_settings().is_gemini_configured:
        return baseline

    gem = _refine_with_gemini(raw_text, course_title, topic, glossary, language)
    if not gem or not isinstance(gem, dict):
        return baseline

    refined_text = str(gem.get("refined_text") or raw_text).strip()
    rebuilt = _run_rule_pipeline(refined_text, glossary, confidence=confidence)
    rebuilt.raw_text = raw_text.strip()
    rebuilt.refined_by = f"gemini ({get_settings().gemini_model})"

    existing_origs = {f["original_text"].lower() for f in rebuilt.formulas}
    extra_formulas = gem.get("formulas") or []
    for ef in extra_formulas:
        if not isinstance(ef, dict):
            continue
        orig = str(ef.get("original_text") or "").strip()
        latex = str(ef.get("latex") or "").strip()
        if orig and latex and orig.lower() not in existing_origs:
            rebuilt.formulas.append(
                {
                    "original_text": orig,
                    "latex": latex,
                    "ambiguous": bool(ef.get("ambiguous", True)),
                    "rule_name": "gemini-flash",
                }
            )
            rebuilt.segments.append(
                {
                    "type": "formula",
                    "original_text": orig,
                    "latex": latex,
                    "ambiguous": bool(ef.get("ambiguous", True)),
                    "rule_name": "gemini-flash",
                }
            )
            existing_origs.add(orig.lower())

    return rebuilt
