from __future__ import annotations

import logging
import re
import threading
from typing import Optional

from sqlalchemy import select

from backend.config import get_settings
from backend.db import SessionLocal
from backend.models import LectureSession, TranscriptSegment

logger = logging.getLogger(__name__)

# Per-session lock so ending a session or double-clicking never runs duplicate polish passes concurrently
_POLISH_LOCKS_GUARD = threading.Lock()
_POLISH_LOCKS: dict[str, threading.Lock] = {}


def _get_session_lock(session_id: str) -> threading.Lock:
    sid = session_id.upper()
    with _POLISH_LOCKS_GUARD:
        lock = _POLISH_LOCKS.get(sid)
        if lock is None:
            lock = threading.Lock()
            _POLISH_LOCKS[sid] = lock
        return lock


# ---------------------------------------------------------------------------
# Disfluency & Filler Cleanup + Paragraph Stitching (Local Deterministic Engine)
# ---------------------------------------------------------------------------

# Spoken fillers in Indonesian and English lectures (only matched as standalone tokens/phrases)
_FILLER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\b(?:e+h+|e+m+|e+e+e+|u+m+|u+h+|h+m+|a+n+u+|y+a+h+|o+k+e+y?\s+jadi\s+gini)\b[,.]*",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:you\s+know|i\s+mean|sort\s+of\s+like|kind\s+of\s+like)\b[,.]*", re.IGNORECASE),
    re.compile(r"\b(?:gitu\s+(?:ya|lho|kan|deh)|apa\s+namanya|gimana\s+ya)\b[,.]*", re.IGNORECASE),
]

# Repeated stuttered words like "jadi jadi", "yang yang", "the the", "kita kita"
_STUTTER_RE = re.compile(r"\b([A-Za-zÀ-ÿ]{2,})(?:\s*,?\s+\1)+\b", re.IGNORECASE)

# Continuation starters that indicate a choppy fragment belongs to the previous sentence
_CONTINUATION_STARTERS = {
    "dan",
    "atau",
    "lalu",
    "terus",
    "kemudian",
    "yang",
    "karena",
    "sehingga",
    "tetapi",
    "tapi",
    "namun",
    "jadi",
    "maka",
    "dengan",
    "untuk",
    "pada",
    "di",
    "ke",
    "dari",
    "adalah",
    "itu",
    "ini",
    "and",
    "or",
    "then",
    "which",
    "that",
    "because",
    "so",
    "but",
    "however",
    "with",
    "for",
    "where",
    "while",
}

# Topic shift markers that naturally start a new academic paragraph
_TOPIC_SHIFT_PREFIXES = (
    "selanjutnya",
    "berikutnya",
    "sekarang kita",
    "kedua",
    "ketiga",
    "keempat",
    "terakhir",
    "kesimpulannya",
    "jadi kesimpulannya",
    "contoh",
    "misalnya",
    "perhatikan",
    "next",
    "now let",
    "second",
    "third",
    "finally",
    "in conclusion",
    "to summarize",
    "for example",
    "consider",
)


