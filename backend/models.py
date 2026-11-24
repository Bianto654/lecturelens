from __future__ import annotations

import time
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db import Base


def _now_ms() -> int:
    return int(time.time() * 1000)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ms)

    sessions: Mapped[list[LectureSession]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class LectureSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_title: Mapped[str] = mapped_column(String(200), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="live", index=True)
    language: Mapped[str] = mapped_column(String(16), default="id-ID")
    summary_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ms)
    ended_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    course: Mapped[Optional[Course]] = relationship(back_populates="sessions")
    glossaries: Mapped[list[GlossaryTerm]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="GlossaryTerm.id",
    )
    transcripts: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.seq",
    )
    bookmarks: Mapped[list[Bookmark]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Bookmark.created_at",
    )


class GlossaryTerm(Base):
    __tablename__ = "glossaries"
    __table_args__ = (
        UniqueConstraint("session_id", "term", name="uq_glossary_session_term"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    term: Mapped[str] = mapped_column(String(160), nullable=False)

    session: Mapped[LectureSession] = relationship(back_populates="glossaries")


class TranscriptSegment(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_transcript_session_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, default=_now_ms)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    processed_text: Mapped[str] = mapped_column(Text, nullable=False)
    segments_json: Mapped[str] = mapped_column(Text, default="[]")
    formulas_json: Mapped[str] = mapped_column(Text, default="[]")
    glossary_matches_json: Mapped[str] = mapped_column(Text, default="[]")
    is_unclear: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="id-ID")
    refined_by: Mapped[str] = mapped_column(String(32), default="rules")

    session: Mapped[LectureSession] = relationship(back_populates="transcripts")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "transcript_seq",
            "student_id",
            name="uq_bookmark_student_seg",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    transcript_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[str] = mapped_column(String(80), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now_ms)

    session: Mapped[LectureSession] = relationship(back_populates="bookmarks")
