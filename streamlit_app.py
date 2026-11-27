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
# Figma Online Educational Platform Visual System (MKS Academy Aesthetic)
# Pure White Canvas (#FFFFFF) + Warm Peach Hero/Bands (#FFF1E8, #FFF7F2)
# Soft Apricot Decorative Arch (#FFD9C6) + Signature EdTech Orange (#F77E23)
# Deep Charcoal Headings (#333333) + Muted Copy (#666666) + Poppins Font
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Poppins', system-ui, -apple-system, sans-serif !important;
  }
  .stApp {
    background: #ffffff !important;
    color: #333333;
  }
  header[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.92) !important;
    backdrop-filter: blur(8px);
  }
  .block-container {
    max-width: 1040px !important;
    padding-top: 3.9rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
  }
  footer { visibility: hidden; }

  /* Primary Vibrant EdTech Orange Buttons (#F77E23) */
  button[kind="primary"],
  div[data-testid="stFormSubmitButton"] button {
    min-height: 46px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    background: #f77e23 !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 8px 20px rgba(247, 126, 35, 0.28) !important;
    transition: transform 0.14s ease, background 0.14s ease, box-shadow 0.14s ease !important;
  }
  button[kind="primary"] *,
  div[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
  }
  button[kind="primary"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover {
    background: #e36a12 !important;
    transform: translateY(-1px);
    box-shadow: 0 10px 24px rgba(247, 126, 35, 0.36) !important;
  }

  /* Secondary Floating White Buttons with Orange Text (Matches Figma 'Register' Button) */
  button[kind="secondary"],
  div[data-testid="stDownloadButton"] button {
    min-height: 44px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    background: #ffffff !important;
    border: 1px solid #ffe0cc !important;
    color: #f77e23 !important;
    box-shadow: 0 6px 18px rgba(51, 51, 51, 0.06) !important;
    transition: all 0.14s ease !important;
  }
  button[kind="secondary"] *,
  div[data-testid="stDownloadButton"] button * {
    color: #f77e23 !important;
  }
  button[kind="secondary"]:hover,
  div[data-testid="stDownloadButton"] button:hover {
    background: #fff7f2 !important;
    border-color: #f77e23 !important;
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(247, 126, 35, 0.14) !important;
  }

  /* Airy Pure White Cards with Soft Shadow (Matches Figma Course & Form Cards) */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1px solid #f2e6de !important;
    border-radius: 18px !important;
    box-shadow: 0 10px 30px rgba(51, 51, 51, 0.06) !important;
  }
  div[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #ffe2cf !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 20px rgba(51, 51, 51, 0.04) !important;
  }
  input[type="text"], textarea, div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    border: 1px solid #e5e7eb !important;
    background: #fafafa !important;
    color: #333333 !important;
  }
  input[type="text"]:focus, textarea:focus {
    border-color: #f77e23 !important;
    background: #ffffff !important;
  }

  /* Streamlit Tabs (Soft Peach + Active Vibrant Orange) */
  div[data-testid="stTabs"] [role="tablist"] {
    gap: 8px;
    border-bottom: 1px solid #f2e6de !important;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }
  div[data-testid="stTabs"] button[role="tab"] {
    background: #fff7f2 !important;
    color: #555555 !important;
    border: 1px solid #ffe2cf !important;
    border-radius: 999px !important;
    padding: 7px 18px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
  }
  div[data-testid="stTabs"] button[role="tab"] * {
    color: #555555 !important;
  }
  div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: #f77e23 !important;
    border-color: #f77e23 !important;
    box-shadow: 0 6px 16px rgba(247, 126, 35, 0.25) !important;
  }
  div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
    color: #ffffff !important;
  }
  div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none !important;
  }

  /* Brand Header (Matches Figma MKS Monogram Style) */
  .fg-brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 23px;
    font-weight: 800;
    color: #333333;
    letter-spacing: -0.03em;
    line-height: 1;
    padding: 4px 0;
  }
  .fg-brand-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: #fff1e8;
    border: 1.5px solid #ffd9c6;
  }
  .fg-brand-accent {
    color: #f77e23;
  }

  /* Signature Figma Warm Peach Hero with Soft Apricot Right Arch */
  .fg-hero {
    position: relative;
    overflow: hidden;
    background: #fff1e8;
    border-radius: 26px;
    padding: 34px 32px 32px;
    margin: 10px 0 22px;
    border: 1px solid #ffe3d1;
  }
  .fg-hero-arch {
    position: absolute;
    top: 0;
    right: 26px;
    width: 39%;
    height: 92%;
    background: #ffd9c6;
    border-radius: 0 0 180px 180px;
    pointer-events: none;
    z-index: 0;
  }
  .fg-hero-grid {
    position: relative;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 28px;
  }
  .fg-hero-copy {
    flex: 1.15;
    min-width: 270px;
  }
  .fg-hero h1 {
    font-size: 38px;
    font-weight: 800;
    line-height: 1.18;
    letter-spacing: -0.025em;
    color: #333333;
    margin: 0 0 14px 0;
  }
  .fg-accent-word {
    position: relative;
    display: inline-block;
    color: #f77e23;
    padding-bottom: 6px;
  }
  .fg-accent-word svg {
    position: absolute;
    left: 0;
    bottom: -2px;
    width: 100%;
    height: 10px;
  }
  .fg-hero p {
    font-size: 14.5px;
    font-weight: 400;
    line-height: 1.65;
    color: #666666;
    margin: 0 0 18px 0;
    max-width: 470px;
  }
  .fg-hero-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .fg-stat-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #ffffff;
    border: 1px solid #ffe0cc;
    color: #333333;
    padding: 6px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(247, 126, 35, 0.08);
  }

  /* Right Hero Dashed Oval Visual + Floating Stat Badge (Matches Figma Portrait Motif) */
  .fg-hero-visual {
    position: relative;
    flex: 0.85;
    min-width: 260px;
    display: flex;
    justify-content: center;
    padding: 8px 6px 14px;
  }
  .fg-dashed-frame {
    position: relative;
    width: 100%;
    max-width: 330px;
    border: 2px dashed #f5b793;
    border-radius: 28px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.45);
  }
  .fg-preview-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 16px;
    box-shadow: 0 14px 32px rgba(51, 51, 51, 0.08);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .fg-preview-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .fg-live-dot-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f77e23;
    color: #ffffff;
    border-radius: 999px;
    padding: 4px 11px;
    font-size: 11px;
    font-weight: 600;
  }
  .fg-preview-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #888888;
  }
  .fg-preview-line {
    background: #fff9f5;
    border: 1px solid #ffe4d2;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    line-height: 1.55;
    color: #333333;
  }
  .fg-preview-gloss {
    background: #fff1e8;
    border-bottom: 2px solid #f77e23;
    color: #d9620f;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 5px;
  }
  .fg-preview-math {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #ffffff;
    border: 1.5px solid #f77e23;
    border-radius: 8px;
    padding: 1px 8px;
    font-weight: 700;
    color: #333333;
  }
  .fg-preview-auto {
    background: #f77e23;
    color: #ffffff;
    border-radius: 999px;
    padding: 1px 6px;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
  }
  .fg-float-badge {
    position: absolute;
    bottom: -10px;
    left: -10px;
    background: #ffffff;
    border-radius: 14px;
    padding: 10px 14px;
    box-shadow: 0 12px 28px rgba(51, 51, 51, 0.12);
    border: 1px solid #ffe8d9;
    display: flex;
    align-items: center;
    gap: 10px;
    z-index: 3;
  }
  .fg-float-icon {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #fff1e8;
    color: #f77e23;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
  }
  .fg-float-title {
    font-size: 12px;
    font-weight: 700;
    color: #f77e23;
    line-height: 1.2;
  }
  .fg-float-sub {
    font-size: 10.5px;
    color: #555555;
    line-height: 1.2;
  }

  /* 3 Pastel Peach Feature Cards Row (Matches Figma Live Chat / Examination / Competition) */
  .fg-features-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    margin: 22px 0 26px;
  }
  .fg-feat-card {
    background: #fff7f2;
    border: 1px solid #ffe8d9;
    border-radius: 16px;
    padding: 20px 18px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .fg-feat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(247, 126, 35, 0.1);
  }
  .fg-feat-icon {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #ffe4d2;
    color: #f77e23;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    margin-bottom: 12px;
  }
  .fg-feat-title {
    font-size: 15px;
    font-weight: 700;
    color: #333333;
    margin-bottom: 5px;
  }
  .fg-feat-desc {
    font-size: 12.5px;
    line-height: 1.6;
    color: #666666;
  }

  /* Centered Figma Section Titles */
  .fg-section-head {
    text-align: center;
    margin: 26px 0 16px;
  }
  .fg-section-head h2 {
    font-size: 26px;
    font-weight: 700;
    color: #333333;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
  }
  .fg-section-head p {
    font-size: 13.5px;
    color: #666666;
    margin: 0;
  }

  /* Warm Peach Quick Join Callout Strip */
  .fg-join-band {
    background: #fff1e8;
    border: 1px solid #ffe0cc;
    border-radius: 18px;
    padding: 16px 20px;
    margin: 8px 0 12px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .fg-join-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .fg-join-icon {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: #f77e23;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
    flex-shrink: 0;
    box-shadow: 0 6px 14px rgba(247, 126, 35, 0.28);
  }
  .fg-join-title {
    font-size: 15px;
    font-weight: 700;
    color: #333333;
  }
  .fg-join-sub {
    font-size: 12.5px;
    color: #666666;
  }

  /* Room / Studio / Create / Transcript Warm Peach Page Banners */
  .fg-page-banner {
    position: relative;
    overflow: hidden;
    background: #fff1e8;
    border: 1px solid #ffe0cc;
    border-radius: 22px;
    padding: 22px 24px;
    margin: 10px 0 18px;
  }
  .fg-page-banner::after {
    content: '';
    position: absolute;
    top: 0;
    right: 24px;
    width: 180px;
    height: 85%;
    background: #ffd9c6;
    border-radius: 0 0 110px 110px;
    opacity: 0.72;
    pointer-events: none;
  }
  .fg-page-banner-inner {
    position: relative;
    z-index: 2;
  }
  .fg-page-banner h2 {
    margin: 8px 0 4px;
    font-size: 24px;
    font-weight: 700;
    color: #333333;
    letter-spacing: -0.02em;
    line-height: 1.25;
  }
  .fg-page-banner .sub {
    font-size: 13.5px;
    color: #666666;
  }

  /* Course / Session Row (Matches Figma Popular Courses Card Aesthetics) */
  .fg-course-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .fg-course-tile {
    width: 52px;
    height: 52px;
    border-radius: 14px;
    color: #ffffff;
    font-size: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 8px 18px rgba(247, 126, 35, 0.2);
  }
  .fg-course-title {
    font-size: 15.5px;
    font-weight: 700;
    color: #333333;
    line-height: 1.3;
  }
  .fg-course-sub {
    font-size: 12.5px;
    color: #666666;
    margin-top: 2px;
  }

  /* Clean Soft Pill Badges */
  .fg-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 8px 0 4px;
  }
  .fg-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    line-height: 1.35;
  }
  .fg-pill-orange { background: #f77e23; color: #ffffff; }
  .fg-pill-peach  { background: #ffe7d6; color: #c7570b; }
  .fg-pill-white  { background: #ffffff; color: #333333; border: 1px solid #ffe0cc; }
  .fg-pill-green  { background: #ecfdf5; color: #166534; border: 1px solid #bbf7d0; }
  .fg-pill-yellow { background: #fef3c7; color: #92400e; }
  .fg-pill-dark   { background: #333333; color: #ffffff; }

  /* Summary & Study Guide Header inside White Cards */
  .fg-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 15px;
    border-radius: 12px;
    background: #fff7f2;
    border: 1px solid #ffe2cf;
    color: #333333;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 12px;
  }

  /* Sleek Dark Footer (Matches Figma Black Bottom Footer) */
  .fg-footer {
    margin-top: 34px;
    background: #111111;
    color: #e5e5e5;
    border-radius: 20px;
    padding: 22px 26px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }
  .fg-footer-brand {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
  }
  .fg-footer-brand span { color: #f77e23; }
  .fg-footer-note {
    font-size: 12px;
    color: #b5b5b5;
    max-width: 620px;
    line-height: 1.55;
  }

  @media (max-width: 768px) {
    .fg-hero { padding: 24px 20px; }
    .fg-hero h1 { font-size: 29px; }
    .fg-hero-arch { width: 100%; height: 42%; top: auto; bottom: 0; right: 0; border-radius: 40px 40px 0 0; opacity: 0.55; }
    .fg-features-grid { grid-template-columns: 1fr; }
    .fg-float-badge { position: static; margin-top: 10px; }
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
    img = qr.make_image(fill_color="#333333", back_color="#ffffff")
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
    ("linear-gradient(135deg, #ff9642, #f77e23)", "📐"),
    ("linear-gradient(135deg, #333333, #1e1e1e)", "💻"),
    ("linear-gradient(135deg, #fb923c, #ea580c)", "🧪"),
    ("linear-gradient(135deg, #f59e0b, #d97706)", "🧬"),
    ("linear-gradient(135deg, #4b5563, #1f2937)", "📚"),
]


def subject_visual(title: str) -> tuple[str, str]:
    idx = sum(ord(ch) for ch in title) % len(SUBJECT_PALETTES)
    return SUBJECT_PALETTES[idx]


BRAND_SVG = """
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M4 5V19H11" stroke="#333333" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M13 5V19H20" stroke="#F77E23" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

UNDERLINE_SVG = """
<svg viewBox="0 0 180 12" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" aria-hidden="true">
  <path d="M3 9C48 2.5 128 2 177 7.5" stroke="#F77E23" stroke-width="4" stroke-linecap="round"/>
</svg>
"""


def page_banner_html(pills_html: str, title: str, subtitle: str) -> str:
    return (
        f'<div class="fg-page-banner">'
        f'  <div class="fg-page-banner-inner">'
        f'    <div class="fg-pill-row" style="margin:0 0 6px;">{pills_html}</div>'
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
# Brand Top Bar (Matches Figma MKS Top Header)
# ---------------------------------------------------------------------------

hdr_l, hdr_r = st.columns([8, 2])
with hdr_l:
    st.markdown(
        f'<div class="fg-brand">'
        f'  <span class="fg-brand-mark">{BRAND_SVG}</span>'
        f'  <span>Lecture<span class="fg-brand-accent">Lens</span></span>'
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

# Clean Horizontal Navigation (hidden automatically when a student scans QR straight into a room)
if not (st.session_state.student_qr_entry and st.session_state.page == "join"):
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
# PAGE 1: HOME (Figma Online Educational Platform Layout)
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

    hero_h1 = (
        f'Teks Kuliah Langsung<br>untuk Masa <span class="fg-accent-word">Depan{UNDERLINE_SVG}</span>'
        if lang == "id"
        else f'Accessible Live Captions<br>for the <span class="fg-accent-word">Future{UNDERLINE_SVG}</span>'
    )
    hero_sub = (
        "Dosen berbicara dari satu perangkat, teks real-time dengan rumus KaTeX otomatis, glosarium kuliah, dan Study Guide PDF rapi langsung hadir di HP setiap mahasiswa."
        if lang == "id"
        else "Speak from one host device while live captions, automatic KaTeX math, glossary matching, and polished AI study guides stream directly to every student phone."
    )
    preview_line_1 = (
        'Hari ini kita bahas <span class="fg-preview-gloss">Integral Riemann</span> dan '
        '<span class="fg-preview-math">∫ 5x² dx <span class="fg-preview-auto">otomatis</span></span>'
        if lang == "id"
        else 'Today we cover <span class="fg-preview-gloss">Riemann Integral</span> and '
        '<span class="fg-preview-math">∫ 5x² dx <span class="fg-preview-auto">auto</span></span>'
    )
    preview_line_2 = (
        'Lalu turunan <span class="fg-preview-math">d/dx (2x⁵) <span class="fg-preview-auto">otomatis</span></span> '
        'disusun rapi jadi panduan belajar.'
        if lang == "id"
        else 'Then derivative <span class="fg-preview-math">d/dx (2x⁵) <span class="fg-preview-auto">auto</span></span> '
        'is polished into clean study paragraphs.'
    )

    st.markdown(
        f'<div class="fg-hero">'
        f'  <div class="fg-hero-arch" aria-hidden="true"></div>'
        f'  <div class="fg-hero-grid">'
        f'    <div class="fg-hero-copy">'
        f'      <h1>{hero_h1}</h1>'
        f'      <p>{hero_sub}</p>'
        f'      <div class="fg-hero-stats">'
        f'        <span class="fg-stat-chip">🟢 {db_badge}</span>'
        f'        <span class="fg-stat-chip">🧮 {gem_badge}</span>'
        f'        <span class="fg-stat-chip">📚 {len(sessions)} {"Sesi Tersimpan" if lang == "id" else "Saved Sessions"}</span>'
        f'      </div>'
        f'    </div>'
        f'    <div class="fg-hero-visual">'
        f'      <div class="fg-dashed-frame">'
        f'        <div class="fg-preview-card">'
        f'          <div class="fg-preview-top">'
        f'            <span class="fg-live-dot-pill">● {"LANGSUNG" if lang == "id" else "LIVE"}</span>'
        f'            <span class="fg-preview-meta">KALK-2026</span>'
        f'          </div>'
        f'          <div class="fg-preview-line">{preview_line_1}</div>'
        f'          <div class="fg-preview-line">{preview_line_2}</div>'
        f'        </div>'
        f'        <div class="fg-float-badge">'
        f'          <div class="fg-float-icon">✨</div>'
        f'          <div>'
        f'            <div class="fg-float-title">{"Study Guide & QR" if lang == "id" else "AI Study Guide"}</div>'
        f'            <div class="fg-float-sub">{"PDF · DOCX · KaTeX" if lang == "id" else "Instant QR · PDF · DOCX"}</div>'
        f'          </div>'
        f'        </div>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Hero Action CTAs (Primary Orange + Crisp White Secondary)
    cta1, cta2 = st.columns(2)
    with cta1:
        if st.button(
            f"🚀 {tr(lang, 'btn_create')}",
            key="home_create",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.created_room = None
            navigate("create")
    with cta2:
        if st.button(
            f"✨ {tr(lang, 'btn_demo')}",
            key="home_demo",
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

    # 3 Soft Peach Feature Cards (Matching Figma Live Chat / Examination / Competition Row)
    if lang == "id":
        feats = [
            ("🎙️", "Teks Kuliah Langsung", "Tombol mikrofon besar ramah HP & sinkronisasi real-time via QR ruangan langsung."),
            ("🧮", "KaTeX & Glosarium", "Rumus integral, turunan, pangkat, serta istilah teknis dosen terdeteksi otomatis."),
            ("📖", "Study Guide Akademik", "Transkrip mentah otomatis dirapikan jadi paragraf utuh siap ekspor PDF & DOCX."),
        ]
    else:
        feats = [
            ("🎙️", "Live Captions", "Large touch-friendly host mic & instant student access via direct room QR scan."),
            ("🧮", "KaTeX & Glossary", "Spoken integrals, derivatives, powers, and course jargon formatted automatically."),
            ("📖", "AI Study Guide", "Post-session async refinement turns choppy speech into polished PDF & DOCX notes."),
        ]

    feat_cards_html = "".join(
        f'<div class="fg-feat-card">'
        f'  <div class="fg-feat-icon">{icon}</div>'
        f'  <div class="fg-feat-title">{title}</div>'
        f'  <div class="fg-feat-desc">{desc}</div>'
        f'</div>'
        for icon, title, desc in feats
    )
    st.markdown(f'<div class="fg-features-grid">{feat_cards_html}</div>', unsafe_allow_html=True)

    # Quick Join Room Section (Warm Peach Callout + Floating White Form Card)
    st.markdown(
        f'<div class="fg-join-band">'
        f'  <div class="fg-join-left">'
        f'    <div class="fg-join-icon">📱</div>'
        f'    <div>'
        f'      <div class="fg-join-title">{"Punya Kode Ruangan dari Dosen?" if lang == "id" else "Have a Room Code from Your Lecturer?"}</div>'
        f'      <div class="fg-join-sub">{"Masukkan kode ruangan atau tempel link untuk langsung baca teks kuliah real-time." if lang == "id" else "Enter the room code or paste a link to open live lecture captions immediately."}</div>'
        f'    </div>'
        f'  </div>'
        f'  <span class="fg-pill fg-pill-white">📲 Direct Room Join</span>'
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
                "Gabung Ruangan →" if lang == "id" else "Join Room →",
                type="primary",
                use_container_width=True,
            ):
                code = extract_session_code(join_raw)
                if code:
                    navigate("join", code)
                else:
                    st.warning(tr(lang, "join_placeholder"))

    # Centered Section Header (Matching Figma "Explore Our Popular Course")
    st.markdown(
        f'<div class="fg-section-head">'
        f'  <h2>{tr(lang, "past_sessions")}</h2>'
        f'  <p>{"Lanjutkan sesi kuliah aktif atau buka Study Guide & ekspor catatan belajar." if lang == "id" else "Resume a live lecture room or open your polished Study Guide & exports."}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if not sessions:
        st.info(tr(lang, "no_sessions"))
    else:
        for s in sessions:
            tile_bg, emoji = subject_visual(s["course_title"])
            status_cls = (
                "fg-pill-orange"
                if s["status"] == "live"
                else "fg-pill-yellow"
                if s["status"] == "paused"
                else "fg-pill-green"
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
                        f'<div class="fg-course-row">'
                        f'  <div class="fg-course-tile" style="background:{tile_bg};">{emoji}</div>'
                        f'  <div>'
                        f'    <div class="fg-course-title">{s["course_title"]}</div>'
                        f'    <div class="fg-course-sub">{s["topic"]}</div>'
                        f'    <div class="fg-pill-row" style="margin:6px 0 0;">'
                        f'      <span class="fg-pill {status_cls}">{status_lbl}</span>'
                        f'      <span class="fg-pill fg-pill-peach">{s["id"]}</span>'
                        f'      <span class="fg-pill fg-pill-white">💬 {s["caption_count"]}</span>'
                        f'      <span class="fg-pill fg-pill-white">👥 {s["student_count"]}</span>'
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
            page_banner_html(
                f'<span class="fg-pill fg-pill-orange">🎉 RUANGAN SIAP</span>'
                f'<span class="fg-pill fg-pill-white">{created["id"]}</span>',
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
            page_banner_html(
                '<span class="fg-pill fg-pill-orange">✨ STUDIO DOSEN</span>',
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
# PAGE 3: HOST LIVE SCREEN
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
        page_banner_html(
            f'<span class="fg-pill fg-pill-orange">🎙️ HOST · {sess["id"]}</span>'
            f'<span class="fg-pill fg-pill-white">📅 {sess["date"]}</span>'
            f'<span class="fg-pill fg-pill-peach">👥 {sess["student_count"]} online</span>',
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
            render_katex_transcript_list(host_caps, ui_lang=lang)
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
# PAGE 4: STUDENT CAPTION SCREEN
# ---------------------------------------------------------------------------

elif st.session_state.page == "join":
    sid = st.session_state.active_session_id
    if not sid:
        st.markdown(
            page_banner_html(
                '<span class="fg-pill fg-pill-orange">📱 RUANG MAHASISWA</span>',
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
        '<span class="fg-pill fg-pill-yellow">⏸ DIJEDA</span>'
        if sess["status"] == "paused"
        else '<span class="fg-pill fg-pill-green">✓ SELESAI</span>'
        if sess["status"] == "ended"
        else '<span class="fg-pill fg-pill-orange">● LANGSUNG</span>'
    )
    st.markdown(
        page_banner_html(
            f'{status_pill}<span class="fg-pill fg-pill-white">Room {sess["id"]}</span>',
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
                    "✅ **Sesi Telah Berakhir** — Klik tombol **Transkrip** di atas untuk membaca Study Guide rapi & ekspor `.docx` / `.pdf`."
                    if lang == "id"
                    else "✅ **Session Ended** — Tap **Transcript** above for your polished Study Guide and `.docx` / `.pdf` export."
                )
                return
            if live_sess["status"] == "paused":
                st.warning(
                    "⏸ Dosen sedang menjeda sesi sementara."
                    if lang == "id"
                    else "⏸ The lecturer has temporarily paused captions."
                )
            live_caps = api.list_captions(sess["id"])
            if not live_caps:
                st.info(
                    "Terhubung ke ruangan! Menunggu dosen mulai berbicara…"
                    if lang == "id"
                    else "Connected to the room! Waiting for the lecturer to begin…"
                )
                return
            render_katex_transcript_list(live_caps, ui_lang=lang, student_mode=True)

        _live_student_feed()


# ---------------------------------------------------------------------------
# PAGE 5: TRANSCRIPT, ASYNC STUDY GUIDE, GEMINI SUMMARY & DOCX/PDF EXPORT
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
    polish_status = sess.get("polish_status") or "idle"

    polish_pill = (
        '<span class="fg-pill fg-pill-green">✨ Study Guide Siap</span>'
        if polish_status == "ready"
        else '<span class="fg-pill fg-pill-yellow">⏳ Merapikan Paragraf...</span>'
        if polish_status == "processing"
        else '<span class="fg-pill fg-pill-white">📝 Raw Log</span>'
    )

    st.markdown(
        page_banner_html(
            f'<span class="fg-pill fg-pill-orange">📘 {sess["id"]}</span>'
            f'<span class="fg-pill fg-pill-white">💬 {len(captions)} segmen</span>'
            f'{polish_pill}',
            sess["course_title"],
            f'{sess["topic"]} · 📅 {sess["date"]}',
        ),
        unsafe_allow_html=True,
    )

    if sess["glossary"]:
        chips = "".join(
            f'<span class="fg-pill fg-pill-peach">🏷️ {g}</span>' for g in sess["glossary"]
        )
        st.markdown(f'<div class="fg-pill-row" style="margin-bottom:14px;">{chips}</div>', unsafe_allow_html=True)

    # Lightweight async watcher while background post-session polish is running
    if polish_status == "processing":
        @st.fragment(run_every=datetime.timedelta(seconds=2.0))
        def _watch_polish_status():
            fresh = api.get_session(sess["id"])
            if fresh and fresh.get("polish_status") != "processing":
                st.rerun()
            st.info(f"⏳ {tr(lang, 'polish_processing')}")

        _watch_polish_status()

    ai1, ai2 = st.columns(2)
    with ai1:
        if st.button(
            f"🪄 {tr(lang, 'btn_polish')}",
            type="primary",
            disabled=len(captions) == 0,
            use_container_width=True,
        ):
            with st.spinner("Menyusun paragraf akademik & membersihkan kata pengisi..."):
                res = api.polish_transcript(sess["id"], wait=True)
                sess["polished_transcript_md"] = res.get("polished_transcript_md")
                sess["polish_status"] = res.get("polish_status", "ready")
                sess["polish_provider"] = res.get("provider")
                st.toast(f"Study Guide siap ({res.get('provider') or 'ok'})")
                st.rerun()
    with ai2:
        if st.button(
            f"✨ {tr(lang, 'btn_summary')}",
            disabled=len(captions) == 0,
            use_container_width=True,
        ):
            with st.spinner("Menyusun rangkuman belajar..."):
                res = api.generate_summary(sess["id"])
                sess["summary_md"] = res["summary_md"]
                st.toast(f"Summary ready ({res['provider']})")
                st.rerun()

    if captions:
        ex1, ex2, ex3 = st.columns(3)
        with ex1:
            docx_bytes = api.download_export(sess["id"], "docx")
            st.download_button(
                f"📘 {tr(lang, 'export_docx')}",
                data=docx_bytes,
                file_name=f"lecturelens-{sess['id'].lower()}-{sess['date']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with ex2:
            pdf_bytes = api.download_export(sess["id"], "pdf")
            st.download_button(
                f"📕 {tr(lang, 'export_pdf')}",
                data=pdf_bytes,
                file_name=f"lecturelens-{sess['id'].lower()}-{sess['date']}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with ex3:
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
                f'<div class="fg-card-header"><span>✨ {tr(lang, "summary_heading")}</span></div>',
                unsafe_allow_html=True,
            )
            st.markdown(sess["summary_md"])

    tab_guide, tab_raw = st.tabs(
        [tr(lang, "tab_study_guide"), tr(lang, "tab_raw_log")]
    )

    with tab_guide:
        if sess.get("polished_transcript_md"):
            provider_lbl = sess.get("polish_provider") or "Academic Editor"
            with st.container(border=True):
                st.markdown(
                    f'<div class="fg-card-header">'
                    f'  <span>📖 {tr(lang, "polish_heading")}</span>'
                    f'  <span class="fg-pill fg-pill-peach">{provider_lbl}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(sess["polished_transcript_md"])
        elif polish_status == "processing":
            st.info(f"⏳ {tr(lang, 'polish_processing')}")
        else:
            st.info(tr(lang, "polish_empty_cta"))

    with tab_raw:
        with st.container(border=True):
            query = st.text_input(
                "Search",
                placeholder=tr(lang, "search_placeholder"),
                label_visibility="collapsed",
            )

        filtered = captions
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
            render_katex_transcript_list(filtered, ui_lang=lang)

st.markdown(
    f'<div class="fg-footer">'
    f'  <div class="fg-footer-brand">Lecture<span>Lens</span></div>'
    f'  <div class="fg-footer-note">🔒 {tr(lang, "privacy_note")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)
