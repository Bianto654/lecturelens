from __future__ import annotations

import json
import random
import re
import threading
import time
from typing import Any, Optional

from sqlalchemy import func, select

from backend.config import get_settings
from backend.db import SessionLocal, init_db
from backend.models import (
    Bookmark,
    Course,
    GlossaryTerm,
    LectureSession,
    TranscriptSegment,
)
from backend.services.export_service import (
    build_docx_bytes,
    build_pdf_bytes,
    build_txt_bytes,
)
from backend.services.polish_service import (
    run_polish_for_session_threadsafe,
    trigger_background_polish_thread,
)
from backend.services.refinement_service import refine_caption
from backend.services.summary_service import generate_grounded_summary

_INIT_LOCK = threading.Lock()
_DB_READY = False
_PRESENCE_LOCK = threading.Lock()
# session_id -> {student_id: last_seen_ms}
_PRESENCE: dict[str, dict[str, int]] = {}
_PRESENCE_TTL_MS = 20_000


def _ensure_db() -> None:
    global _DB_READY
    if _DB_READY:
        return
    with _INIT_LOCK:
        if not _DB_READY:
            init_db()
            _DB_READY = True


def touch_student_presence(session_id: str, student_id: str) -> int:
    sid = session_id.upper()
    now = int(time.time() * 1000)
    with _PRESENCE_LOCK:
        room = _PRESENCE.setdefault(sid, {})
        room[student_id] = now
        stale = [k for k, ts in room.items() if now - ts > _PRESENCE_TTL_MS]
        for k in stale:
            room.pop(k, None)
        return len(room)


def get_student_count(session_id: str) -> int:
    sid = session_id.upper()
    now = int(time.time() * 1000)
    with _PRESENCE_LOCK:
        room = _PRESENCE.get(sid)
        if not room:
            return 0
        stale = [k for k, ts in room.items() if now - ts > _PRESENCE_TTL_MS]
        for k in stale:
            room.pop(k, None)
        return len(room)


def _generate_room_code(course_title: str) -> str:
    prefix = re.sub(r"[^A-Z]", "", course_title.upper())[:4].ljust(4, "L")
    return f"{prefix}-{random.randint(1000, 9999)}"


def _serialize_session(db, s: LectureSession) -> dict[str, Any]:
    glossary = [g.term for g in s.glossaries]
    cap_count = (
        db.scalar(
            select(func.count(TranscriptSegment.id)).where(
                TranscriptSegment.session_id == s.id
            )
        )
        or 0
    )
    return {
        "id": s.id,
        "course_id": s.course_id,
        "course_title": s.course_title,
        "topic": s.topic,
        "date": s.date,
        "status": s.status,
        "language": s.language,
        "glossary": glossary,
        "summary_md": s.summary_md,
        "polished_transcript_md": s.polished_transcript_md,
        "polish_status": s.polish_status or "idle",
        "polish_provider": s.polish_provider,
        "caption_count": cap_count,
        "student_count": get_student_count(s.id),
        "created_at": s.created_at,
        "ended_at": s.ended_at,
    }


def _serialize_caption(row: TranscriptSegment) -> dict[str, Any]:
    return {
        "seq": row.seq,
        "session_id": row.session_id,
        "timestamp_ms": row.timestamp_ms,
        "raw_text": row.raw_text,
        "processed_text": row.processed_text,
        "segments": json.loads(row.segments_json or "[]"),
        "formulas": json.loads(row.formulas_json or "[]"),
        "glossary_matches": json.loads(row.glossary_matches_json or "[]"),
        "is_unclear": row.is_unclear,
        "confidence": row.confidence,
        "language": row.language,
        "refined_by": row.refined_by,
    }


