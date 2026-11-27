from __future__ import annotations

import asyncio
import json
import random
import re
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import SessionLocal, get_db, init_db
from backend.models import (
    Course,
    GlossaryTerm,
    LectureSession,
    TranscriptSegment,
)
from backend.schemas import (
    CaptionOut,
    CaptionSubmit,
    CourseCreate,
    CourseOut,
    FormulaAnnotation,
    GlossaryAnnotation,
    PolishResponse,
    SessionCreate,
    SessionOut,
    SessionPatch,
    SummaryResponse,
)
from backend.services.export_service import (
    build_docx_bytes,
    build_pdf_bytes,
    build_txt_bytes,
)
from backend.services.polish_service import run_polish_for_session_threadsafe
from backend.services.refinement_service import refine_caption
from backend.services.stt_service import stt_service
from backend.services.summary_service import generate_grounded_summary
from backend.ws_manager import ws_manager

_BACKGROUND_TASKS: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LectureLens API",
    description=(
        "FastAPI + WebSockets backend for LectureLens with Supabase PostgreSQL, "
        "Faster-Whisper (large-v3-turbo) + Silero VAD, Google Gemini Flash refinement & summary, "
        "and python-docx / ReportLab exports."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Serializers & Helpers
# ---------------------------------------------------------------------------


def _generate_room_code(course_title: str) -> str:
    prefix = re.sub(r"[^A-Z]", "", course_title.upper())[:4].ljust(4, "L")
    return f"{prefix}-{random.randint(1000, 9999)}"


def _serialize_session(db: Session, s: LectureSession) -> SessionOut:
    glossary = [g.term for g in s.glossaries]
    cap_count = (
        db.scalar(
            select(func.count(TranscriptSegment.id)).where(
                TranscriptSegment.session_id == s.id
            )
        )
        or 0
    )
    return SessionOut(
        id=s.id,
        course_id=s.course_id,
        course_title=s.course_title,
        topic=s.topic,
        date=s.date,
        status=s.status,  # type: ignore[arg-type]
        language=s.language,  # type: ignore[arg-type]
        glossary=glossary,
        summary_md=s.summary_md,
        polished_transcript_md=s.polished_transcript_md,
        polish_status=(s.polish_status or "idle"),  # type: ignore[arg-type]
        polish_provider=s.polish_provider,
        caption_count=cap_count,
        student_count=ws_manager.student_count(s.id),
        created_at=s.created_at,
        ended_at=s.ended_at,
    )


async def _async_polish_and_broadcast(session_id: str) -> None:
    """Runs post-session academic transcript polish off the event loop and broadcasts update."""
    sid = session_id.upper()
    await asyncio.to_thread(run_polish_for_session_threadsafe, sid)
    with SessionLocal() as db:
        sess = db.get(LectureSession, sid)
        if sess:
            out = _serialize_session(db, sess)
            await ws_manager.broadcast(
                sid, {"type": "session_update", "session": out.model_dump()}
            )


def _schedule_async_polish(session_id: str) -> None:
    task = asyncio.create_task(_async_polish_and_broadcast(session_id.upper()))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


def _serialize_caption(row: TranscriptSegment) -> CaptionOut:
    segments = json.loads(row.segments_json or "[]")
    formulas = [FormulaAnnotation(**f) for f in json.loads(row.formulas_json or "[]")]
    glossary_matches = [
        GlossaryAnnotation(**g)
        for g in json.loads(row.glossary_matches_json or "[]")
    ]
    return CaptionOut(
        seq=row.seq,
        session_id=row.session_id,
        timestamp_ms=row.timestamp_ms,
        raw_text=row.raw_text,
        processed_text=row.processed_text,
        segments=segments,
        formulas=formulas,
        glossary_matches=glossary_matches,
        is_unclear=row.is_unclear,
        confidence=row.confidence,
        language=row.language,  # type: ignore[arg-type]
        refined_by=row.refined_by,
    )


def _save_refined_caption(
    db: Session,
    session_obj: LectureSession,
    raw_text: str,
    confidence: Optional[float] = 0.95,
    language: Optional[str] = None,
    use_gemini: bool = True,
) -> CaptionOut:
    lang = language or session_obj.language
    glossary = [g.term for g in session_obj.glossaries]

    refined = refine_caption(
        raw_text=raw_text,
        course_title=session_obj.course_title,
        topic=session_obj.topic,
        glossary=glossary,
        language=lang,
        confidence=confidence,
        use_gemini=use_gemini,
    )

    max_seq = (
        db.scalar(
            select(func.max(TranscriptSegment.seq)).where(
                TranscriptSegment.session_id == session_obj.id
            )
        )
        or 0
    )
    row = TranscriptSegment(
        session_id=session_obj.id,
        seq=max_seq + 1,
        timestamp_ms=int(time.time() * 1000),
        raw_text=refined.raw_text,
        processed_text=refined.processed_text,
        segments_json=json.dumps(refined.segments, ensure_ascii=False),
        formulas_json=json.dumps(refined.formulas, ensure_ascii=False),
        glossary_matches_json=json.dumps(refined.glossary_matches, ensure_ascii=False),
        is_unclear=refined.is_unclear,
        confidence=confidence,
        language=lang,
        refined_by=refined.refined_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_caption(row)


def _save_refined_caption_threadsafe(
    session_id: str,
    raw_text: str,
    confidence: Optional[float] = 0.95,
    language: Optional[str] = None,
    use_gemini: bool = True,
) -> Optional[CaptionOut]:
    """Opens and closes its own SQLAlchemy Session inside the worker thread."""
    with SessionLocal() as db:
        session_obj = db.get(LectureSession, session_id)
        if not session_obj:
            return None
        return _save_refined_caption(
            db,
            session_obj,
            raw_text,
            confidence=confidence,
            language=language,
            use_gemini=use_gemini,
        )


def _safe_filename(s: LectureSession, ext: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{s.course_title}-{s.topic}".lower()).strip("-")[:48]
    return f"lecturelens-{slug or s.id.lower()}-{s.date}.{ext}"


# ---------------------------------------------------------------------------
# Health & Courses
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "ok": True,
        "database": "supabase-postgresql" if settings.is_postgres else "sqlite-local",
        "gemini_configured": settings.is_gemini_configured,
        "gemini_model": settings.gemini_model,
        "stt": stt_service.status_info,
    }


@app.get("/api/courses", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)):
    rows = db.scalars(select(Course).order_by(Course.created_at.desc())).all()
    return [
        CourseOut(id=c.id, code=c.code, title=c.title, created_at=c.created_at)
        for c in rows
    ]


@app.post("/api/courses", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    code = payload.code.strip().upper()
    existing = db.scalar(select(Course).where(Course.code == code))
    if existing:
        return CourseOut(
            id=existing.id,
            code=existing.code,
            title=existing.title,
            created_at=existing.created_at,
        )
    course = Course(code=code, title=payload.title.strip())
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseOut(
        id=course.id,
        code=course.code,
        title=course.title,
        created_at=course.created_at,
    )


# ---------------------------------------------------------------------------
# Sessions & Glossaries
# ---------------------------------------------------------------------------


@app.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(LectureSession).order_by(LectureSession.created_at.desc()).limit(50)
    ).all()
    return [_serialize_session(db, s) for s in rows]


@app.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    course_title = payload.course_title.strip()
    course_code = (
        payload.course_code.strip().upper()
        if payload.course_code and payload.course_code.strip()
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
        topic=payload.topic.strip(),
        date=payload.date.strip(),
        status="live",
        language=payload.language,
    )
    db.add(sess)
    db.flush()

    seen_terms: set[str] = set()
    for raw_term in payload.glossary:
        term = raw_term.strip()
        if term and term.lower() not in seen_terms:
            seen_terms.add(term.lower())
            db.add(GlossaryTerm(session_id=sess.id, term=term))

    db.commit()
    db.refresh(sess)
    return _serialize_session(db, sess)


@app.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(db, sess)


@app.patch("/api/sessions/{session_id}", response_model=SessionOut)
async def patch_session(
    session_id: str, payload: SessionPatch, db: Session = Depends(get_db)
):
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    should_polish = False
    if payload.status is not None:
        sess.status = payload.status
        if payload.status == "ended":
            sess.ended_at = int(time.time() * 1000)
            cap_count = (
                db.scalar(
                    select(func.count(TranscriptSegment.id)).where(
                        TranscriptSegment.session_id == sess.id
                    )
                )
                or 0
            )
            if cap_count > 0:
                sess.polish_status = "processing"
                should_polish = True
    if payload.language is not None:
        sess.language = payload.language

    db.commit()
    db.refresh(sess)
    out = _serialize_session(db, sess)
    await ws_manager.broadcast(
        sess.id, {"type": "session_update", "session": out.model_dump()}
    )
    if should_polish:
        _schedule_async_polish(sess.id)
    return out


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(sess)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Captions & Audio Transcription (Faster-Whisper + Silero VAD + Gemini Flash)
# ---------------------------------------------------------------------------


@app.get("/api/sessions/{session_id}/captions", response_model=list[CaptionOut])
def list_captions(session_id: str, db: Session = Depends(get_db)):
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.scalars(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == sess.id)
        .order_by(TranscriptSegment.seq.asc())
    ).all()
    return [_serialize_caption(r) for r in rows]


