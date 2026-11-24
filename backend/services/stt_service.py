from __future__ import annotations

import logging
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

import numpy as np

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    text: str
    confidence: float
    language: str
    engine: str
    had_speech: bool = True


class STTAdapter(Protocol):
    """Swappable Speech-to-Text engine contract."""

    def transcribe_pcm16(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        language: str,
        course_title: str,
        topic: str,
        glossary: list[str],
    ) -> list[STTResult]: ...

    def transcribe_file(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str,
        course_title: str,
        topic: str,
        glossary: list[str],
    ) -> list[STTResult]: ...


def build_initial_prompt(
    course_title: str,
    topic: str,
    glossary: list[str],
    language: str,
) -> str:
    """Builds a domain-aware Whisper initial_prompt biasing technical vocabulary."""
    terms = ", ".join(g.strip() for g in glossary if g.strip())
    if language.startswith("id"):
        base = f"Kuliah {course_title}, topik {topic}."
        if terms:
            base += f" Istilah penting: {terms}."
        return base
    base = f"University lecture on {course_title}, topic {topic}."
    if terms:
        base += f" Key terminology: {terms}."
    return base


def build_hotwords(glossary: list[str]) -> Optional[str]:
    cleaned = [g.strip() for g in glossary if g.strip()]
    return ", ".join(cleaned[:40]) if cleaned else None


class FasterWhisperSileroService:
    """
    Faster-Whisper (large-v3-turbo) + Silero VAD transcription engine.
    - Uses built-in ONNX Silero VAD (`vad_filter=True`) to skip silence & prevent hallucinations.
    - Injects session glossary via both `hotwords` and `initial_prompt`.
    - Lazily loads the WhisperModel on first audio request so FastAPI boots instantly.
    """

    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()
        self._load_error: Optional[str] = None

    @property
    def is_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401

            return True
        except Exception:
            return False

    @property
    def status_info(self) -> dict[str, object]:
        settings = get_settings()
        return {
            "library_installed": self.is_available,
            "model_size": settings.whisper_model_size,
            "device": settings.whisper_device,
            "compute_type": settings.whisper_compute_type,
            "silero_vad": True,
            "loaded": self._model is not None,
            "load_error": self._load_error,
        }

    def _get_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            settings = get_settings()
            if not settings.whisper_enabled:
                raise RuntimeError("WHISPER_ENABLED is false in environment config.")
            try:
                from faster_whisper import WhisperModel

                device = settings.whisper_device
                compute_type = settings.whisper_compute_type
                if device == "auto":
                    try:
                        import ctranslate2

                        device = (
                            "cuda"
                            if ctranslate2.get_cuda_device_count() > 0
                            else "cpu"
                        )
                    except Exception:
                        device = "cpu"
                if device == "cpu" and compute_type == "float16":
                    compute_type = "int8"

                logger.info(
                    "Loading Faster-Whisper model=%s device=%s compute_type=%s",
                    settings.whisper_model_size,
                    device,
                    compute_type,
                )
                self._model = WhisperModel(
                    settings.whisper_model_size,
                    device=device,
                    compute_type=compute_type,
                )
                self._load_error = None
                return self._model
            except Exception as exc:
                self._load_error = str(exc)
                logger.exception("Failed to initialize Faster-Whisper model")
                raise

    def _run_transcribe(
        self,
        audio_input,
        language: str,
        course_title: str,
        topic: str,
        glossary: list[str],
    ) -> list[STTResult]:
        model = self._get_model()
        lang_code = "id" if language.startswith("id") else "en"
        initial_prompt = build_initial_prompt(course_title, topic, glossary, language)
        hotwords = build_hotwords(glossary)

        segments, info = model.transcribe(
            audio_input,
            language=lang_code,
            task="transcribe",
            beam_size=5,
            vad_filter=True,  # Built-in Silero VAD
            vad_parameters={
                "min_silence_duration_ms": 450,
                "speech_pad_ms": 250,
                "threshold": 0.45,
            },
            initial_prompt=initial_prompt,
            hotwords=hotwords,
            condition_on_previous_text=True,
        )

        results: list[STTResult] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            # Convert avg_logprob (~ -1.5..0) into a 0..1 confidence estimate
            avg_lp = getattr(seg, "avg_logprob", -0.25)
            no_speech = getattr(seg, "no_speech_prob", 0.0)
            if no_speech > 0.75:
                continue
            conf = float(max(0.1, min(0.99, np.exp(avg_lp))))
            results.append(
                STTResult(
                    text=text,
                    confidence=round(conf, 3),
                    language=language,
                    engine=f"faster-whisper ({get_settings().whisper_model_size}) + silero-vad",
                    had_speech=True,
                )
            )
        return results

    def transcribe_pcm16(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        language: str,
        course_title: str,
        topic: str,
        glossary: list[str],
    ) -> list[STTResult]:
        if not pcm_bytes:
            return []
        pcm_i16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        if pcm_i16.size < 1600:  # < 0.1s at 16kHz
            return []
        audio_f32 = pcm_i16.astype(np.float32) / 32768.0

        # Quick RMS energy pre-gate before invoking Whisper
        rms = float(np.sqrt(np.mean(np.square(audio_f32))))
        if rms < 0.008:
            return []

        if sample_rate != 16000 and sample_rate > 0:
            # Linear resample to 16kHz
            target_len = max(1, int(round(audio_f32.size * 16000 / sample_rate)))
            x_old = np.linspace(0.0, 1.0, num=audio_f32.size, endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
            audio_f32 = np.interp(x_new, x_old, audio_f32).astype(np.float32)

        return self._run_transcribe(
            audio_f32, language, course_title, topic, glossary
        )

    def transcribe_file(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str,
        course_title: str,
        topic: str,
        glossary: list[str],
    ) -> list[STTResult]:
        suffix = Path(filename).suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)
        try:
            return self._run_transcribe(
                str(tmp_path), language, course_title, topic, glossary
            )
        finally:
            tmp_path.unlink(missing_ok=True)


stt_service = FasterWhisperSileroService()