def strip_disfluencies(text: str) -> str:
    """Removes oral fillers, stutters, and messy whitespace while preserving technical content."""
    cleaned = text.strip()
    if not cleaned:
        return ""
    for pat in _FILLER_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    cleaned = _STUTTER_RE.sub(r"\1", cleaned)
    # Clean stray leading/repeated punctuation left after removing fillers
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"([,.;:!?]){2,}", r"\1", cleaned)
    cleaned = re.sub(r"^[,.;:\-\s]+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def _render_caption_with_inline_math(cap: dict) -> str:
    """
    Reconstructs a clean sentence from a refined caption dict, embedding formulas as
    clean inline LaTeX `$...$` and bolding verified glossary terms.
    """
    segments = cap.get("segments") or []
    if not segments:
        return strip_disfluencies(str(cap.get("processed_text") or cap.get("raw_text") or ""))

    parts: list[str] = []
    for seg in segments:
        stype = seg.get("type")
        if stype == "text":
            txt = strip_disfluencies(str(seg.get("text") or ""))
            if txt:
                parts.append(txt)
        elif stype == "glossary":
            term = str(seg.get("matched_term") or seg.get("text") or "").strip()
            if term:
                parts.append(f"**{term}**")
        elif stype == "formula":
            latex = str(seg.get("latex") or "").strip()
            if latex:
                parts.append(f"${latex}$")
        elif stype == "unclear":
            parts.append("[unclear]")

    joined = " ".join(parts)
    joined = re.sub(r"\s+([,.;:!?])", r"\1", joined)
    joined = re.sub(r"\s{2,}", " ", joined).strip()
    return joined


def _ensure_sentence_case_and_period(sentence: str) -> str:
    s = sentence.strip()
    if not s:
        return ""
    # Capitalize the first alphabetic character if it's not inside LaTeX or bold markup
    if s[0].islower():
        s = s[0].upper() + s[1:]
    if s[-1] not in ".!?":
        s += "."
    return s


def _polish_local_fallback(
    course_title: str,
    topic: str,
    glossary: list[str],
    captions: list[dict],
    language: str,
) -> str:
    """
    Deterministic local academic editor when GEMINI_API_KEY is not configured.
    Strips oral fillers, stitches fragmented utterances into full sentences,
    groups sentences into cohesive academic paragraphs, and compiles formulas.
    """
    is_id = language.startswith("id")
    stitched_sentences: list[tuple[int, str]] = []  # (timestamp_ms, sentence)

    for cap in captions:
        if cap.get("is_unclear") and str(cap.get("processed_text", "")).strip() == "[unclear]":
            continue
        cleaned = _render_caption_with_inline_math(cap)
        if not cleaned or cleaned == "[unclear]":
            continue

        ts = int(cap.get("timestamp_ms") or 0)
        words = cleaned.split()
        first_word_plain = re.sub(r"[^A-Za-zÀ-ÿ]", "", words[0]).lower() if words else ""

        # Decide whether to stitch this fragment into the previous sentence
        should_stitch = False
        if stitched_sentences:
            prev_ts, prev_text = stitched_sentences[-1]
            gap_ms = abs(ts - prev_ts) if (ts and prev_ts) else 0
            prev_ended = prev_text.endswith((".", "!", "?"))
            prev_short = len(prev_text.split()) < 10
            curr_short = len(words) <= 6
            if gap_ms <= 12_000 and (
                (not prev_ended and (first_word_plain in _CONTINUATION_STARTERS or cleaned[0].islower()))
                or (prev_short and curr_short and not prev_ended)
            ):
                should_stitch = True

        if should_stitch:
            prev_ts, prev_text = stitched_sentences[-1]
            sep = " " if not prev_text.endswith(",") else " "
            merged = f"{prev_text.rstrip('. ')}{sep}{cleaned}"
            stitched_sentences[-1] = (ts or prev_ts, merged)
        else:
            stitched_sentences.append((ts, cleaned))

    if not stitched_sentences:
        return (
            "Belum ada materi transkrip yang dapat dirapikan."
            if is_id
            else "No transcript content available to polish yet."
        )

    # Group stitched sentences into cohesive academic paragraphs
    paragraphs: list[str] = []
    current_para: list[str] = []
    prev_ts = stitched_sentences[0][0]

    for ts, raw_sent in stitched_sentences:
        sent = _ensure_sentence_case_and_period(raw_sent)
        lower_plain = re.sub(r"^\*+", "", sent).lower()
        gap_ms = abs(ts - prev_ts) if (ts and prev_ts) else 0
        is_topic_shift = any(lower_plain.startswith(p) for p in _TOPIC_SHIFT_PREFIXES)

        if current_para and (len(current_para) >= 3 or gap_ms >= 25_000 or is_topic_shift):
            paragraphs.append(" ".join(current_para))
            current_para = [sent]
        else:
            current_para.append(sent)
        prev_ts = ts

    if current_para:
        paragraphs.append(" ".join(current_para))

    formulas = list(
        dict.fromkeys(
            (str(f.get("latex", "")).strip(), str(f.get("original_text", "")).strip())
            for cap in captions
            for f in (cap.get("formulas") or [])
            if str(f.get("latex", "")).strip()
        )
    )

    lines: list[str] = []
    if is_id:
        lines.append(f"## Panduan Belajar: {course_title} — {topic}")
        lines.append(
            "> *Dirapikan otomatis oleh Local Academic Editor (filler & fragmen disatukan menjadi paragraf utuh; tambahkan `GEMINI_API_KEY` untuk penyuntingan mendalam Google Gemini Flash).*"
        )
        lines.append("")
        for idx, para in enumerate(paragraphs, start=1):
            if len(paragraphs) > 1:
                lines.append(f"### Bagian {idx}")
            lines.append(para)
            lines.append("")
        if formulas:
            lines.append("### Ringkasan Rumus Matematika")
            for latex, orig in formulas:
                lines.append(f"- ${latex}$ *(diucapkan: \"{orig}\")*")
    else:
        lines.append(f"## Study Guide: {course_title} — {topic}")
        lines.append(
            "> *Refined by the Local Academic Editor (oral fillers stripped and choppy fragments stitched into cohesive paragraphs; configure `GEMINI_API_KEY` for deeper Google Gemini Flash rewriting).*"
        )
        lines.append("")
        for idx, para in enumerate(paragraphs, start=1):
            if len(paragraphs) > 1:
                lines.append(f"### Section {idx}")
            lines.append(para)
            lines.append("")
        if formulas:
            lines.append("### Key Mathematical Formulas")
            for latex, orig in formulas:
                lines.append(f"- ${latex}$ *(spoken: \"{orig}\")*")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Contextual Windowing + Gemini Flash Post-Session Academic Editor
# ---------------------------------------------------------------------------


def _build_windowed_chunks(captions: list[dict], max_chars: int = 10_000) -> list[str]:
    """Splits a long lecture transcript into manageable contextual windows."""
    windows: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for cap in captions:
        text = str(cap.get("processed_text") or cap.get("raw_text") or "").strip()
        if not text:
            continue
        formulas = cap.get("formulas") or []
        formula_note = ""
        if formulas:
            f_list = "; ".join(
                f'"{f.get("original_text", "")}" -> ${f.get("latex", "")}$'
                for f in formulas
                if f.get("latex")
            )
            if f_list:
                formula_note = f" [Formulas: {f_list}]"
        line = f"[#{cap['seq']}] {text}{formula_note}"

        if current_lines and current_len + len(line) + 1 > max_chars:
            windows.append("\n".join(current_lines))
            current_lines = [line]
            current_len = len(line)
        else:
            current_lines.append(line)
            current_len += len(line) + 1

    if current_lines:
        windows.append("\n".join(current_lines))
    return windows


def polish_lecture_transcript(
    course_title: str,
    topic: str,
    glossary: list[str],
    captions: list[dict],
    language: str = "id-ID",
) -> tuple[str, str]:
    """
    Post-session academic refinement pass:
    Converts choppy raw STT segments into cohesive, study-guide-ready academic paragraphs
    with filler removal, course glossary grounding, and clean LaTeX math formatting.

    Returns `(polished_markdown, provider_label)`.
    """
    if not captions:
        empty_msg = (
            "Transkrip masih kosong—belum ada materi yang dapat dirapikan."
            if language.startswith("id")
            else "Transcript is empty—no lecture content to polish yet."
        )
        return empty_msg, "empty"

    settings = get_settings()
    if not settings.is_gemini_configured:
        return (
            _polish_local_fallback(course_title, topic, glossary, captions, language),
            "local-academic-editor",
        )

    out_lang = "Indonesian" if language.startswith("id") else "English"
    glossary_str = ", ".join(glossary) if glossary else "-"
    windows = _build_windowed_chunks(captions, max_chars=10_000)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        polished_parts: list[str] = []

        for idx, chunk in enumerate(windows, start=1):
            part_hint = (
                f" (Part {idx} of {len(windows)})" if len(windows) > 1 else ""
            )
            prompt = (
                "You are an expert academic editor preparing a clean university study guide.\n"
                f"Rewrite the raw, unedited lecture transcript below in {out_lang} into clean, "
                "well-structured, coherent academic paragraphs suitable for a PDF/DOCX study guide.\n\n"
                f"Course: {course_title}\n"
                f"Topic: {topic}{part_hint}\n"
                f"Course Glossary: {glossary_str}\n\n"
                "STRICT EDITING & GROUNDING RULES:\n"
                "1. Convert choppy fragments and speaker pauses into cohesive paragraphs with clear topic sentences and concise markdown subheadings (`### Subheading`).\n"
                "2. Eliminate oral disfluencies, fillers ('um', 'uh', 'eh', 'anu', 'emm'), false starts, and accidental word repetitions while preserving 100% of the lecturer's technical meaning.\n"
                "3. Cross-reference technical terminology against the Course Glossary and bold key glossary terms (e.g., **Integral Riemann**).\n"
                "4. Format mathematical expressions and variables cleanly using inline `$...$` or display `$$...$$` LaTeX.\n"
                "5. NEVER hallucinate or add outside facts, proofs, or numbers not grounded in the raw transcript.\n"
                "6. Return clean Markdown only (no outer code fences).\n\n"
                f"Raw Transcript:\n{chunk}"
            )
            resp = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            if resp.text and resp.text.strip():
                polished_parts.append(resp.text.strip())

        if polished_parts:
            header = (
                f"## Panduan Belajar: {course_title} — {topic}\n\n"
                if language.startswith("id")
                else f"## Study Guide: {course_title} — {topic}\n\n"
            )
            body = "\n\n".join(polished_parts)
            # Avoid duplicating top-level title if Gemini already produced one
            if body.startswith("#"):
                return body, f"gemini ({settings.gemini_model})"
            return header + body, f"gemini ({settings.gemini_model})"
    except Exception as exc:
        logger.warning("Gemini transcript polish failed, falling back to local editor: %s", exc)

    return (
        _polish_local_fallback(course_title, topic, glossary, captions, language),
        "local-academic-editor-fallback",
    )


# ---------------------------------------------------------------------------
# Thread-Safe Persistence & Async Background Worker
# ---------------------------------------------------------------------------


def _load_captions_dicts(db, session_id: str) -> list[dict]:
    import json

    rows = db.scalars(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.seq.asc())
    ).all()
    return [
        {
            "seq": r.seq,
            "timestamp_ms": r.timestamp_ms,
            "raw_text": r.raw_text,
            "processed_text": r.processed_text,
            "segments": json.loads(r.segments_json or "[]"),
            "formulas": json.loads(r.formulas_json or "[]"),
            "glossary_matches": json.loads(r.glossary_matches_json or "[]"),
            "is_unclear": r.is_unclear,
            "confidence": r.confidence,
            "language": r.language,
            "refined_by": r.refined_by,
        }
        for r in rows
    ]