@app.post("/api/sessions/{session_id}/captions", response_model=CaptionOut, status_code=201)
async def submit_caption(session_id: str, payload: CaptionSubmit):
    sid = session_id.upper()
    cap = await asyncio.to_thread(
        _save_refined_caption_threadsafe,
        sid,
        payload.raw_text,
        payload.confidence,
        payload.language,
        payload.use_gemini,
    )
    if cap is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await ws_manager.broadcast(
        sid, {"type": "caption", "caption": cap.model_dump()}
    )
    return cap


@app.post("/api/sessions/{session_id}/transcribe-audio", response_model=list[CaptionOut])
async def transcribe_uploaded_audio(
    session_id: str,
    file: UploadFile = File(...),
    language: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Transcribes an uploaded lecture recording using Faster-Whisper (large-v3-turbo) + Silero VAD
    with the session's glossary hotwords & initial_prompt, then refines via Gemini Flash / Math Engine.
    Audio is processed in a temporary file and immediately deleted (never stored).
    """
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    lang = language or sess.language
    glossary = [g.term for g in sess.glossaries]

    try:
        stt_results = await asyncio.to_thread(
            stt_service.transcribe_file,
            audio_bytes,
            file.filename or "recording.wav",
            lang,
            sess.course_title,
            sess.topic,
            glossary,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Faster-Whisper transcription failed: {exc}",
        ) from exc

    created: list[CaptionOut] = []
    for item in stt_results:
        cap = await asyncio.to_thread(
            _save_refined_caption_threadsafe,
            sess.id,
            item.text,
            item.confidence,
            lang,
            True,
        )
        if cap is None:
            continue
        created.append(cap)
        await ws_manager.broadcast(
            sess.id, {"type": "caption", "caption": cap.model_dump()}
        )

    return created


# ---------------------------------------------------------------------------
# Post-Session Summary (Gemini Flash) & Export (python-docx, ReportLab, TXT)
# ---------------------------------------------------------------------------


@app.post("/api/sessions/{session_id}/summary", response_model=SummaryResponse)
async def create_summary(session_id: str, db: Session = Depends(get_db)):
    sess = db.get(LectureSession, session_id.upper())
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = db.scalars(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == sess.id)
        .order_by(TranscriptSegment.seq.asc())
    ).all()
    captions = [_serialize_caption(r).model_dump() for r in rows]
    glossary = [g.term for g in sess.glossaries]

    summary_md, provider = await asyncio.to_thread(
        generate_grounded_summary,
        sess.course_title,
        sess.topic,
        glossary,
        captions,
        sess.language,
    )
    sess.summary_md = summary_md
    db.commit()
    return SummaryResponse(
        session_id=sess.id, summary_md=summary_md, provider=provider
    )


@app.post("/api/sessions/{session_id}/polish", response_model=PolishResponse)
async def polish_session_transcript(
    session_id: str,
    wait: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """
    Runs the post-session academic transcript polish pass (stitching choppy STT fragments,
    removing oral fillers, grounding glossary & LaTeX into study-guide paragraphs).
    Pass `wait=false` to trigger asynchronously in the background.
    """
    sid = session_id.upper()
    sess = db.get(LectureSession, sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    cap_count = (
        db.scalar(
            select(func.count(TranscriptSegment.id)).where(
                TranscriptSegment.session_id == sid
            )
        )
        or 0
    )
    if cap_count == 0:
        return PolishResponse(
            session_id=sid,
            polish_status="idle",
            polished_transcript_md=sess.polished_transcript_md,
            provider=sess.polish_provider,
        )

    if not wait:
        sess.polish_status = "processing"
        db.commit()
        _schedule_async_polish(sid)
        return PolishResponse(
            session_id=sid,
            polish_status="processing",
            polished_transcript_md=sess.polished_transcript_md,
            provider=sess.polish_provider,
        )

    res = await asyncio.to_thread(run_polish_for_session_threadsafe, sid)
    if not res:
        raise HTTPException(status_code=404, detail="Session not found")

    with SessionLocal() as fresh_db:
        updated = fresh_db.get(LectureSession, sid)
        if updated:
            await ws_manager.broadcast(
                sid,
                {
                    "type": "session_update",
                    "session": _serialize_session(fresh_db, updated).model_dump(),
                },
            )
    return PolishResponse(**res)


def _load_export_bundle(session_id: str, db: Session):
    sid = session_id.upper()
    sess = db.get(LectureSession, sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = db.scalars(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == sess.id)
        .order_by(TranscriptSegment.seq.asc())
    ).all()
    if rows and not sess.polished_transcript_md:
        run_polish_for_session_threadsafe(sid)
        db.expire_all()
        sess = db.get(LectureSession, sid) or sess
    sess_dict = _serialize_session(db, sess).model_dump()
    captions = [_serialize_caption(r).model_dump() for r in rows]
    return sess, sess_dict, captions


@app.get("/api/sessions/{session_id}/export/docx")
def export_docx(session_id: str, db: Session = Depends(get_db)):
    sess, sess_dict, captions = _load_export_bundle(session_id, db)
    content = build_docx_bytes(sess_dict, captions)
    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(sess, "docx")}"'
        },
    )


@app.get("/api/sessions/{session_id}/export/pdf")
def export_pdf(session_id: str, db: Session = Depends(get_db)):
    sess, sess_dict, captions = _load_export_bundle(session_id, db)
    content = build_pdf_bytes(sess_dict, captions)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(sess, "pdf")}"'
        },
    )


@app.get("/api/sessions/{session_id}/export/txt")
def export_txt(session_id: str, db: Session = Depends(get_db)):
    sess, sess_dict, captions = _load_export_bundle(session_id, db)
    content = build_txt_bytes(sess_dict, captions)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(sess, "txt")}"'
        },
    )


# ---------------------------------------------------------------------------
# WebSockets: Low-Latency Host Audio/Caption Stream & Student Live Sync
# ---------------------------------------------------------------------------


@app.websocket("/ws/student/{session_id}")
async def ws_student(
    websocket: WebSocket,
    session_id: str,
    client_id: str = Query(default="stu-anon"),
):
    sid = session_id.upper()
    count = await ws_manager.connect_student(sid, websocket, client_id)

    try:
        with SessionLocal() as db:
            sess = db.get(LectureSession, sid)
            if not sess:
                await websocket.send_json({"type": "error", "message": "Session not found"})
                await websocket.close(code=4004)
                return
            rows = db.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.session_id == sid)
                .order_by(TranscriptSegment.seq.asc())
            ).all()
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "session": _serialize_session(db, sess).model_dump(),
                    "captions": [_serialize_caption(r).model_dump() for r in rows],
                    "student_count": count,
                }
            )

        await ws_manager.broadcast(
            sid, {"type": "student_count", "count": count}
        )

        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        remaining = await ws_manager.disconnect_student(sid, websocket)
        await ws_manager.broadcast(
            sid, {"type": "student_count", "count": remaining}
        )


@app.websocket("/ws/host/{session_id}")
async def ws_host(websocket: WebSocket, session_id: str):
    """
    Host WebSocket accepts:
    - Binary frames: 16kHz mono PCM16 audio chunks -> Faster-Whisper + Silero VAD -> Gemini refinement -> Broadcast
    - Text JSON frames: {"type": "interim"|"final"|"status"|"language", ...}
    """
    sid = session_id.upper()
    await ws_manager.connect_host(sid, websocket)

    try:
        with SessionLocal() as db:
            sess = db.get(LectureSession, sid)
            if not sess:
                await websocket.send_json({"type": "error", "message": "Session not found"})
                await websocket.close(code=4004)
                return
            rows = db.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.session_id == sid)
                .order_by(TranscriptSegment.seq.asc())
            ).all()
            await websocket.send_json(
                {
                    "type": "snapshot",
                    "session": _serialize_session(db, sess).model_dump(),
                    "captions": [_serialize_caption(r).model_dump() for r in rows],
                    "student_count": ws_manager.student_count(sid),
                }
            )

        while True:
            packet = await websocket.receive()
            if packet.get("type") == "websocket.disconnect":
                break

            # 1. Binary PCM16 audio chunk from lecturer's mic -> Faster-Whisper + Silero VAD
            raw_bytes = packet.get("bytes")
            if raw_bytes:
                with SessionLocal() as db:
                    sess = db.get(LectureSession, sid)
                    if not sess or sess.status != "live":
                        continue
                    glossary = [g.term for g in sess.glossaries]
                    lang = sess.language
                    course_title = sess.course_title
                    topic = sess.topic

                try:
                    stt_items = await asyncio.to_thread(
                        stt_service.transcribe_pcm16,
                        raw_bytes,
                        16000,
                        lang,
                        course_title,
                        topic,
                        glossary,
                    )
                except Exception as exc:
                    await websocket.send_json(
                        {"type": "stt_error", "message": str(exc)}
                    )
                    continue

                for item in stt_items:
                    cap = await asyncio.to_thread(
                        _save_refined_caption_threadsafe,
                        sid,
                        item.text,
                        item.confidence,
                        lang,
                        True,
                    )
                    if cap is not None:
                        await ws_manager.broadcast(
                            sid, {"type": "caption", "caption": cap.model_dump()}
                        )
                continue

            # 2. JSON text control or utterance event
            text_payload = packet.get("text")
            if not text_payload:
                continue
            if text_payload == "ping":
                await websocket.send_text("pong")
                continue

            data = json.loads(text_payload)
            msg_type = data.get("type")

            if msg_type == "interim":
                await ws_manager.broadcast(
                    sid,
                    {"type": "interim", "text": str(data.get("text") or "").strip()},
                )
            elif msg_type == "final":
                utterance = str(data.get("text") or "").strip()
                if not utterance:
                    continue
                conf = data.get("confidence", 0.94)
                cap = await asyncio.to_thread(
                    _save_refined_caption_threadsafe,
                    sid,
                    utterance,
                    conf,
                    data.get("language"),
                    bool(data.get("use_gemini", True)),
                )
                if cap is not None:
                    await ws_manager.broadcast(sid, {"type": "interim", "text": ""})
                    await ws_manager.broadcast(
                        sid, {"type": "caption", "caption": cap.model_dump()}
                    )
            elif msg_type == "status":
                new_status = data.get("status")
                if new_status in ("live", "paused", "ended"):
                    should_polish = False
                    with SessionLocal() as db:
                        sess = db.get(LectureSession, sid)
                        if sess:
                            sess.status = new_status
                            if new_status == "ended":
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
                            db.commit()
                            db.refresh(sess)
                            out = _serialize_session(db, sess).model_dump()
                            await ws_manager.broadcast(
                                sid, {"type": "session_update", "session": out}
                            )
                    if should_polish:
                        _schedule_async_polish(sid)
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect_host(sid, websocket)
