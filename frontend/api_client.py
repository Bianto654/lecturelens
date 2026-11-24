from __future__ import annotations

import os
from typing import Any, Optional
import httpx


def get_backend_http_url() -> str:
    # Supports Streamlit Community Cloud secrets or .env BACKEND_URL
    try:
        import streamlit as st

        if "BACKEND_URL" in st.secrets:
            return str(st.secrets["BACKEND_URL"]).rstrip("/")
    except Exception:
        pass
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def get_public_backend_ws_url() -> str:
    try:
        import streamlit as st

        if "PUBLIC_BACKEND_WS_URL" in st.secrets:
            return str(st.secrets["PUBLIC_BACKEND_WS_URL"]).rstrip("/")
    except Exception:
        pass
    explicit = os.getenv("PUBLIC_BACKEND_WS_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    http_url = get_backend_http_url()
    if http_url.startswith("https://"):
        return http_url.replace("https://", "wss://", 1)
    return http_url.replace("http://", "ws://", 1)


def get_public_backend_http_url() -> str:
    ws_url = get_public_backend_ws_url()
    if ws_url.startswith("wss://"):
        return ws_url.replace("wss://", "https://", 1)
    if ws_url.startswith("ws://"):
        return ws_url.replace("ws://", "http://", 1)
    return get_backend_http_url()


def get_public_app_url() -> str:
    try:
        import streamlit as st

        if "PUBLIC_APP_URL" in st.secrets:
            return str(st.secrets["PUBLIC_APP_URL"]).rstrip("/")
    except Exception:
        pass
    return os.getenv("PUBLIC_APP_URL", "http://localhost:8501").rstrip("/")


class LectureLensAPI:
    is_embedded = False

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or get_backend_http_url()).rstrip("/")

    def health(self) -> Optional[dict[str, Any]]:
        try:
            r = httpx.get(f"{self.base_url}/api/health", timeout=4.0)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def list_sessions(self) -> list[dict[str, Any]]:
        r = httpx.get(f"{self.base_url}/api/sessions", timeout=8.0)
        r.raise_for_status()
        return r.json()

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = httpx.post(f"{self.base_url}/api/sessions", json=payload, timeout=10.0)
        r.raise_for_status()
        return r.json()

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        r = httpx.get(f"{self.base_url}/api/sessions/{session_id}", timeout=8.0)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def patch_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = httpx.patch(
            f"{self.base_url}/api/sessions/{session_id}", json=payload, timeout=8.0
        )
        r.raise_for_status()
        return r.json()

    def delete_session(self, session_id: str) -> None:
        r = httpx.delete(f"{self.base_url}/api/sessions/{session_id}", timeout=8.0)
        r.raise_for_status()

    def list_captions(self, session_id: str) -> list[dict[str, Any]]:
        r = httpx.get(
            f"{self.base_url}/api/sessions/{session_id}/captions", timeout=10.0
        )
        r.raise_for_status()
        return r.json()

    def submit_caption(
        self, session_id: str, raw_text: str, confidence: float = 0.95
    ) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/api/sessions/{session_id}/captions",
            json={"raw_text": raw_text, "confidence": confidence},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()

    def transcribe_audio_file(
        self,
        session_id: str,
        filename: str,
        data: bytes,
        content_type: str,
        language: str,
    ) -> list[dict[str, Any]]:
        r = httpx.post(
            f"{self.base_url}/api/sessions/{session_id}/transcribe-audio",
            params={"language": language},
            files={"file": (filename, data, content_type)},
            timeout=300.0,
        )
        r.raise_for_status()
        return r.json()

    def list_bookmarks(self, session_id: str, student_id: str) -> list[dict[str, Any]]:
        r = httpx.get(
            f"{self.base_url}/api/sessions/{session_id}/bookmarks",
            params={"student_id": student_id},
            timeout=8.0,
        )
        r.raise_for_status()
        return r.json()

    def upsert_bookmark(
        self, session_id: str, seq: int, student_id: str, note: str = ""
    ) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/api/sessions/{session_id}/bookmarks",
            json={"transcript_seq": seq, "student_id": student_id, "note": note},
            timeout=8.0,
        )
        r.raise_for_status()
        return r.json()

    def delete_bookmark(self, session_id: str, seq: int, student_id: str) -> None:
        r = httpx.delete(
            f"{self.base_url}/api/sessions/{session_id}/bookmarks/{seq}",
            params={"student_id": student_id},
            timeout=8.0,
        )
        r.raise_for_status()

    def generate_summary(self, session_id: str) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/api/sessions/{session_id}/summary", timeout=60.0
        )
        r.raise_for_status()
        return r.json()

    def download_export(self, session_id: str, fmt: str) -> bytes:
        r = httpx.get(
            f"{self.base_url}/api/sessions/{session_id}/export/{fmt}", timeout=30.0
        )
        r.raise_for_status()
        return r.content


def get_api_client():
    """
    Returns remote FastAPI client when BACKEND_URL is reachable,
    or seamlessly falls back to EmbeddedLectureLensAPI for 1-click
    zero-card Streamlit Community Cloud deployment!
    """
    remote = LectureLensAPI()
    if remote.health() is not None:
        return remote

    # Bridge Streamlit Cloud secrets into os.environ for backend.config.Settings
    try:
        import streamlit as st

        for key in ("DATABASE_URL", "GEMINI_API_KEY", "GEMINI_MODEL", "PUBLIC_APP_URL"):
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass

    from frontend.local_backend import EmbeddedLectureLensAPI

    return EmbeddedLectureLensAPI()