class EmbeddedLectureLensAPI:
    """
    In-process backend adapter for single-app Streamlit Community Cloud deployment
    (zero credit card / no separate Render backend required).
    Uses the exact same SQLAlchemy models (Supabase PostgreSQL or SQLite),
    Gemini Flash refinement/summary, and python-docx / ReportLab export pipeline.
    """

    is_embedded = True

    def __init__(self) -> None:
        _ensure_db()

    def health(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "ok": True,
            "mode": "embedded",
            "database": "supabase-postgresql" if settings.is_postgres else "sqlite-local",
            "gemini_configured": settings.is_gemini_configured,
            "gemini_model": settings.gemini_model,
            "stt": {
                "library_installed": False,
                "model_size": "cloud-embedded",
                "silero_vad": False,
            },
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(LectureSession).order_by(LectureSession.created_at.desc()).limit(50)
            ).all()
            return [_serialize_session(db, s) for s in rows]

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        with SessionLocal() as db:
            course_title = str(payload["course_title"]).strip()
            raw_code = payload.get("course_code")
            course_code = (
                str(raw_code).strip().upper()
                if raw_code and str(raw_code).strip()
                else re.sub(r"[^A-Z0-9]", "", course_title.upper())[:10] or "COURSE"
            )
            course = db.scalar(select(Course).where(Course.code == course_code))
            if not course:
                course = Course(code=course_code, title=course_title)
                db.add(course)
                db.flush()

            room_id = _generate_room_code(course_title)
            while db.get(LectureSession, room_id) is not None:
                room_id = _generate_room_code(course_title)

            sess = LectureSession(
                id=room_id,
                course_id=course.id,
                course_title=course_title,
                topic=str(payload["topic"]).strip(),
                date=str(payload["date"]).strip(),
                status="live",
                language=str(payload.get("language") or "id-ID"),
            )
            db.add(sess)
            db.flush()

            seen: set[str] = set()
            for raw_term in payload.get("glossary") or []:
                term = str(raw_term).strip()
                if term and term.lower() not in seen:
                    seen.add(term.lower())
                    db.add(GlossaryTerm(session_id=sess.id, term=term))

            db.commit()
            db.refresh(sess)
            return _serialize_session(db, sess)

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        with SessionLocal() as db:
            sess = db.get(LectureSession, session_id.upper())
            if not sess:
                return None
            return _serialize_session(db, sess)

    def patch_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        sid = session_id.upper()
        should_polish = False
        with SessionLocal() as db:
            sess = db.get(LectureSession, sid)
            if not sess:
                raise ValueError("Session not found")
            if payload.get("status"):
                sess.status = payload["status"]
                if payload["status"] == "ended":
                    sess.ended_at = int(time.time() * 1000)
                    cap_count = (
                        db.scalar(
                            select(func.count(TranscriptSegment.id)).where(
                                TranscriptSegment.session_id == sid
                            )
                        )
                        or 0
                    )
                    if cap_count > 0:
                        sess.polish_status = "processing"
                        should_polish = True
            if payload.get("language"):
                sess.language = payload["language"]
            db.commit()
            db.refresh(sess)
            serialized = _serialize_session(db, sess)
        if should_polish:
            trigger_background_polish_thread(sid)
        return serialized

    def delete_session(self, session_id: str) -> None:
        with SessionLocal() as db:
            sess = db.get(LectureSession, session_id.upper())
            if sess:
                db.delete(sess)
                db.commit()

    def list_captions(self, session_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.session_id == session_id.upper())
                .order_by(TranscriptSegment.seq.asc())
            ).all()
            return [_serialize_caption(r) for r in rows]

    def submit_caption(
        self, session_id: str, raw_text: str, confidence: float = 0.95
    ) -> dict[str, Any]:
        with SessionLocal() as db:
            sess = db.get(LectureSession, session_id.upper())
            if not sess:
                raise ValueError("Session not found")
            glossary = [g.term for g in sess.glossaries]
            refined = refine_caption(
                raw_text=raw_text,
                course_title=sess.course_title,
                topic=sess.topic,
                glossary=glossary,
                language=sess.language,
                confidence=confidence,
                use_gemini=True,
            )
            max_seq = (
                db.scalar(
                    select(func.max(TranscriptSegment.seq)).where(
                        TranscriptSegment.session_id == sess.id
                    )
                )
                or 0
            )
            row = TranscriptSegment(
                session_id=sess.id,
                seq=max_seq + 1,
                timestamp_ms=int(time.time() * 1000),
                raw_text=refined.raw_text,
                processed_text=refined.processed_text,
                segments_json=json.dumps(refined.segments, ensure_ascii=False),
                formulas_json=json.dumps(refined.formulas, ensure_ascii=False),
                glossary_matches_json=json.dumps(
                    refined.glossary_matches, ensure_ascii=False
                ),
                is_unclear=refined.is_unclear,
                confidence=confidence,
                language=sess.language,
                refined_by=refined.refined_by,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _serialize_caption(row)

    def transcribe_audio_file(
        self,
        session_id: str,
        filename: str,
        data: bytes,
        content_type: str,
        language: str,
    ) -> list[dict[str, Any]]:
        """
        In embedded cloud mode, uses Google Gemini Flash multimodal audio transcription
        when GEMINI_API_KEY is configured (or Faster-Whisper if installed locally).
        """
        settings = get_settings()
        sess = self.get_session(session_id)
        if not sess:
            raise ValueError("Session not found")

        # 1. Prefer Google Gemini Flash native audio transcription if API key is configured
        if settings.is_gemini_configured:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key.strip())
            lang_name = "Indonesian" if language.startswith("id") else "English"
            glossary_str = ", ".join(sess["glossary"]) or "-"
            prompt = (
                f"Transcribe this university lecture audio accurately in {lang_name}.\n"
                f"Course: {sess['course_title']} | Topic: {sess['topic']}\n"
                f"Important glossary terms: {glossary_str}\n"
                "Return one spoken sentence per line, plain text only, keeping spoken math intact. "
                "Mark genuinely unintelligible speech as [unclear]."
            )
            mime = content_type or "audio/wav"
            resp = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=data, mime_type=mime),
                    prompt,
                ],
            )
            text = (resp.text or "").strip()
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            return [self.submit_caption(session_id, ln, confidence=0.92) for ln in lines]

        # 2. Fallback to local Faster-Whisper if installed
        from backend.services.stt_service import stt_service

        if stt_service.is_available:
            items = stt_service.transcribe_file(
                data,
                filename,
                language,
                sess["course_title"],
                sess["topic"],
                sess["glossary"],
            )
            return [
                self.submit_caption(session_id, it.text, confidence=it.confidence)
                for it in items
            ]

        raise RuntimeError(
            "Tambahkan GEMINI_API_KEY di Streamlit Secrets (gratis di aistudio.google.com/apikey) "
            "untuk mentranskripsi file audio / rekaman mikrofon langsung di Streamlit Cloud."
        )

    def list_bookmarks(self, session_id: str, student_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(Bookmark)
                .where(
                    Bookmark.session_id == session_id.upper(),
                    Bookmark.student_id == student_id,
                )
                .order_by(Bookmark.transcript_seq.asc())
            ).all()
            return [
                {
                    "id": b.id,
                    "session_id": b.session_id,
                    "transcript_seq": b.transcript_seq,
                    "student_id": b.student_id,
                    "note": b.note,
                    "created_at": b.created_at,
                }
                for b in rows
            ]

    def upsert_bookmark(
        self, session_id: str, seq: int, student_id: str, note: str = ""
    ) -> dict[str, Any]:
        sid = session_id.upper()
        with SessionLocal() as db:
            existing = db.scalar(
                select(Bookmark).where(
                    Bookmark.session_id == sid,
                    Bookmark.transcript_seq == seq,
                    Bookmark.student_id == student_id,
                )
            )
            if existing:
                existing.note = note.strip()
                db.commit()
                db.refresh(existing)
                b = existing
            else:
                b = Bookmark(
                    session_id=sid,
                    transcript_seq=seq,
                    student_id=student_id,
                    note=note.strip(),
                )
                db.add(b)
                db.commit()
                db.refresh(b)
            return {
                "id": b.id,
                "session_id": b.session_id,
                "transcript_seq": b.transcript_seq,
                "student_id": b.student_id,
                "note": b.note,
                "created_at": b.created_at,
            }

    def delete_bookmark(self, session_id: str, seq: int, student_id: str) -> None:
        with SessionLocal() as db:
            existing = db.scalar(
                select(Bookmark).where(
                    Bookmark.session_id == session_id.upper(),
                    Bookmark.transcript_seq == seq,
                    Bookmark.student_id == student_id,
                )
            )
            if existing:
                db.delete(existing)
                db.commit()

    def generate_summary(self, session_id: str) -> dict[str, Any]:
        sess = self.get_session(session_id)
        if not sess:
            raise ValueError("Session not found")
        captions = self.list_captions(session_id)
        summary_md, provider = generate_grounded_summary(
            sess["course_title"],
            sess["topic"],
            sess["glossary"],
            captions,
            sess["language"],
        )
        with SessionLocal() as db:
            row = db.get(LectureSession, session_id.upper())
            if row:
                row.summary_md = summary_md
                db.commit()
        return {
            "session_id": session_id.upper(),
            "summary_md": summary_md,
            "provider": provider,
        }

    def polish_transcript(self, session_id: str, wait: bool = True) -> dict[str, Any]:
        sid = session_id.upper()
        sess = self.get_session(sid)
        if not sess:
            raise ValueError("Session not found")
        if sess.get("caption_count", 0) == 0:
            return {
                "session_id": sid,
                "polish_status": "idle",
                "polished_transcript_md": sess.get("polished_transcript_md"),
                "provider": sess.get("polish_provider"),
            }
        if not wait:
            with SessionLocal() as db:
                row = db.get(LectureSession, sid)
                if row:
                    row.polish_status = "processing"
                    db.commit()
            trigger_background_polish_thread(sid)
            return {
                "session_id": sid,
                "polish_status": "processing",
                "polished_transcript_md": sess.get("polished_transcript_md"),
                "provider": sess.get("polish_provider"),
            }
        res = run_polish_for_session_threadsafe(sid)
        if not res:
            raise ValueError("Session not found")
        return res

    def download_export(self, session_id: str, fmt: str) -> bytes:
        sess = self.get_session(session_id)
        if not sess:
            raise ValueError("Session not found")
        captions = self.list_captions(session_id)
        if captions and not sess.get("polished_transcript_md"):
            run_polish_for_session_threadsafe(session_id)
            sess = self.get_session(session_id) or sess
        if fmt == "docx":
            return build_docx_bytes(sess, captions)
        if fmt == "pdf":
            return build_pdf_bytes(sess, captions)
        return build_txt_bytes(sess, captions)
