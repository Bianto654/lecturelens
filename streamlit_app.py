from __future__ import annotations

import base64
import datetime
import io
import re
import uuid
from urllib.parse import parse_qs, urlparse

import qrcode
import streamlit as st
from dotenv import load_dotenv

from frontend.api_client import (
    get_api_client,
    get_backend_http_url,
    get_public_app_url,
    get_public_backend_http_url,
    get_public_backend_ws_url,
)
from frontend.bidi_mic import mount_host_mic_console, mount_room_qr_card
from frontend.components import (
    render_host_live_console,
    render_katex_transcript_list,
    render_student_live_console,
)
from frontend.i18n import tr

load_dotenv()

st.set_page_config(
    page_title="LectureLens — Teks Kuliah Langsung",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Canva Education Bio-Link Visual System (DAHcFfKiO5Q)
# Royal Cobalt Blue Canvas (#004D8F) + Retro Coral-Orange (#FF4F28)
# Crisp Light Grey (#EDEDED) + Pure White Pill Surfaces (#FFFFFF)
# Bold Deep Navy-Ink Outlines (#0C2337) + Retro Window Frames (● ■ ▲)
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..900;1,9..40,400..900&family=JetBrains+Mono:wght@600;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif !important;
  }
  .stApp {
    background: #004d8f !important;
    color: #ffffff;
  }
  header[data-testid="stHeader"] {
    background: rgba(0, 77, 143, 0.92) !important;
    backdrop-filter: blur(8px);
  }
  .block-container {
    max-width: 1020px !important;
    padding-top: 4rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
  }
  footer { visibility: hidden; }

  /* Default text directly on Royal Cobalt Blue canvas */
  .stApp .stMarkdown h1,
  .stApp .stMarkdown h2,
  .stApp .stMarkdown h3,
  .stApp .stMarkdown h4,
  .stApp .stMarkdown p,
  .stApp [data-testid="stCaptionContainer"] p,
  .stApp [data-testid="stWidgetLabel"] p {
    color: #ffffff;
  }
  .stApp hr {
    border-color: rgba(237, 237, 237, 0.28) !important;
  }

  /* Crisp Canva Pill Buttons (White + Navy Ink Outline, Coral-Orange Primary) */
  button[kind="primary"],
  div[data-testid="stFormSubmitButton"] button {
    min-height: 50px !important;
    border-radius: 999px !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    letter-spacing: 0.055em !important;
    text-transform: uppercase !important;
    background: #ff4f28 !important;
    color: #ffffff !important;
    border: 2.2px solid #0c2337 !important;
    box-shadow: 0 4px 0 #0c2337 !important;
    transition: transform 0.13s ease, background 0.13s ease, box-shadow 0.13s ease !important;
  }
  button[kind="primary"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover {
    background: #e63f1a !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 0 #0c2337 !important;
  }
  button[kind="primary"]:active,
  div[data-testid="stFormSubmitButton"] button:active {
    transform: translateY(1px);
    box-shadow: 0 2px 0 #0c2337 !important;
  }

  button[kind="secondary"],
  div[data-testid="stDownloadButton"] button {
    min-height: 48px !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    font-size: 12.5px !important;
    letter-spacing: 0.055em !important;
    text-transform: uppercase !important;
    background: #ffffff !important;
    border: 2.2px solid #0c2337 !important;
    color: #0c2337 !important;
    box-shadow: 0 4px 0 #0c2337 !important;
    transition: transform 0.13s ease, background 0.13s ease, box-shadow 0.13s ease !important;
  }
  button[kind="primary"] *,
  div[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
  }
  button[kind="secondary"] *,
  div[data-testid="stDownloadButton"] button * {
    color: #0c2337 !important;
  }
  button[kind="secondary"]:hover,
  div[data-testid="stDownloadButton"] button:hover {
    background: #ededed !important;
    color: #0c2337 !important;
    border-color: #0c2337 !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 0 #0c2337 !important;
  }
  button[kind="secondary"]:active,
  div[data-testid="stDownloadButton"] button:active {
    transform: translateY(1px);
    box-shadow: 0 2px 0 #0c2337 !important;
  }

  /* Crisp White Retro-Outlined Cards, Expanders & Alerts */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 2.5px solid #0c2337 !important;
    border-radius: 22px !important;
    box-shadow: 0 5px 0 #0c2337 !important;
    color: #0c2337 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h1,
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h2,
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h3,
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h4,
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p,
  div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown li,
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"] p,
  div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] p,
  div[data-testid="stVerticalBlockBorderWrapper"] label,
  div[data-testid="stVerticalBlockBorderWrapper"] span {
    color: #0c2337;
  }
  /* Preserve white text on primary buttons inside white cards */
  div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"] *,
  div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
  }

  div[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 2.5px solid #0c2337 !important;
    border-radius: 20px !important;
    box-shadow: 0 4px 0 #0c2337 !important;
    overflow: hidden;
  }
  div[data-testid="stExpander"] summary,
  div[data-testid="stExpander"] summary p,
  div[data-testid="stExpander"] summary svg,
  div[data-testid="stExpander"] [data-testid="stCaptionContainer"] p,
  div[data-testid="stExpander"] label,
  div[data-testid="stExpander"] .stMarkdown p {
    color: #0c2337 !important;
    font-weight: 700;
  }
  div[data-testid="stExpander"] button[kind="primary"] * {
    color: #ffffff !important;
  }

  div[data-testid="stAlert"] {
    background: #ededed !important;
    border: 2.2px solid #0c2337 !important;
    border-radius: 18px !important;
    box-shadow: 0 4px 0 #0c2337 !important;
    color: #0c2337 !important;
  }
  div[data-testid="stAlert"] p,
  div[data-testid="stAlert"] span,
  div[data-testid="stAlert"] strong,
  div[data-testid="stAlert"] code {
    color: #0c2337 !important;
  }

  /* Inputs inside Forms & Cards */
  input[type="text"], textarea, div[data-baseweb="select"] > div {
    border-radius: 14px !important;
    border: 2px solid #0c2337 !important;
    background: #f8fafc !important;
    color: #0c2337 !important;
    font-weight: 600 !important;
  }

  /* Brand Header (✴ lecturelens) */
  .cv-brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 27px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.03em;
    line-height: 1;
    padding: 4px 0;
  }
  .cv-spark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    flex-shrink: 0;
  }

  /* Signature Canva Coral-Topped Retro Browser Window (Home Hero Left) */
  .cv-window-wrap {
    position: relative;
    padding-top: 4px;
    padding-right: 16px;
    margin-bottom: 10px;
  }
  .cv-window {
    background: #ffffff;
    border: 2.5px solid #0c2337;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 7px 0 #0c2337;
  }
  .cv-win-bar {
    background: #ff4f28;
    border-bottom: 2.5px solid #0c2337;
    padding: 10px 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .cv-win-dots {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .cv-dot-c { width: 11px; height: 11px; border-radius: 50%; background: #ededed; display: inline-block; }
  .cv-dot-s { width: 11px; height: 11px; background: #ededed; display: inline-block; }
  .cv-dot-t {
    width: 0; height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-bottom: 11px solid #ededed;
    display: inline-block;
  }
  .cv-win-bar-tag {
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .cv-win-scene {
    background: linear-gradient(180deg, #f7f4ef 0%, #ede8df 100%);
    padding: 20px 18px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .cv-scene-live {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    align-self: flex-start;
    background: #ff4f28;
    color: #ffffff;
    border: 2px solid #0c2337;
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .cv-scene-card {
    background: #ffffff;
    border: 2px solid #0c2337;
    border-radius: 16px;
    padding: 13px 15px;
    color: #0c2337;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.5;
    box-shadow: 0 3px 0 #0c2337;
  }
  .cv-scene-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    color: #455c72;
    margin-bottom: 4px;
  }
  .cv-scene-math {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #fff4f1;
    border: 1.8px solid #ff4f28;
    border-radius: 10px;
    padding: 2px 9px;
    margin: 2px 0;
    font-weight: 800;
    color: #0c2337;
  }
  .cv-scene-auto {
    background: #ff4f28;
    color: #ffffff;
    border-radius: 999px;
    padding: 1px 7px;
    font-size: 9.5px;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .cv-scene-gloss {
    background: #e0eefb;
    border-bottom: 2px solid #004d8f;
    color: #004d8f;
    font-weight: 800;
    padding: 1px 6px;
    border-radius: 6px;
  }
  .cv-scene-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    padding-top: 2px;
  }
  .cv-scene-chip {
    background: #ededed;
    border: 1.8px solid #0c2337;
    color: #0c2337;
    border-radius: 999px;
    padding: 4px 11px;
    font-size: 11.5px;
    font-weight: 800;
  }

  /* Floating Retro Speech Bubble with Blue Heart (Signature Canva Detail) */
  .cv-heart-bubble {
    position: absolute;
    top: 48px;
    right: 0;
    width: 78px;
    height: 60px;
    background: #ededed;
    border: 2.5px solid #0c2337;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 0 #0c2337;
    z-index: 3;
  }
  .cv-heart-bubble::after {
    content: '';
    position: absolute;
    bottom: -10px;
    left: 50%;
    transform: translateX(-50%) rotate(45deg);
    width: 15px;
    height: 15px;
    background: #ededed;
    border-right: 2.5px solid #0c2337;
    border-bottom: 2.5px solid #0c2337;
  }

  /* Right-Side Canva Display Headline */
  .cv-hero-headline {
    text-align: center;
    padding: 6px 6px 14px;
  }
  .cv-hero-headline h1 {
    font-size: 40px;
    font-weight: 500;
    line-height: 1.1;
    letter-spacing: -0.025em;
    color: #ffffff;
    margin: 0 0 10px 0;
  }
  .cv-hero-headline p {
    font-size: 14.5px;
    font-weight: 500;
    line-height: 1.55;
    color: #dbeafe;
    margin: 0 auto;
    max-width: 430px;
  }
  .cv-hero-stats {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    margin-top: 14px;
  }
  .cv-stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.14);
    border: 1.5px solid rgba(237, 237, 237, 0.45);
    color: #ffffff;
    padding: 5px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }

  /* Retro Window Banner for Room / Studio / Create / Transcript Pages */
  .cv-win-banner {
    background: #ffffff;
    border: 2.5px solid #0c2337;
    border-radius: 22px;
    overflow: hidden;
    box-shadow: 0 6px 0 #0c2337;
    margin: 10px 0 18px;
  }
  .cv-win-banner-body {
    padding: 18px 22px 20px;
    color: #0c2337;
  }
  .cv-win-banner-body h2 {
    margin: 8px 0 4px;
    font-size: 24px;
    font-weight: 800;
    color: #0c2337 !important;
    letter-spacing: -0.02em;
    line-height: 1.25;
  }
  .cv-win-banner-body .sub {
    font-size: 14px;
    font-weight: 500;
    color: #354c61 !important;
  }

  /* Section Header Bar on Royal Cobalt Canvas */
  .cv-section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.015em;
    margin: 22px 0 10px;
  }
  .cv-section-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #ff4f28;
    border: 2px solid #0c2337;
    display: inline-block;
  }

  /* Quick Join Coral Header Strip */
  .cv-join-strip {
    background: #ff4f28;
    border: 2.5px solid #0c2337;
    border-radius: 18px;
    padding: 12px 18px;
    margin: 18px 0 10px;
    box-shadow: 0 4px 0 #0c2337;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    color: #ffffff;
  }
  .cv-join-strip-title {
    font-size: 14.5px;
    font-weight: 800;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: #ffffff;
  }
  .cv-join-strip-sub {
    font-size: 13px;
    font-weight: 500;
    color: #fff1ed;
  }

  /* Past Sessions Row inside White Window Cards */
  .cv-course-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .cv-course-tile {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    border: 2.2px solid #0c2337;
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 3px 0 #0c2337;
  }
  .cv-course-title {
    font-size: 16.5px;
    font-weight: 800;
    color: #0c2337;
    line-height: 1.3;
  }
  .cv-course-sub {
    font-size: 13px;
    font-weight: 500;
    color: #455c72;
    margin-top: 2px;
  }

  /* Pill Badges (Canva Palette) */
  .cv-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 8px 0 4px;
  }
  .cv-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1.8px solid #0c2337;
    line-height: 1.35;
  }
  .cv-pill-blue   { background: #004d8f; color: #ffffff !important; }
  .cv-pill-orange { background: #ff4f28; color: #ffffff !important; }
  .cv-pill-grey   { background: #ededed; color: #0c2337 !important; }
  .cv-pill-white  { background: #ffffff; color: #0c2337 !important; }
  .cv-pill-yellow { background: #fef08a; color: #0c2337 !important; }
  .cv-pill-green  { background: #dcfce7; color: #0c2337 !important; }

  /* Summary Highlight Header */
  .cv-summary-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 15px;
    border-radius: 14px;
    background: #ededed;
    border: 2px solid #0c2337;
    color: #0c2337 !important;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  @media (max-width: 768px) {
    .cv-hero-headline h1 { font-size: 32px; }
    .cv-window-wrap { padding-right: 6px; }
    .cv-heart-bubble { width: 64px; height: 50px; top: 44px; }
  }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session State & Direct QR Deep-Link Handling
# ---------------------------------------------------------------------------

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "id"
if "student_id" not in st.session_state:
    st.session_state.student_id = f"stu-{uuid.uuid4().hex[:8]}"
if "page" not in st.session_state:
    st.session_state.page = "home"
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = ""
if "created_room" not in st.session_state:
    st.session_state.created_room = None
if "glossary_draft" not in st.session_state:
    st.session_state.glossary_draft = ""
if "seen_utterance_ids" not in st.session_state:
    st.session_state.seen_utterance_ids = set()
if "last_action_ts" not in st.session_state:
    st.session_state.last_action_ts = 0
if "student_qr_entry" not in st.session_state:
    st.session_state.student_qr_entry = False

qp_page = str(st.query_params.get("page", "")).strip().lower()
qp_session = str(st.query_params.get("session", "")).strip().upper()
qp_sig = f"{qp_page}|{qp_session}"

if qp_sig != st.session_state.get("_synced_qp"):
    st.session_state._synced_qp = qp_sig
    if qp_session:
        st.session_state.active_session_id = qp_session
        target_page = qp_page if qp_page in ("host", "join", "transcript") else "join"
        st.session_state.page = target_page
        st.session_state.student_qr_entry = target_page == "join"
    elif qp_page in ("home", "create", "host", "join", "transcript"):
        st.session_state.page = qp_page


def navigate(page: str, session_id: str = "") -> None:
    st.session_state.page = page
    if session_id:
        st.session_state.active_session_id = session_id.upper()
    if page != "join":
        st.session_state.student_qr_entry = False

    st.query_params["page"] = page
    if st.session_state.active_session_id and page in ("host", "join", "transcript"):
        st.query_params["session"] = st.session_state.active_session_id
    elif "session" in st.query_params and page in ("home", "create"):
        del st.query_params["session"]

    st.session_state._synced_qp = f"{page}|{st.query_params.get('session', '')}"
    st.rerun()


def extract_session_code(raw: str) -> str:
    txt = raw.strip()
    if not txt:
        return ""
    if "://" in txt or "session=" in txt or "/join/" in txt:
        parsed = urlparse(
            txt if "://" in txt else f"https://example.com/{txt.lstrip('/')}"
        )
        qs = parse_qs(parsed.query)
        if qs.get("session"):
            return qs["session"][0].strip().upper()
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            return parts[-1].strip().upper()
    return re.sub(r"[^A-Za-z0-9_-]", "", txt).upper()


def make_qr_data_url(url: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0c2337", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def parse_csv_glossary(content: str) -> list[str]:
    skip = {"term", "terms", "glossary", "istilah", "glosarium", "kata"}
    found: list[str] = []
    for line in content.splitlines():
        for cell in re.split(r"[,;]", line):
            val = cell.strip().strip("\"'")
            if val and val.lower() not in skip:
                found.append(val)
    return list(dict.fromkeys(found))


def resolve_public_app_url() -> str:
    try:
        ctx_url = getattr(st.context, "url", None)
        if ctx_url:
            parsed = urlparse(str(ctx_url))
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    except Exception:
        pass

    configured = get_public_app_url()
    if configured and "localhost" not in configured and "127.0.0.1" not in configured:
        return configured

    try:
        fwd_host = st.context.headers.get("x-forwarded-host") or st.context.headers.get(
            "host", ""
        )
        if fwd_host and "localhost" not in fwd_host and "127.0.0.1" not in fwd_host:
            return f"https://{fwd_host}".rstrip("/")
    except Exception:
        pass

    return configured


SUBJECT_PALETTES = [
    ("#004d8f", "📐"),
    ("#ff4f28", "🧪"),
    ("#0c2337", "💻"),
    ("#0369a1", "🧬"),
    ("#ea580c", "📚"),
]


def subject_visual(title: str) -> tuple[str, str]:
    idx = sum(ord(ch) for ch in title) % len(SUBJECT_PALETTES)
    return SUBJECT_PALETTES[idx]


SPARK_SVG = """
<svg width="26" height="26" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M14 2L16.4 9.6L23.5 5.8L19.1 12.6L26.6 15.2L18.7 16.5L21.8 23.8L14.9 19.3L11.8 26.5L11.4 18.6L3.6 20.6L9.1 14.8L2.2 10.6L10.1 11.1L9.2 3.2L14 9.5V2Z" fill="#FF4F28"/>
</svg>
"""

HEART_SVG = """
<svg width="36" height="32" viewBox="0 0 36 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M18 30.2C18 30.2 3 21.1 3 10.7C3 5.7 6.8 2 11.4 2C14.3 2 16.8 3.6 18 6C19.2 3.6 21.7 2 24.6 2C29.2 2 33 5.7 33 10.7C33 21.1 18 30.2 18 30.2Z" fill="#004D8F"/>
</svg>
"""


def win_banner_html(bar_title: str, pills_html: str, title: str, subtitle: str) -> str:
    return (
        f'<div class="cv-win-banner">'
        f'  <div class="cv-win-bar">'
        f'    <span class="cv-win-dots" aria-hidden="true">'
        f'      <span class="cv-dot-c"></span><span class="cv-dot-s"></span><span class="cv-dot-t"></span>'
        f'    </span>'
        f'    <span class="cv-win-bar-tag">{bar_title}</span>'
        f'  </div>'
        f'  <div class="cv-win-banner-body">'
        f'    <div class="cv-pill-row" style="margin:0 0 6px;">{pills_html}</div>'
        f'    <h2>{title}</h2>'
        f'    <div class="sub">{subtitle}</div>'
        f'  </div>'
        f'</div>'
    )


api = get_api_client()
lang = st.session_state.ui_lang
backend_http = get_backend_http_url()
public_backend_http = get_public_backend_http_url()
backend_ws = get_public_backend_ws_url()
public_app_url = resolve_public_app_url()
health = api.health()


# ---------------------------------------------------------------------------
# Brand Top Bar (Canva * lecturelens Header)
# ---------------------------------------------------------------------------

hdr_l, hdr_r = st.columns([8, 2])
with hdr_l:
    st.markdown(
        f'<div class="cv-brand">'
        f'  <span class="cv-spark">{SPARK_SVG}</span>'
        f'  <span>lecturelens</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with hdr_r:
    next_lang = "en" if lang == "id" else "id"
    if st.button(f"🌐 {lang.upper()} → {next_lang.upper()}", use_container_width=True):
        st.session_state.ui_lang = next_lang
        st.rerun()

if not health:
    st.error(tr(lang, "backend_offline", url=backend_http))
    st.stop()

# Clean Canva Pill Navigation (hidden on Home because Home features the signature Canva pill hub,
# and hidden automatically when a student scans QR straight into a room)
if st.session_state.page != "home" and not (
    st.session_state.student_qr_entry and st.session_state.page == "join"
):
    nav_cols = st.columns(5)
    nav_items = [
        ("home", f"🏠 {tr(lang, 'nav_home')}"),
        ("create", f"➕ {tr(lang, 'nav_create')}"),
        ("host", f"🎙️ {tr(lang, 'nav_host')}"),
        ("join", f"📱 {tr(lang, 'nav_student')}"),
        ("transcript", f"📄 {tr(lang, 'nav_transcript')}"),
    ]
    for col, (p_key, label) in zip(nav_cols, nav_items):
        with col:
            btn_type = "primary" if st.session_state.page == p_key else "secondary"
            if st.button(
                label, key=f"nav_{p_key}", type=btn_type, use_container_width=True
            ):
                navigate(p_key)


# ---------------------------------------------------------------------------
# PAGE 1: HOME (Canva Royal Blue Bio-Link Hub + Retro Classroom Window)
# ---------------------------------------------------------------------------

if st.session_state.page == "home":
    sessions = api.list_sessions()
    db_badge = (
        "Supabase PostgreSQL"
        if health.get("database") == "supabase-postgresql"
        else "Cloud Sync Aktif"
    )
    gem_badge = (
        f"Gemini {health.get('gemini_model', 'Flash')}"
        if health.get("gemini_configured")
        else "KaTeX Math Pintar"
    )

    hero_l, hero_r = st.columns([5.2, 4.8], gap="large")
    with hero_l:
        preview_line_1 = (
            'Hari ini kita bahas <span class="cv-scene-gloss">Integral Riemann</span> dan '
            '<span class="cv-scene-math">∫ 5x² dx <span class="cv-scene-auto">otomatis</span></span>'
            if lang == "id"
            else 'Today we cover <span class="cv-scene-gloss">Riemann Integral</span> and '
            '<span class="cv-scene-math">∫ 5x² dx <span class="cv-scene-auto">automatic</span></span>'
        )
        preview_line_2 = (
            'Lalu turunan <span class="cv-scene-math">d/dx (2x⁵) <span class="cv-scene-auto">otomatis</span></span> '
            'langsung muncul di HP mahasiswa.'
            if lang == "id"
            else 'Then derivative <span class="cv-scene-math">d/dx (2x⁵) <span class="cv-scene-auto">automatic</span></span> '
            'streams live to every student phone.'
        )
        st.markdown(
            f'<div class="cv-window-wrap">'
            f'  <div class="cv-heart-bubble">{HEART_SVG}</div>'
            f'  <div class="cv-window">'
            f'    <div class="cv-win-bar">'
            f'      <span class="cv-win-dots" aria-hidden="true">'
            f'        <span class="cv-dot-c"></span>'
            f'        <span class="cv-dot-s"></span>'
            f'        <span class="cv-dot-t"></span>'
            f'      </span>'
            f'      <span class="cv-win-bar-tag">LIVE CLASSROOM</span>'
            f'    </div>'
            f'    <div class="cv-win-scene">'
            f'      <span class="cv-scene-live">● {"TEKS LANGSUNG" if lang == "id" else "LIVE CAPTIONS"}</span>'
            f'      <div class="cv-scene-card">'
            f'        <div class="cv-scene-meta">#1 · 09:00:12 · KALK202</div>'
            f'        <div>{preview_line_1}</div>'
            f'      </div>'
            f'      <div class="cv-scene-card">'
            f'        <div class="cv-scene-meta">#2 · 09:00:18 · KATEX MATH</div>'
            f'        <div>{preview_line_2}</div>'
            f'      </div>'
            f'      <div class="cv-scene-footer">'
            f'        <span class="cv-scene-chip">🎙️ {"Mic Besar" if lang == "id" else "Big Live Mic"}</span>'
            f'        <span class="cv-scene-chip">📲 {"Scan QR Langsung" if lang == "id" else "Direct QR Join"}</span>'
            f'        <span class="cv-scene-chip">📄 DOCX & PDF</span>'
            f'      </div>'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with hero_r:
        hero_heading = (
            "Buat kuliah<br>makin jelas!"
            if lang == "id"
            else "Let's make<br>learning clear!"
        )
        hero_sub = (
            "Teks kuliah langsung dengan rumus KaTeX otomatis, glosarium dosen, dan QR ruangan instan."
            if lang == "id"
            else "Accessible live lecture captions with automatic KaTeX formulas, glossary matching & instant QR rooms."
        )
        st.markdown(
            f'<div class="cv-hero-headline">'
            f'  <h1>{hero_heading}</h1>'
            f'  <p>{hero_sub}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Signature Canva 2-Column Pill Action Hub
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            if st.button(
                f"🚀 {tr(lang, 'btn_create')}",
                key="hub_create",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.created_room = None
                navigate("create")
        with r1c2:
            if st.button(
                f"✨ {'Demo Cepat' if lang == 'id' else 'Quick Demo'}",
                key="hub_demo",
                use_container_width=True,
            ):
                is_id = lang == "id"
                demo = api.create_session(
                    {
                        "course_title": "Kalkulus II (Demo)" if is_id else "Calculus II (Demo)",
                        "course_code": "KALK2",
                        "topic": (
                            "Bab 4 — Integral Tentu & Konvergensi"
                            if is_id
                            else "Chapter 4 — Definite Integrals & Convergence"
                        ),
                        "date": datetime.date.today().isoformat(),
                        "language": "id-ID" if is_id else "en-US",
                        "glossary": [
                            "Integral Riemann",
                            "Eigenvalue",
                            "Transformasi Fourier",
                            "Konvergensi",
                            "Persamaan Diferensial",
                        ]
                        if is_id
                        else [
                            "Riemann Integral",
                            "Eigenvalue",
                            "Fourier Transform",
                            "Convergence",
                            "Differential Equation",
                        ],
                    }
                )
                navigate("host", demo["id"])

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            if st.button(
                f"🎙️ {tr(lang, 'nav_host')}",
                key="hub_host",
                use_container_width=True,
            ):
                navigate("host")
        with r2c2:
            if st.button(
                f"📱 {tr(lang, 'nav_student')}",
                key="hub_join",
                use_container_width=True,
            ):
                navigate("join")

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            if st.button(
                f"📄 {tr(lang, 'nav_transcript')}",
                key="hub_transcript",
                use_container_width=True,
            ):
                navigate("transcript")
        with r3c2:
            next_lang_hub = "en" if lang == "id" else "id"
            if st.button(
                f"🌐 {'English UI' if lang == 'id' else 'Bahasa ID'}",
                key="hub_lang",
                use_container_width=True,
            ):
                st.session_state.ui_lang = next_lang_hub
                st.rerun()

        st.markdown(
            f'<div class="cv-hero-stats">'
            f'  <span class="cv-stat-pill">🟢 {db_badge}</span>'
            f'  <span class="cv-stat-pill">🧮 {gem_badge}</span>'
            f'  <span class="cv-stat-pill">📚 {len(sessions)} {"Sesi" if lang == "id" else "Sessions"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Coral-Orange Quick Join Room Strip + Crisp White Window Input
    st.markdown(
        f'<div class="cv-join-strip">'
        f'  <div>'
        f'    <div class="cv-join-strip-title">📱 {"Punya Kode Ruangan dari Dosen?" if lang == "id" else "Have a Room Code from Your Lecturer?"}</div>'
        f'    <div class="cv-join-strip-sub">{"Masukkan kode ruangan atau tempel tautan untuk langsung membaca teks kuliah." if lang == "id" else "Enter the room code or paste a link to join captions immediately."}</div>'
        f'  </div>'
        f'  <span class="cv-win-dots" aria-hidden="true"><span class="cv-dot-c"></span><span class="cv-dot-s"></span><span class="cv-dot-t"></span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        jc1, jc2 = st.columns([7, 3])
        with jc1:
            join_raw = st.text_input(
                tr(lang, "btn_join"),
                placeholder=tr(lang, "join_placeholder"),
                label_visibility="collapsed",
            )
        with jc2:
            if st.button(
                "Gabung →" if lang == "id" else "Join →",
                type="primary",
                use_container_width=True,
            ):
                code = extract_session_code(join_raw)
                if code:
                    navigate("join", code)
                else:
                    st.warning(tr(lang, "join_placeholder"))

    st.markdown(
        f'<div class="cv-section-title"><span class="cv-section-dot"></span><span>{tr(lang, "past_sessions")}</span></div>',
        unsafe_allow_html=True,
    )
    if not sessions:
        st.info(tr(lang, "no_sessions"))
    else:
        for s in sessions:
            tile_bg, emoji = subject_visual(s["course_title"])
            status_cls = (
                "cv-pill-orange"
                if s["status"] == "live"
                else "cv-pill-yellow"
                if s["status"] == "paused"
                else "cv-pill-green"
            )
            status_lbl = (
                "● LANGSUNG"
                if s["status"] == "live"
                else "⏸ DIJEDA"
                if s["status"] == "paused"
                else "✓ SELESAI"
            )
            with st.container(border=True):
                left, right = st.columns([6, 4])
                with left:
                    st.markdown(
                        f'<div class="cv-course-row">'
                        f'  <div class="cv-course-tile" style="background:{tile_bg};">{emoji}</div>'
                        f'  <div>'
                        f'    <div class="cv-course-title">{s["course_title"]}</div>'
                        f'    <div class="cv-course-sub">{s["topic"]}</div>'
                        f'    <div class="cv-pill-row" style="margin:6px 0 0;">'
                        f'      <span class="cv-pill {status_cls}">{status_lbl}</span>'
                        f'      <span class="cv-pill cv-pill-blue">{s["id"]}</span>'
                        f'      <span class="cv-pill cv-pill-grey">💬 {s["caption_count"]}</span>'
                        f'      <span class="cv-pill cv-pill-grey">👥 {s["student_count"]}</span>'
                        f'    </div>'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with right:
                    st.write("")
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("🎙️ Host", key=f"h_{s['id']}", use_container_width=True):
                            navigate("host", s["id"])
                    with b2:
                        if st.button("📱 Masuk", key=f"j_{s['id']}", use_container_width=True):
                            navigate("join", s["id"])
                    with b3:
                        if st.button("📄", key=f"t_{s['id']}", use_container_width=True):
                            navigate("transcript", s["id"])


# ---------------------------------------------------------------------------
# PAGE 2: CREATE SESSION
# ---------------------------------------------------------------------------

elif st.session_state.page == "create":
    created = st.session_state.created_room
    if created:
        st.markdown(
            win_banner_html(
                "ROOM READY",
                f'<span class="cv-pill cv-pill-orange">🎉 RUANGAN SIAP</span>'
                f'<span class="cv-pill cv-pill-blue">{created["id"]}</span>',
                created["course_title"],
                f'{created["topic"]} · Bagikan QR di bawah ke mahasiswa sebelum mulai bicara!',
            ),
            unsafe_allow_html=True,
        )
        join_url = f"{public_app_url}/?page=join&session={created['id']}"
        mount_room_qr_card(
            session_id=created["id"],
            fallback_origin=public_app_url,
            server_join_url=join_url,
            qr_data_url=make_qr_data_url(join_url),
            ui_lang=lang,
        )
        st.write("")
        c_a, c_b = st.columns(2)
        with c_a:
            if st.button(
                f"🎙️ {tr(lang, 'open_host')}", type="primary", use_container_width=True
            ):
                sid = created["id"]
                st.session_state.created_room = None
                navigate("host", sid)
        with c_b:
            if st.button(f"📱 {tr(lang, 'open_student')}", use_container_width=True):
                sid = created["id"]
                st.session_state.created_room = None
                navigate("join", sid)
    else:
        st.markdown(
            win_banner_html(
                "CREATE SESSION",
                '<span class="cv-pill cv-pill-orange">✨ STUDIO DOSEN</span>',
                tr(lang, "create_title"),
                "Lengkapi mata kuliah & glosarium istilah agar transkripsi dan rumus semakin akurat."
                if lang == "id"
                else "Add course details and a glossary so captions & formulas stay ultra-accurate.",
            ),
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            up_col1, up_col2 = st.columns([6, 4])
            with up_col1:
                csv_file = st.file_uploader(
                    tr(lang, "upload_csv"), type=["csv", "txt"], key="glossary_csv"
                )
                if csv_file is not None:
                    imported = parse_csv_glossary(
                        csv_file.getvalue().decode("utf-8", errors="ignore")
                    )
                    existing = [
                        x.strip()
                        for x in st.session_state.glossary_draft.splitlines()
                        if x.strip()
                    ]
                    merged = list(dict.fromkeys(existing + imported))
                    st.session_state.glossary_draft = "\n".join(merged)
                    st.success(f"+{len(imported)} istilah ditambahkan dari CSV")
            with up_col2:
                st.write("")
                st.write("")
                if st.button(f"✨ {tr(lang, 'load_sample')}", use_container_width=True):
                    sample = [
                        "Integral Riemann",
                        "Eigenvalue",
                        "Transformasi Fourier",
                        "Konvergensi",
                        "Persamaan Diferensial",
                        "Asimtot",
                    ]
                    st.session_state.glossary_draft = "\n".join(sample)
                    st.rerun()

            with st.form("create_session_form"):
                col_a, col_b = st.columns([7, 3])
                with col_a:
                    course_title = st.text_input(
                        tr(lang, "course_title"),
                        placeholder="Kalkulus II / Kecerdasan Buatan",
                    )
                with col_b:
                    course_code = st.text_input(
                        tr(lang, "course_code"),
                        placeholder="KALK202",
                    )
                topic = st.text_input(
                    tr(lang, "topic"),
                    placeholder="Bab 4 — Integral Tentu & Teorema Dasar",
                )
                col_c, col_d = st.columns(2)
                with col_c:
                    sess_date = st.date_input(tr(lang, "date"), value=datetime.date.today())
                with col_d:
                    speech_lang = st.selectbox(
                        tr(lang, "speech_lang"),
                        options=["id-ID", "en-US"],
                        index=0 if lang == "id" else 1,
                    )
                glossary_text = st.text_area(
                    tr(lang, "glossary_label"),
                    value=st.session_state.glossary_draft,
                    height=120,
                    help=tr(lang, "glossary_help"),
                )
                submitted = st.form_submit_button(
                    f"🚀 {tr(lang, 'start_session')}",
                    type="primary",
                    use_container_width=True,
                )

        if submitted:
            if not course_title.strip() or not topic.strip():
                st.error("Nama Mata Kuliah & Topik wajib diisi.")
            else:
                terms = [t.strip() for t in glossary_text.splitlines() if t.strip()]
                room = api.create_session(
                    {
                        "course_title": course_title.strip(),
                        "course_code": course_code.strip() or None,
                        "topic": topic.strip(),
                        "date": sess_date.isoformat(),
                        "language": speech_lang,
                        "glossary": terms,
                    }
                )
                st.session_state.created_room = room
                st.session_state.active_session_id = room["id"]
                st.session_state.glossary_draft = ""
                st.rerun()


# ---------------------------------------------------------------------------
# PAGE 3: HOST LIVE SCREEN (Canva Retro Window Studio)
# ---------------------------------------------------------------------------

elif st.session_state.page == "host":
    sid = st.session_state.active_session_id
    if not sid:
        sessions = api.list_sessions()
        if sessions:
            sid = sessions[0]["id"]
            st.session_state.active_session_id = sid
    sess = api.get_session(sid) if sid else None

    if not sess:
        st.info("Pilih atau buat sesi terlebih dahulu.")
        if st.button(f"➕ {tr(lang, 'btn_create')}", type="primary"):
            navigate("create")
        st.stop()

    st.markdown(
        win_banner_html(
            f"HOST STUDIO · {sess['id']}",
            f'<span class="cv-pill cv-pill-blue">🎙️ {sess["id"]}</span>'
            f'<span class="cv-pill cv-pill-grey">📅 {sess["date"]}</span>'
            f'<span class="cv-pill cv-pill-orange">👥 {sess["student_count"]} online</span>',
            sess["course_title"],
            sess["topic"],
        ),
        unsafe_allow_html=True,
    )

    join_url = f"{public_app_url}/?page=join&session={sess['id']}"
    with st.expander(f"📲 Bagikan QR Code & Link Mahasiswa ({sess['id']})", expanded=False):
        mount_room_qr_card(
            session_id=sess["id"],
            fallback_origin=public_app_url,
            server_join_url=join_url,
            qr_data_url=make_qr_data_url(join_url),
            ui_lang=lang,
        )

    if not getattr(api, "is_embedded", False):
        render_host_live_console(
            session=sess,
            ws_base_url=backend_ws,
            http_base_url=public_backend_http,
            ui_lang=lang,
        )
    else:
        if "demo_cursor" not in st.session_state:
            st.session_state.demo_cursor = 0

        demo_lines = (
            [
                "Selamat pagi, hari ini kita bahas Integral Riemann dan Konvergensi deret.",
                "Perhatikan integral dari 5x² dan hitung de per de ex dari 2x pangkat 5.",
                "Pada metode eiginvalue kita menjumpai akar dari x tambah satu sebelum Transformasi Fourier.",
                "Cek papan sebelah kiri [unclear] lalu evaluasi limit x menuju nol dari sin x per x.",
            ]
            if sess["language"].startswith("id")
            else [
                "Good morning everyone, today we study Riemann Integral and Convergence.",
                "Consider the integral from zero to one of x squared dx and derivative of y with respect to x.",
                "In eiginvalue decomposition we encounter square root of x plus one before Fourier Transform.",
                "Check the board [unclear] then compute limit as x approaches zero of sin x over x.",
            ]
        )

        utterance, action = mount_host_mic_console(
            session_id=sess["id"],
            speech_lang=sess["language"],
            student_count=sess["student_count"],
            ui_lang=lang,
        )

        if utterance and isinstance(utterance, dict):
            uid = str(utterance.get("id", ""))
            txt = str(utterance.get("text", "")).strip()
            if uid and txt and uid not in st.session_state.seen_utterance_ids:
                st.session_state.seen_utterance_ids.add(uid)
                api.submit_caption(
                    sess["id"],
                    txt,
                    confidence=float(utterance.get("confidence", 0.92)),
                )

        if action and isinstance(action, dict):
            ats = int(action.get("ts", 0))
            if ats and ats != st.session_state.last_action_ts:
                st.session_state.last_action_ts = ats
                atype = action.get("type")
                if atype == "pause":
                    api.patch_session(sess["id"], {"status": "paused"})
                elif atype == "resume":
                    api.patch_session(sess["id"], {"status": "live"})
                elif atype == "language" and action.get("language"):
                    api.patch_session(sess["id"], {"language": action["language"]})
                elif atype == "demo_one":
                    line = demo_lines[st.session_state.demo_cursor % len(demo_lines)]
                    st.session_state.demo_cursor += 1
                    api.submit_caption(sess["id"], line)
                elif atype == "end":
                    api.patch_session(sess["id"], {"status": "ended"})
                    navigate("transcript", sess["id"])

        with st.container(border=True):
            with st.form("embedded_manual_caption", clear_on_submit=True):
                m1, m2 = st.columns([8, 2])
                with m1:
                    u_in = st.text_input(
                        "Caption",
                        placeholder=(
                            'Ketik kalimat uji (mis: "de per de ex dari 2x pangkat 5")...'
                            if lang == "id"
                            else 'Type a test sentence (e.g. "integral from zero to one of x squared dx")...'
                        ),
                        label_visibility="collapsed",
                    )
                with m2:
                    if st.form_submit_button(
                        "📤 Kirim" if lang == "id" else "📤 Send",
                        type="primary",
                        use_container_width=True,
                    ):
                        if u_in.strip():
                            api.submit_caption(sess["id"], u_in.strip())
                            st.rerun()

        st.markdown("#### 📝 Transkrip Berlangsung" if lang == "id" else "#### 📝 Live Transcript")
        host_caps = api.list_captions(sess["id"])
        if host_caps:
            render_katex_transcript_list(host_caps, set(), ui_lang=lang)
        else:
            st.info(
                "Belum ada teks. Tap tombol mikrofon besar di atas dan mulai berbicara, atau tekan ✨ Kirim 1 Baris Demo."
                if lang == "id"
                else "No captions yet. Tap the big microphone button above and start speaking, or tap ✨ Send 1 Demo Line."
            )

    with st.expander(f"🎧 {tr(lang, 'upload_audio_title')}", expanded=False):
        st.caption(tr(lang, "upload_audio_help"))
        audio_file = st.file_uploader(
            "Audio file",
            type=["mp3", "wav", "m4a", "ogg", "webm", "flac"],
            label_visibility="collapsed",
        )
        if audio_file is not None:
            st.audio(audio_file.getvalue())
            if st.button(
                f"🚀 {tr(lang, 'btn_transcribe_audio')}",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Mentranskripsi rekaman audio..."):
                    try:
                        added = api.transcribe_audio_file(
                            session_id=sess["id"],
                            filename=audio_file.name,
                            data=audio_file.getvalue(),
                            content_type=audio_file.type or "audio/mpeg",
                            language=sess["language"],
                        )
                        st.success(f"Berhasil mentranskripsi {len(added)} segmen!")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


# ---------------------------------------------------------------------------
# PAGE 4: STUDENT CAPTION SCREEN (Canva Live Class Reading Room)
# ---------------------------------------------------------------------------

elif st.session_state.page == "join":
    sid = st.session_state.active_session_id
    if not sid:
        st.markdown(
            win_banner_html(
                "JOIN CLASSROOM",
                '<span class="cv-pill cv-pill-orange">📱 RUANG BELAJAR</span>',
                tr(lang, "btn_join"),
                "Masukkan kode ruangan atau tempel link dari dosen."
                if lang == "id"
                else "Enter the room code or paste your lecturer link.",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            code_in = st.text_input(tr(lang, "join_placeholder"))
            if st.button(
                "Masuk Ruangan →" if lang == "id" else "Join Room →",
                type="primary",
                use_container_width=True,
            ):
                c = extract_session_code(code_in)
                if c:
                    navigate("join", c)
        st.stop()

    sess = api.get_session(sid)
    if not sess:
        st.error(
            f"Ruangan `{sid}` tidak ditemukan. Pastikan dosen sudah membuat sesi yang aktif."
            if lang == "id"
            else f"Room `{sid}` was not found. Make sure the lecturer created an active session."
        )
        if st.button(f"🏠 {tr(lang, 'nav_home')}", type="primary"):
            navigate("home")
        st.stop()

    status_pill = (
        '<span class="cv-pill cv-pill-yellow">⏸ DIJEDA</span>'
        if sess["status"] == "paused"
        else '<span class="cv-pill cv-pill-green">✓ SELESAI</span>'
        if sess["status"] == "ended"
        else '<span class="cv-pill cv-pill-orange">● LANGSUNG</span>'
    )
    st.markdown(
        win_banner_html(
            f"STUDENT ROOM · {sess['id']}",
            f'{status_pill}<span class="cv-pill cv-pill-blue">ROOM {sess["id"]}</span>',
            sess["course_title"],
            sess["topic"],
        ),
        unsafe_allow_html=True,
    )

    s_nav1, s_nav2 = st.columns(2)
    with s_nav1:
        if st.button(f"📄 {tr(lang, 'nav_transcript')}", use_container_width=True):
            navigate("transcript", sess["id"])
    with s_nav2:
        if st.button(f"🏠 {tr(lang, 'nav_home')}", use_container_width=True):
            navigate("home")

    if not getattr(api, "is_embedded", False):
        render_student_live_console(
            session=sess,
            ws_base_url=backend_ws,
            http_base_url=public_backend_http,
            student_id=st.session_state.student_id,
            ui_lang=lang,
        )
    else:
        from frontend.local_backend import touch_student_presence

        if "stu_pause_poll" not in st.session_state:
            st.session_state.stu_pause_poll = False

        with st.container(border=True):
            st.session_state.stu_pause_poll = st.toggle(
                "⏸ Jeda Auto-Refresh" if lang == "id" else "⏸ Pause Auto-Refresh",
                value=st.session_state.stu_pause_poll,
            )

        @st.fragment(
            run_every=None
            if st.session_state.stu_pause_poll
            else datetime.timedelta(seconds=1.5)
        )
        def _live_student_feed():
            touch_student_presence(sess["id"], st.session_state.student_id)
            live_sess = api.get_session(sess["id"])
            if not live_sess:
                st.error("Sesi tidak ditemukan.")
                return
            if live_sess["status"] == "ended":
                st.success(
                    "✅ **Sesi Telah Berakhir** — Klik tombol **Transkrip** di atas untuk membaca rangkuman dan ekspor `.docx` / `.pdf`."
                    if lang == "id"
                    else "✅ **Session Ended** — Tap **Transcript** above for the post-session summary and `.docx` / `.pdf` export."
                )
                return
            if live_sess["status"] == "paused":
                st.warning(
                    "⏸ Dosen sedang menjeda sesi sementara."
                    if lang == "id"
                    else "⏸ The lecturer has temporarily paused captions."
                )
            live_caps = api.list_captions(sess["id"])
            bks = api.list_bookmarks(sess["id"], st.session_state.student_id)
            bk_seqs = {b["transcript_seq"] for b in bks}
            if not live_caps:
                st.info(
                    "Terhubung ke ruangan! Menunggu dosen mulai berbicara…"
                    if lang == "id"
                    else "Connected to the room! Waiting for the lecturer to begin…"
                )
                return
            render_katex_transcript_list(
                live_caps, bk_seqs, ui_lang=lang, student_mode=True
            )
            latest_seq = live_caps[-1]["seq"]
            saved = latest_seq in bk_seqs
            lbl = (
                f"★ Hapus Bookmark Segmen #{latest_seq}"
                if saved
                else f"⭐ Simpan Bookmark Pribadi (#{latest_seq})"
            )
            if st.button(lbl, key=f"quick_bk_{latest_seq}", use_container_width=True):
                if saved:
                    api.delete_bookmark(sess["id"], latest_seq, st.session_state.student_id)
                else:
                    api.upsert_bookmark(sess["id"], latest_seq, st.session_state.student_id)
                st.rerun()

        _live_student_feed()


# ---------------------------------------------------------------------------
# PAGE 5: TRANSCRIPT, GEMINI SUMMARY & DOCX/PDF EXPORT (Catatan Belajar)
# ---------------------------------------------------------------------------

elif st.session_state.page == "transcript":
    sid = st.session_state.active_session_id
    if not sid:
        sessions = api.list_sessions()
        if sessions:
            sid = sessions[0]["id"]
            st.session_state.active_session_id = sid
    sess = api.get_session(sid) if sid else None

    if not sess:
        st.info("Belum ada sesi terpilih.")
        st.stop()

    captions = api.list_captions(sess["id"])
    bookmarks = api.list_bookmarks(sess["id"], st.session_state.student_id)
    bookmarked_seqs = {b["transcript_seq"] for b in bookmarks}

    st.markdown(
        win_banner_html(
            f"STUDY NOTES · {sess['id']}",
            f'<span class="cv-pill cv-pill-blue">📘 {sess["id"]}</span>'
            f'<span class="cv-pill cv-pill-grey">💬 {len(captions)} segmen</span>'
            f'<span class="cv-pill cv-pill-orange">⭐ {len(bookmarked_seqs)} bookmark</span>',
            sess["course_title"],
            f'{sess["topic"]} · 📅 {sess["date"]}',
        ),
        unsafe_allow_html=True,
    )

    if sess["glossary"]:
        chips = "".join(
            f'<span class="cv-pill cv-pill-white">🏷️ {g}</span>' for g in sess["glossary"]
        )
        st.markdown(f'<div class="cv-pill-row" style="margin-bottom:14px;">{chips}</div>', unsafe_allow_html=True)

    ex1, ex2, ex3, ex4 = st.columns(4)
    with ex1:
        if st.button(
            f"✨ {tr(lang, 'btn_summary')}",
            type="primary",
            disabled=len(captions) == 0,
            use_container_width=True,
        ):
            with st.spinner("Menyusun rangkuman belajar..."):
                res = api.generate_summary(sess["id"])
                sess["summary_md"] = res["summary_md"]
                st.toast(f"Summary ready ({res['provider']})")
                st.rerun()
    with ex2:
        if captions:
            docx_bytes = api.download_export(sess["id"], "docx")
            st.download_button(
                f"📘 {tr(lang, 'export_docx')}",
                data=docx_bytes,
                file_name=f"lecturelens-{sess['id'].lower()}-{sess['date']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    with ex3:
        if captions:
            pdf_bytes = api.download_export(sess["id"], "pdf")
            st.download_button(
                f"📕 {tr(lang, 'export_pdf')}",
                data=pdf_bytes,
                file_name=f"lecturelens-{sess['id'].lower()}-{sess['date']}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    with ex4:
        if captions:
            txt_bytes = api.download_export(sess["id"], "txt")
            st.download_button(
                f"📝 {tr(lang, 'export_txt')}",
                data=txt_bytes,
                file_name=f"lecturelens-{sess['id'].lower()}-{sess['date']}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    if sess.get("summary_md"):
        with st.container(border=True):
            st.markdown(
                f'<div class="cv-summary-header">✨ {tr(lang, "summary_heading")}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(sess["summary_md"])

    with st.container(border=True):
        f1, f2 = st.columns([7, 3])
        with f1:
            query = st.text_input(
                "Search",
                placeholder=tr(lang, "search_placeholder"),
                label_visibility="collapsed",
            )
        with f2:
            only_bk = st.checkbox(tr(lang, "only_bookmarks"), value=False)

    filtered = captions
    if only_bk:
        filtered = [c for c in filtered if c["seq"] in bookmarked_seqs]
    if query.strip():
        ql = query.strip().lower()
        filtered = [
            c
            for c in filtered
            if ql in c["raw_text"].lower()
            or ql in c["processed_text"].lower()
            or any(ql in f.get("latex", "").lower() for f in c.get("formulas") or [])
        ]

    if not filtered:
        st.info("Tidak ada baris transkrip yang cocok.")
    else:
        render_katex_transcript_list(filtered, bookmarked_seqs, ui_lang=lang)

st.divider()
st.caption(f"🔒 {tr(lang, 'privacy_note')}")