def run_polish_for_session_threadsafe(session_id: str) -> Optional[dict]:
    """
    Runs the post-session academic polish pass using an isolated SQLAlchemy session.
    Safe to execute inside `asyncio.to_thread(...)` or a daemon `threading.Thread`.
    Returns `{session_id, polish_status, polished_transcript_md, provider}` or `None` if not found.
    """
    sid = session_id.upper()
    lock = _get_session_lock(sid)
    with lock:
        with SessionLocal() as db:
            sess = db.get(LectureSession, sid)
            if not sess:
                return None
            course_title = sess.course_title
            topic = sess.topic
            language = sess.language
            glossary = [g.term for g in sess.glossaries]
            captions = _load_captions_dicts(db, sid)

            if not captions:
                sess.polish_status = "idle"
                db.commit()
                return {
                    "session_id": sid,
                    "polish_status": "idle",
                    "polished_transcript_md": sess.polished_transcript_md,
                    "provider": sess.polish_provider,
                }

            sess.polish_status = "processing"
            db.commit()

        try:
            polished_md, provider = polish_lecture_transcript(
                course_title=course_title,
                topic=topic,
                glossary=glossary,
                captions=captions,
                language=language,
            )
        except Exception as exc:
            logger.exception("Post-session polish crashed for %s: %s", sid, exc)
            with SessionLocal() as db:
                sess = db.get(LectureSession, sid)
                if sess:
                    sess.polish_status = "failed"
                    db.commit()
            return {
                "session_id": sid,
                "polish_status": "failed",
                "polished_transcript_md": None,
                "provider": None,
            }

        with SessionLocal() as db:
            sess = db.get(LectureSession, sid)
            if not sess:
                return None
            sess.polished_transcript_md = polished_md
            sess.polish_status = "ready"
            sess.polish_provider = provider
            db.commit()
            return {
                "session_id": sid,
                "polish_status": "ready",
                "polished_transcript_md": polished_md,
                "provider": provider,
            }


def trigger_background_polish_thread(session_id: str) -> threading.Thread:
    """Fires a non-blocking daemon thread to polish the session transcript asynchronously."""
    t = threading.Thread(
        target=run_polish_for_session_threadsafe,
        args=(session_id.upper(),),
        name=f"polish-{session_id.upper()}",
        daemon=True,
    )
    t.start()
    return t
