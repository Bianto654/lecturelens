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
# Ruangguru-Inspired Indonesian EdTech Visual System
# Signature Turquoise (#00A5B5) + Sunny Orange (#FF7A00) + Warm Yellow (#FACC15)
# Soft Mint-Ice Canvas (#F2FAFB), Rounded 24-28px Cards, Friendly Nunito Font
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@600;800&family=Nunito:wght@500;600;700;800;900&display=swap');

  html, body, [class*="css"] {
    font-family: 'Nunito', system-ui, -apple-system, sans-serif !important;
  }
  .stApp {
    background:
      radial-gradient(circle at 8% 0%, rgba(0, 184, 201, 0.12) 0%, rgba(0, 184, 201, 0) 38%),
      radial-gradient(circle at 92% 6%, rgba(255, 122, 0, 0.09) 0%, rgba(255, 122, 0, 0) 34%),
      linear-gradient(180deg, #f0fafb 0%, #f7fbfc 50%, #eef7f9 100%);
  }
  .block-container {
    max-width: 980px !important;
    padding-top: 3.9rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
  }
  footer { visibility: hidden; }

  /* Friendly Pill Buttons (Ruangguru Turquoise Primary + Crisp White Secondary) */
  button[kind="primary"] {
    min-height: 50px !important;
    border-radius: 999px !important;
    font-weight: 800 !important;
    font-size: 14.5px !important;
    background: linear-gradient(135deg, #00c0d0 0%, #0095a8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(0, 155, 173, 0.28) !important;
    transition: transform 0.14s ease, filter 0.14s ease !important;
  }
  button[kind="primary"]:hover {
    filter: brightness(1.06);
    transform: translateY(-1px);
  }
  button[kind="secondary"] {
    min-height: 46px !important;
    border-radius: 999px !important;
    font-weight: 800 !important;
    font-size: 13.5px !important;
    background: #ffffff !important;
    border: 1.8px solid #cbe9ee !important;
    color: #0e4a56 !important;
    box-shadow: 0 3px 10px rgba(0, 130, 155, 0.06) !important;
    transition: all 0.14s ease !important;
  }
  button[kind="secondary"]:hover {
    border-color: #00a5b5 !important;
    background: #e6f8fa !important;
    color: #006b78 !important;
    transform: translateY(-1px);
  }

  /* Inputs & Form Containers */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1.8px solid #d2edf1 !important;
    border-radius: 24px !important;
    box-shadow: 0 8px 24px rgba(0, 145, 165, 0.07) !important;
  }
  input[type="text"], textarea, div[data-baseweb="select"] > div {
    border-radius: 14px !important;
  }

  /* Brand Header */
  .rg-brand {
    display: inline-flex;
    align-items: center;
    gap: 11px;
    font-size: 24px;
    font-weight: 900;
    color: #0b3c49;
    letter-spacing: -0.02em;
  }
  .rg-brand-accent {
    color: #00a5b5;
  }
  .rg-logo {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: linear-gradient(135deg, #00c4d4 0%, #008b9e 100%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 6px 16px rgba(0, 165, 181, 0.32);
  }

  /* Ruangguru Curved Turquoise Hero Banner */
  .rg-hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #00bfd0 0%, #0092a8 52%, #066387 100%);
    border-radius: 28px;
    padding: 28px 26px 26px;
    color: #ffffff;
    box-shadow: 0 16px 36px rgba(0, 130, 155, 0.24);
    margin: 10px 0 18px;
  }
  .rg-hero::before {
    content: '';
    position: absolute;
    top: -60px;
    right: -40px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.12);
    pointer-events: none;
  }
  .rg-hero::after {
    content: '';
    position: absolute;
    bottom: -75px;
    right: 90px;
    width: 170px;
    height: 170px;
    border-radius: 50%;
    background: rgba(250, 204, 21, 0.18);
    pointer-events: none;
  }
  .rg-hero-grid {
    position: relative;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
  }
  .rg-hero-copy {
    flex: 1;
    min-width: 250px;
  }
  .rg-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.35);
    color: #ffffff;
    padding: 5px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 12px;
    backdrop-filter: blur(6px);
  }
  .rg-hero h1 {
    font-size: 27px;
    font-weight: 900;
    line-height: 1.22;
    margin: 0 0 10px 0;
    color: #ffffff;
    letter-spacing: -0.02em;
  }
  .rg-hero p {
    font-size: 14.5px;
    font-weight: 600;
    line-height: 1.6;
    margin: 0;
    color: #e6fbfe;
    max-width: 560px;
  }
  .rg-hero-art {
    width: 118px;
    height: 118px;
    border-radius: 26px;
    background: rgba(255, 255, 255, 0.16);
    border: 2px solid rgba(255, 255, 255, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    backdrop-filter: blur(8px);
    box-shadow: 0 10px 24px rgba(0, 60, 80, 0.18);
  }
  .rg-hero-stats {
    position: relative;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 18px;
  }
  .rg-stat-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: rgba(255, 255, 255, 0.94);
    color: #0b4a56;
    padding: 7px 14px;
    border-radius: 999px;
    font-size: 12.5px;
    font-weight: 800;
    box-shadow: 0 4px 10px rgba(0, 50, 70, 0.12);
  }

  /* Room & Section Banners */
  .rg-room-banner {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #00a9b9 0%, #007d94 55%, #075375 100%);
    color: #ffffff;
    border-radius: 26px;
    padding: 20px 22px;
    margin: 8px 0 16px;
    box-shadow: 0 12px 28px rgba(0, 125, 148, 0.24);
  }
  .rg-room-banner::after {
    content: '';
    position: absolute;
    top: -40px;
    right: -30px;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.12);
    pointer-events: none;
  }
  .rg-room-banner h2 {
    margin: 8px 0 3px;
    font-size: 22px;
    font-weight: 900;
    color: #ffffff;
    line-height: 1.25;
  }
  .rg-room-banner .sub {
    font-size: 13.5px;
    font-weight: 600;
    color: #dcf7fb;
  }

  /* Feature Mini-Tiles on Home */
  .rg-action-banner {
    background: linear-gradient(135deg, #fff8ed 0%, #fff1dc 100%);
    border: 2px solid #fed7aa;
    border-radius: 22px;
    padding: 14px 18px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .rg-action-icon {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    background: linear-gradient(135deg, #ff8a00 0%, #ff5a1f 100%);
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    box-shadow: 0 6px 14px rgba(255, 106, 0, 0.28);
  }

  /* Color-Coded Ruangguru Subject Icon Tile for Past Sessions */
  .rg-course-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .rg-course-tile {
    width: 48px;
    height: 48px;
    border-radius: 16px;
    color: #ffffff;
    font-size: 21px;
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
  }
  .rg-course-title {
    font-size: 16px;
    font-weight: 900;
    color: #0f2937;
    line-height: 1.3;
  }
  .rg-course-sub {
    font-size: 13px;
    font-weight: 600;
    color: #527080;
    margin-top: 2px;
  }

  /* Pill Badges */
  .rg-pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin: 8px 0 12px;
  }
  .rg-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.35;
  }
  .rg-pill-teal   { background: #dcf6f9; color: #0b6874; }
  .rg-pill-orange { background: #ffedd5; color: #c2410c; }
  .rg-pill-yellow { background: #fef9c3; color: #854d0e; }
  .rg-pill-green  { background: #dcfce7; color: #166534; }
  .rg-pill-red    { background: #ffe4e6; color: #be123c; }
  .rg-pill-glass  { background: rgba(255,255,255,0.2); color: #ffffff; border: 1px solid rgba(255,255,255,0.3); }

  /* Summary Highlight Card */
  .rg-summary-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 16px;
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border: 1.5px solid #fcd34d;
    color: #78350f;
    font-weight: 900;
    font-size: 15px;
    margin-bottom: 10px;
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
    img = qr.make_image(fill_color="#0b3c49", back_color="#ffffff")
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
    ("linear-gradient(135deg, #00c0d0, #00829b)", "📐"),
    ("linear-gradient(135deg, #ff8a00, #f97316)", "🧪"),
    ("linear-gradient(135deg, #6366f1, #4338ca)", "💻"),
    ("linear-gradient(135deg, #10b981, #047857)", "🧬"),
    ("linear-gradient(135deg, #ec4899, #be185d)", "📚"),
]


def subject_visual(title: str) -> tuple[str, str]:
    idx = sum(ord(ch) for ch in title) % len(SUBJECT_PALETTES)
    return SUBJECT_PALETTES[idx]


HERO_SVG = """
<svg width="74" height="74" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="10" y="16" width="60" height="44" rx="14" fill="#FFFFFF" fill-opacity="0.96"/>
  <rect x="18" y="26" width="30" height="6" rx="3" fill="#00A5B5"/>
  <rect x="18" y="37" width="44" height="6" rx="3" fill="#0F2937" fill-opacity="0.82"/>
  <rect x="18" y="48" width="24" height="5" rx="2.5" fill="#FF7A00"/>
  <circle cx="60" cy="56" r="14" fill="#FF7A00" stroke="#FFFFFF" stroke-width="4"/>
  <path d="M55 56L58.5 59.5L66 52" stroke="#FFFFFF" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

LOGO_SVG = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="5" width="18" height="14" rx="4"/>
  <path d="M7 10h6"/>
  <path d="M7 14h10"/>
</svg>
"""


api = get_api_client()
lang = st.session_state.ui_lang
backend_http = get_backend_http_url()
public_backend_http = get_public_backend_http_url()
backend_ws = get_public_backend_ws_url()
public_app_url = resolve_public_app_url()
health = api.health()


# ---------------------------------------------------------------------------
# Brand Top Bar
# ---------------------------------------------------------------------------

hdr_l, hdr_r = st.columns([8, 2])
with hdr_l:
    st.markdown(
        f'<div class="rg-brand">'
        f'<span class="rg-logo">{LOGO_SVG}</span>'
        f'<span>Lecture<span class="rg-brand-accent">Lens</span></span>'
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

# Sleek Pill Navigation (hidden automatically when a student scans QR straight into a room)
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
# PAGE 1: HOME (Ruangguru EdTech Dashboard)
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

    eyebrow = (
        "✨ Ruang Kuliah Interaktif & Aksesibel"
        if lang == "id"
        else "✨ Interactive & Accessible Live Lectures"
    )

    st.markdown(
        f'<div class="rg-hero">'
        f'  <div class="rg-hero-grid">'
        f'    <div class="rg-hero-copy">'
        f'      <div class="rg-eyebrow">{eyebrow}</div>'
        f'      <h1>{tr(lang, "home_title")}</h1>'
        f'      <p>{tr(lang, "home_subtitle")}</p>'
        f'    </div>'
        f'    <div class="rg-hero-art">{HERO_SVG}</div>'
        f'  </div>'
        f'  <div class="rg-hero-stats">'
        f'    <span class="rg-stat-chip">🟢 {db_badge}</span>'
        f'    <span class="rg-stat-chip">🧮 {gem_badge}</span>'
        f'    <span class="rg-stat-chip">📚 {len(sessions)} {"Sesi Tersimpan" if lang == "id" else "Saved Sessions"}</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Primary Action Buttons
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            f"🚀 {tr(lang, 'btn_create')}", type="primary", use_container_width=True
        ):
            st.session_state.created_room = None
            navigate("create")
    with c2:
        if st.button(f"✨ {tr(lang, 'btn_demo')}", use_container_width=True):
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

    # Warm Orange-Accented Quick Join Room Card
    st.markdown(
        f'<div class="rg-action-banner">'
        f'  <div class="rg-action-icon">📱</div>'
        f'  <div>'
        f'    <div style="font-size:15px;font-weight:900;color:#7c2d12;">'
        f'      {"Punya Kode Ruangan dari Dosen?" if lang == "id" else "Have a Room Code from Your Lecturer?"}'
        f'    </div>'
        f'    <div style="font-size:13px;font-weight:600;color:#9a3412;">'
        f'      {"Masukkan kode ruangan atau tempel link untuk langsung baca teks kuliah." if lang == "id" else "Enter the room code or paste a link to join captions immediately."}'
        f'    </div>'
        f'  </div>'
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
            if st.button(f"Gabung →" if lang == "id" else "Join →", type="primary", use_container_width=True):
                code = extract_session_code(join_raw)
                if code:
                    navigate("join", code)
                else:
                    st.warning(tr(lang, "join_placeholder"))

    st.markdown(
        f"### 📖 {tr(lang, 'past_sessions')}"
    )
    if not sessions:
        st.info(tr(lang, "no_sessions"))
    else:
        for s in sessions:
            grad, emoji = subject_visual(s["course_title"])
            status_cls = (
                "rg-pill-green"
                if s["status"] == "live"
                else "rg-pill-yellow"
                if s["status"] == "paused"
                else "rg-pill-teal"
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
                        f'<div class="rg-course-row">'
                        f'  <div class="rg-course-tile" style="background:{grad};">{emoji}</div>'
                        f'  <div>'
                        f'    <div class="rg-course-title">{s["course_title"]}</div>'
                        f'    <div class="rg-course-sub">{s["topic"]}</div>'
                        f'    <div class="rg-pill-row" style="margin:6px 0 0;">'
                        f'      <span class="rg-pill {status_cls}">{status_lbl}</span>'
                        f'      <span class="rg-pill rg-pill-orange">{s["id"]}</span>'
                        f'      <span class="rg-pill rg-pill-teal">💬 {s["caption_count"]}</span>'
                        f'      <span class="rg-pill rg-pill-yellow">👥 {s["student_count"]}</span>'
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
            f'<div class="rg-room-banner">'
            f'<span class="rg-pill rg-pill-glass">🎉 RUANGAN SIAP</span> '
            f'<span class="rg-pill rg-pill-glass">{created["id"]}</span>'
            f'<h2>{created["course_title"]}</h2>'
            f'<div class="sub">{created["topic"]} · Bagikan QR di bawah ke mahasiswa sebelum mulai bicara!</div>'
            f'</div>',
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
            f'<div class="rg-room-banner">'
            f'<span class="rg-pill rg-pill-glass">✨ STUDIO DOSEN</span>'
            f'<h2>{tr(lang, "create_title")}</h2>'
            f'<div class="sub">{"Lengkapi mata kuliah & glosarium istilah agar transkripsi dan rumus semakin akurat." if lang == "id" else "Add course details and a glossary so captions & formulas stay ultra-accurate."}</div>'
            f'</div>',
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
# PAGE 3: HOST LIVE SCREEN (Ruangguru Studio Mode)
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
        f'<div class="rg-room-banner">'
        f'<span class="rg-pill rg-pill-glass">🎙️ STUDIO HOST · {sess["id"]}</span> '
        f'<span class="rg-pill rg-pill-glass">📅 {sess["date"]}</span> '
        f'<span class="rg-pill rg-pill-yellow">👥 {sess["student_count"]} online</span>'
        f'<h2>{sess["course_title"]}</h2>'
        f'<div class="sub">{sess["topic"]}</div>'
        f'</div>',
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
# PAGE 4: STUDENT CAPTION SCREEN (Ruangguru Live Class Reading Mode)
# ---------------------------------------------------------------------------

elif st.session_state.page == "join":
    sid = st.session_state.active_session_id
    if not sid:
        st.markdown(
            f'<div class="rg-room-banner">'
            f'<span class="rg-pill rg-pill-glass">📱 RUANG BELAJAR</span>'
            f'<h2>{tr(lang, "btn_join")}</h2>'
            f'<div class="sub">{"Masukkan kode ruangan atau tempel link dari dosen." if lang == "id" else "Enter the room code or paste your lecturer link."}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            code_in = st.text_input(tr(lang, "join_placeholder"))
            if st.button(f"Masuk Ruangan →" if lang == "id" else "Join Room →", type="primary", use_container_width=True):
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
        '<span class="rg-pill rg-pill-yellow">⏸ DIJEDA</span>'
        if sess["status"] == "paused"
        else '<span class="rg-pill rg-pill-green">✓ SELESAI</span>'
        if sess["status"] == "ended"
        else '<span class="rg-pill rg-pill-orange">● LANGSUNG</span>'
    )
    st.markdown(
        f'<div class="rg-room-banner">'
        f'{status_pill} <span class="rg-pill rg-pill-glass">Room {sess["id"]}</span>'
        f'<h2>{sess["course_title"]}</h2>'
        f'<div class="sub">{sess["topic"]}</div>'
        f'</div>',
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
        f'<div class="rg-room-banner">'
        f'<span class="rg-pill rg-pill-glass">📘 CATATAN BELAJAR · {sess["id"]}</span> '
        f'<span class="rg-pill rg-pill-glass">💬 {len(captions)} segmen</span> '
        f'<span class="rg-pill rg-pill-yellow">⭐ {len(bookmarked_seqs)} bookmark</span>'
        f'<h2>{sess["course_title"]}</h2>'
        f'<div class="sub">{sess["topic"]} · 📅 {sess["date"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if sess["glossary"]:
        chips = "".join(
            f'<span class="rg-pill rg-pill-teal">🏷️ {g}</span>' for g in sess["glossary"]
        )
        st.markdown(f'<div class="rg-pill-row">{chips}</div>', unsafe_allow_html=True)

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
                f'<div class="rg-summary-header">✨ {tr(lang, "summary_heading")}</div>',
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
