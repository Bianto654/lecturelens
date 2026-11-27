from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

SpeechLanguage = Literal["id-ID", "en-US"]
SessionStatus = Literal["live", "paused", "ended"]
PolishStatus = Literal["idle", "processing", "ready", "failed"]


class CourseCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=2, max_length=200)


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    created_at: int


class SessionCreate(BaseModel):
    course_title: str = Field(min_length=1, max_length=200)
    course_code: Optional[str] = None
    topic: str = Field(min_length=1, max_length=255)
    date: str
    language: SpeechLanguage = "id-ID"
    glossary: list[str] = Field(default_factory=list)


class SessionPatch(BaseModel):
    status: Optional[SessionStatus] = None
    language: Optional[SpeechLanguage] = None


class SessionOut(BaseModel):
    id: str
    course_id: Optional[int] = None
    course_title: str
    topic: str
    date: str
    status: SessionStatus
    language: SpeechLanguage
    glossary: list[str] = Field(default_factory=list)
    summary_md: Optional[str] = None
    polished_transcript_md: Optional[str] = None
    polish_status: PolishStatus = "idle"
    polish_provider: Optional[str] = None
    caption_count: int = 0
    student_count: int = 0
    created_at: int
    ended_at: Optional[int] = None


class FormulaAnnotation(BaseModel):
    original_text: str
    latex: str
    ambiguous: bool = False
    rule_name: str = "rule"


class GlossaryAnnotation(BaseModel):
    original: str
    matched_term: str
    was_corrected: bool = False
    similarity: float = 1.0


class CaptionOut(BaseModel):
    seq: int
    session_id: str
    timestamp_ms: int
    raw_text: str
    processed_text: str
    segments: list[dict[str, Any]]
    formulas: list[FormulaAnnotation]
    glossary_matches: list[GlossaryAnnotation]
    is_unclear: bool = False
    confidence: Optional[float] = None
    language: SpeechLanguage = "id-ID"
    refined_by: str = "rules"


class CaptionSubmit(BaseModel):
    raw_text: str = Field(min_length=1)
    confidence: Optional[float] = 0.95
    language: Optional[SpeechLanguage] = None
    use_gemini: bool = True


class SummaryResponse(BaseModel):
    session_id: str
    summary_md: str
    provider: str


class PolishResponse(BaseModel):
    session_id: str
    polish_status: PolishStatus
    polished_transcript_md: Optional[str] = None
    provider: Optional[str] = None
