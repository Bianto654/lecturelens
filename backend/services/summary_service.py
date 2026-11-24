from __future__ import annotations

import logging
from backend.config import get_settings

logger = logging.getLogger(__name__)


def _fallback_grounded_summary(
    course_title: str,
    topic: str,
    glossary: list[str],
    captions: list[dict],
    language: str,
) -> str:
    is_id = language.startswith("id")
    formulas = [
        f
        for cap in captions
        for f in (cap.get("formulas") or [])
        if f.get("latex")
    ]
    matched_terms = list(
        dict.fromkeys(
            g["matched_term"]
            for cap in captions
            for g in (cap.get("glossary_matches") or [])
            if g.get("matched_term")
        )
    )

    lines: list[str] = []
    if is_id:
        lines.append(f"## Ringkasan Sesi: {course_title} — {topic}")
        lines.append(
            "> *Mode ringkasan ekstraktif lokal (tambahkan `GEMINI_API_KEY` di `.env` untuk ringkasan AI Google Gemini Flash).*"
        )
        lines.append("")
        lines.append("### Poin Utama dari Transkrip")
        for cap in captions[:8]:
            lines.append(f"- **[#{cap['seq']}]** {cap['processed_text']}")
        if formulas:
            lines.append("")
            lines.append("### Rumus yang Dibahas")
            for f in formulas:
                lines.append(f"- `{f['latex']}` *(dari: \"{f['original_text']}\")*")
        if matched_terms or glossary:
            lines.append("")
            lines.append("### Istilah Glosarium Terdeteksi")
            lines.append(", ".join(matched_terms or glossary))
    else:
        lines.append(f"## Session Summary: {course_title} — {topic}")
        lines.append(
            "> *Local extractive fallback (set `GEMINI_API_KEY` in `.env` for Google Gemini Flash grounded summarization).*"
        )
        lines.append("")
        lines.append("### Key Transcript Points")
        for cap in captions[:8]:
            lines.append(f"- **[#{cap['seq']}]** {cap['processed_text']}")
        if formulas:
            lines.append("")
            lines.append("### Formulas Mentioned")
            for f in formulas:
                lines.append(f"- `{f['latex']}` *(spoken: \"{f['original_text']}\")*")
        if matched_terms or glossary:
            lines.append("")
            lines.append("### Glossary Terms Covered")
            lines.append(", ".join(matched_terms or glossary))

    return "\n".join(lines)


def generate_grounded_summary(
    course_title: str,
    topic: str,
    glossary: list[str],
    captions: list[dict],
    language: str = "id-ID",
) -> tuple[str, str]:
    """
    Generates a transcript-grounded post-session summary using Google Gemini Flash API.
    Returns `(summary_markdown, provider_label)`.
    """
    if not captions:
        empty_msg = (
            "Transkrip masih kosong—belum ada materi yang dapat diringkas."
            if language.startswith("id")
            else "Transcript is empty—no lecture content to summarize yet."
        )
        return empty_msg, "empty"

    settings = get_settings()
    if not settings.is_gemini_configured:
        return (
            _fallback_grounded_summary(
                course_title, topic, glossary, captions, language
            ),
            "local-extractive",
        )

    transcript_lines = "\n".join(
        f"[#{c['seq']}] {c['processed_text']}" for c in captions
    )
    out_lang = "Indonesian" if language.startswith("id") else "English"

    prompt = (
        f"You are an academic note-taking assistant for LectureLens.\n"
        f"Write a concise, well-structured post-session study summary in {out_lang}.\n"
        f"Course: {course_title}\n"
        f"Topic: {topic}\n"
        f"Glossary: {', '.join(glossary) if glossary else '-'}\n\n"
        "STRICT GROUNDING RULES:\n"
        "- Base EVERY claim strictly on the transcript lines below. Do NOT hallucinate outside facts.\n"
        "- Cite segment numbers like [#3] for key points.\n"
        "- Include sections: 1) Overview, 2) Key Takeaways (bulleted with [#seq]), "
        "3) Key Formulas (in LaTeX `$...$`), 4) Glossary Terms Mentioned.\n\n"
        f"TRANSCRIPT:\n{transcript_lines}"
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        if resp.text and resp.text.strip():
            return resp.text.strip(), f"gemini ({settings.gemini_model})"
    except Exception as exc:
        logger.warning("Gemini summary failed, falling back to extractive: %s", exc)

    return (
        _fallback_grounded_summary(course_title, topic, glossary, captions, language),
        "local-extractive-fallback",
    )
