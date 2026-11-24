from __future__ import annotations

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

# Mobile-first clean accessible CSS (large 48px tap targets, WCAG AA contrast)
st.markdown(
    """
<style>
  .block-container { max-width: 1080px; padding-top: 1.2rem; padding-bottom: 3rem; }
  button[kind="primary"], button[kind="secondary"] { min-height: 46px; border-radius: 12px !important; font-weight: 700 !important; }
  .ll-pill {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; margin-right: 6px; margin-bottom: 4px;
  }
  .ll-pill-blue { background: #dbeafe; color: #1e3a8a; }
  .ll-pill-green { background: #dcfce7; color: #14532d; }
  .ll-pill-amber { background: #fef3c7; color: #78350f; }
  .ll-pill-slate { background: #e2e8f0; color: #1e293b; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session State & Query Params Initialization
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

# Honor deep links like ?page=join&session=KALK-4821 from QR codes
qp = st.query_params
if "page" in qp and qp["page"] in ("home", "create", "host", "join", "transcript"):
    st.session_state.page = qp["page"]
if "session" in qp and qp["session"]:
    st.session_state.active_session_id = str(qp["session"]).strip().upper()


def navigate(page: str, session_id: str = "") -> None:
    st.session_state.page = page
    if session_id:
        st.session_state.active_session_id = session_id.upper()
    st.query_params["page"] = page
    if st.session_state.active_session_id and page in ("host", "join", "transcript"):
        st.query_params["session"] = st.session_state.active_session_id
    elif "session" in st.query_params and page in ("home", "create"):
        del st.query_params["session"]
    st.rerun()


def extract_session_code(raw: str) -> str:
    txt = raw.strip()
    if not txt:
        return ""
    if "://" in txt or "session=" in txt or "/join/" in txt:
        parsed = urlparse(txt if "://" in txt else f"https://example.com/{txt.lstrip('/')}")
        qs = parse_qs(parsed.query)
        if qs.get("session"):
            return qs["session"][0].strip().upper()
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            return parts[-1].strip().upper()
    return re.sub(r"[^A-Za-z0-9_-]", "", txt).upper()


def make_qr_png(url: str) -> bytes:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
    configured = get_public_app_url()
    if configured and "localhost" not in configured and "127.0.0.1" not in configured:
        return configured
    # Automatically detect deployed Streamlit Community Cloud domain from request headers!
    try:
        host = st.context.headers.get("host", "")
        if host and "localhost" not in host and "127.0.0.1" not in host:
            return f"https://{host}"
    except Exception:
        pass
    return configured


api = get_api_client()
lang = st.session_state.ui_lang
backend_http = get_backend_http_url()
public_backend_http = get_public_backend_http_url()
backend_ws = get_public_backend_ws_url()
public_app_url = resolve_public_app_url()
health = api.health()


# ---------------------------------------------------------------------------
# Top Header & Navigation Bar
# ---------------------------------------------------------------------------

h_col1, h_col2, h_col3 = st.columns([5, 3, 2])
with h_col1:
    st.markdown("### 🎓 LectureLens")
    st.caption(tr(lang, "app_tagline"))
with h_col2:
    if health:
        db_badge = (
            "Supabase PostgreSQL"
            if health.get("database") == "supabase-postgresql"
            else "SQLite Local"
        )
        gem_badge = (
            f"Gemini {health.get('gemini_model', 'Flash')}"
            if health.get("gemini_configured")
            else "Rules Math Engine"
        )
        stt_info = health.get("stt", {})
        stt_badge = f"Faster-Whisper ({stt_info.get('model_size', 'large-v3-turbo')}) + Silero VAD"
        st.markdown(
            f'<span class="ll-pill ll-pill-green">● {db_badge}</span>'
            f'<span class="ll-pill ll-pill-blue">{gem_badge}</span>'
            f'<span class="ll-pill ll-pill-slate">{stt_badge}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.error(tr(lang, "backend_offline", url=backend_http))
with h_col3:
    next_lang = "en" if lang == "id" else "id"
    if st.button(f"🌐 {lang.upper()} → {next_lang.upper()}", use_container_width=True):
        st.session_state.ui_lang = next_lang
        st.rerun()

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
        if st.button(label, key=f"nav_{p_key}", type=btn_type, use_container_width=True):
            navigate(p_key)

st.divider()

if not health:
    st.stop()


# ---------------------------------------------------------------------------
# PAGE 1: HOME
# ---------------------------------------------------------------------------

if st.session_state.page == "home":
    st.header(tr(lang, "home_title"))
    st.write(tr(lang, "home_subtitle"))

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(f"➕ {tr(lang, 'btn_create')}", type="primary", use_container_width=True):
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
    with c3:
        join_raw = st.text_input(
            tr(lang, "btn_join"),
            placeholder=tr(lang, "join_placeholder"),
            label_visibility="collapsed",
        )
        if st.button(f"📱 {tr(lang, 'btn_join')}", use_container_width=True):
            code = extract_session_code(join_raw)
            if code:
                navigate("join", code)
            else:
                st.warning(tr(lang, "join_placeholder"))

    st.subheader(f"🕒 {tr(lang, 'past_sessions')}")
    sessions = api.list_sessions()
    if not sessions:
        st.info(tr(lang, "no_sessions"))
    else:
        for s in sessions:
            with st.container(border=True):
                left, right = st.columns([6, 4])
                with left:
                    st.markdown(
                        f"**{s['course_title']}** — {s['topic']}  \n"
                        f"`{s['id']}` · 📅 {s['date']} · status: **{s['status']}** · "
                        f"💬 {s['caption_count']} segmen · 👥 {s['student_count']} online"
                    )
                with right:
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("🎙️ Host", key=f"h_{s['id']}", use_container_width=True):
                            navigate("host", s["id"])
                    with b2:
                        if st.button("📱 Join", key=f"j_{s['id']}", use_container_width=True):
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
        st.success(f"✅ {tr(lang, 'room_ready')}: **{created['id']}**")
        join_url = f"{public_app_url}/?page=join&session={created['id']}"
        q_col, info_col = st.columns([4, 6])
        with q_col:
            st.image(make_qr_png(join_url), caption=f"Room {created['id']}", width=240)
        with info_col:
            st.markdown(f"### {created['course_title']}")
            st.write(created["topic"])
            st.code(join_url, language=None)
            st.caption(f"Glossary ({len(created['glossary'])}): {', '.join(created['glossary']) or '-'}")
            c_a, c_b = st.columns(2)
            with c_a:
                if st.button(f"🎙️ {tr(lang, 'open_host')}", type="primary", use_container_width=True):
                    sid = created["id"]
                    st.session_state.created_room = None
                    navigate("host", sid)
            with c_b:
                if st.button(f"📱 {tr(lang, 'open_student')}", use_container_width=True):
                    sid = created["id"]
                    st.session_state.created_room = None
                    navigate("join", sid)
    else:
        st.header(tr(lang, "create_title"))

        up_col1, up_col2 = st.columns([6, 4])
        with up_col1:
            csv_file = st.file_uploader(
                tr(lang, "upload_csv"), type=["csv", "txt"], key="glossary_csv"
            )
            if csv_file is not None:
                imported = parse_csv_glossary(csv_file.getvalue().decode("utf-8", errors="ignore"))
                existing = [
                    x.strip() for x in st.session_state.glossary_draft.splitlines() if x.strip()
                ]
                merged = list(dict.fromkeys(existing + imported))
                st.session_state.glossary_draft = "\n".join(merged)
                st.success(f"+{len(imported)} terms loaded from CSV")
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
                height=130,
                help=tr(lang, "glossary_help"),
            )
            submitted = st.form_submit_button(
                f"🚀 {tr(lang, 'start_session')}",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not course_title.strip() or not topic.strip():
                st.error("Course Title & Topic are required.")
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

    top_l, top_r = st.columns([7, 3])
    with top_l:
        st.header(f"🎙️ {sess['course_title']}")
        st.caption(f"{sess['topic']} · Room `{sess['id']}` · 📅 {sess['date']} · 🌐 {sess['language']}")
    with top_r:
        if st.button(f"📄 {tr(lang, 'nav_transcript')}", use_container_width=True):
            navigate("transcript", sess["id"])

    join_url = f"{public_app_url}/?page=join&session={sess['id']}"
    with st.expander(f"📲 Share QR Code & Join Link (`{sess['id']}`)", expanded=False):
        q1, q2 = st.columns([3, 7])
        with q1:
            st.image(make_qr_png(join_url), width=190)
        with q2:
            st.code(join_url, language=None)
            st.caption(f"Glossary hotwords: {', '.join(sess['glossary']) or '-'}")

    # Real-Time Host Console: FastAPI WebSocket mode OR Standalone Streamlit Cloud mode
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
                "Perhatikan fungsi x kuadrat dan hitung integral dari nol sampai satu x kuadrat dx.",
                "Pada metode eiginvalue kita menjumpai akar dari x tambah satu sebelum Transformasi Fourier.",
                "Cek papan sebelah kiri [unclear] lalu evaluasi limit x menuju nol dari sin x per x.",
            ]
            if sess["language"].startswith("id")
            else [
                "Good morning everyone, today we study Riemann Integral and Convergence.",
                "Consider x squared and evaluate the integral from zero to one of x squared dx.",
                "In eiginvalue decomposition we encounter square root of x plus one before Fourier Transform.",
                "Check the board [unclear] then compute limit as x approaches zero of sin x over x.",
            ]
        )

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Status", sess["status"].upper())
        with sc2:
            st.metric("Mahasiswa Online" if lang == "id" else "Students", sess["student_count"])
        with sc3:
            if sess["status"] == "paused":
                if st.button("▶ Lanjutkan" if lang == "id" else "▶ Resume", type="primary", use_container_width=True):
                    api.patch_session(sess["id"], {"status": "live"})
                    st.rerun()
            else:
                if st.button("⏸ Jeda" if lang == "id" else "⏸ Pause", use_container_width=True):
                    api.patch_session(sess["id"], {"status": "paused"})
                    st.rerun()
        with sc4:
            if st.button("■ Akhiri Sesi" if lang == "id" else "■ End Session", use_container_width=True):
                api.patch_session(sess["id"], {"status": "ended"})
                navigate("transcript", sess["id"])

        # Native browser microphone recorder (transcribes with Gemini Flash when GEMINI_API_KEY is set)
        mic_audio = st.audio_input(
            "🎙️ Rekam suara dosen (klik mic → bicara → klik stop untuk transkripsi)"
            if lang == "id"
            else "🎙️ Record lecturer voice (tap mic → speak → stop to transcribe)"
        )
        if mic_audio is not None:
            audio_sig = f"{sess['id']}-{len(mic_audio.getvalue())}"
            if st.session_state.get("last_mic_sig") != audio_sig:
                st.session_state.last_mic_sig = audio_sig
                with st.spinner("Mentranskripsi suara..." if lang == "id" else "Transcribing audio..."):
                    try:
                        api.transcribe_audio_file(
                            session_id=sess["id"],
                            filename="mic.wav",
                            data=mic_audio.getvalue(),
                            content_type="audio/wav",
                            language=sess["language"],
                        )
                        st.toast("✅ Teks berhasil ditambahkan!" if lang == "id" else "✅ Caption added!")
                    except Exception as exc:
                        st.warning(str(exc))

        # Quick Manual Utterance & Demo Line Controls
        mc1, mc2 = st.columns([7, 3])
        with mc1:
            with st.form("embedded_manual_caption", clear_on_submit=True):
                u_in = st.text_input(
                    "Caption",
                    placeholder=(
                        'Ketik kalimat uji (mis: "integral dari nol sampai satu x kuadrat dx")...'
                        if lang == "id"
                        else 'Type a test sentence (e.g. "integral from zero to one of x squared dx")...'
                    ),
                    label_visibility="collapsed",
                )
                if st.form_submit_button("📤 Kirim Teks" if lang == "id" else "📤 Send Caption", type="primary", use_container_width=True):
                    if u_in.strip():
                        api.submit_caption(sess["id"], u_in.strip())
                        st.rerun()
        with mc2:
            if st.button("✨ Kirim 1 Baris Demo" if lang == "id" else "✨ Send 1 Demo Line", use_container_width=True):
                line = demo_lines[st.session_state.demo_cursor % len(demo_lines)]
                st.session_state.demo_cursor += 1
                api.submit_caption(sess["id"], line)
                st.rerun()

        host_caps = api.list_captions(sess["id"])
        if host_caps:
            render_katex_transcript_list(host_caps, set(), ui_lang=lang)
        else:
            st.info(
                "Belum ada teks. Tekan 'Kirim 1 Baris Demo', rekam mikrofon, atau ketik kalimat uji di atas."
                if lang == "id"
                else "No captions yet. Click 'Send 1 Demo Line', record audio, or type a sentence above."
            )

    # Upload Audio Recording -> FastAPI Faster-Whisper + Silero VAD
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
                with st.spinner("Running Faster-Whisper + Silero VAD + Gemini Flash..."):
                    try:
                        added = api.transcribe_audio_file(
                            session_id=sess["id"],
                            filename=audio_file.name,
                            data=audio_file.getvalue(),
                            content_type=audio_file.type or "audio/mpeg",
                            language=sess["language"],
                        )
                        st.success(f"Transcribed & refined {len(added)} segment(s)!")
                    except Exception as exc:
                        st.error(f"Transcription error: {exc}")


# ---------------------------------------------------------------------------
# PAGE 4: STUDENT CAPTION SCREEN
# ---------------------------------------------------------------------------

elif st.session_state.page == "join":
    sid = st.session_state.active_session_id
    if not sid:
        code_in = st.text_input(tr(lang, "join_placeholder"))
        if st.button(tr(lang, "btn_join"), type="primary"):
            c = extract_session_code(code_in)
            if c:
                navigate("join", c)
        st.stop()

    sess = api.get_session(sid)
    if not sess:
        st.error(f"Session `{sid}` not found.")
        if st.button(tr(lang, "nav_home")):
            navigate("home")
        st.stop()

    sl, sr = st.columns([7, 3])
    with sl:
        st.header(f"📱 {sess['course_title']}")
        st.caption(
            f"{sess['topic']} · Room `{sess['id']}` · Private ID `{st.session_state.student_id}`"
        )
    with sr:
        if st.button(f"📄 {tr(lang, 'nav_transcript')}", use_container_width=True):
            navigate("transcript", sess["id"])

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

        ctrl1, ctrl2 = st.columns([6, 4])
        with ctrl1:
            st.caption(
                "🔄 Teks diperbarui otomatis tiap 1,5 detik (Cloud Live Sync)"
                if lang == "id"
                else "🔄 Captions auto-refresh every 1.5s (Cloud Live Sync)"
            )
        with ctrl2:
            st.session_state.stu_pause_poll = st.toggle(
                "⏸ Jeda Gulir / Auto-Refresh" if lang == "id" else "⏸ Pause Auto-Refresh",
                value=st.session_state.stu_pause_poll,
            )

        @st.fragment(run_every=None if st.session_state.stu_pause_poll else "1.5s")
        def _live_student_feed():
            touch_student_presence(sess["id"], st.session_state.student_id)
            live_sess = api.get_session(sess["id"])
            if not live_sess:
                st.error("Session not found.")
                return
            if live_sess["status"] == "ended":
                st.success(
                    "✅ **Sesi Telah Berakhir** — Dosen telah mengakhiri sesi ini. Buka tab **Transkrip & Ringkasan** untuk melihat ringkasan & ekspor `.docx` / `.pdf`."
                    if lang == "id"
                    else "✅ **Session Ended** — Open the **Transcript & Summary** tab above to summarize and export `.docx` / `.pdf`."
                )
                return
            if live_sess["status"] == "paused":
                st.warning(
                    "⏸ Dosen sedang menjeda sesi."
                    if lang == "id"
                    else "⏸ The lecturer has temporarily paused the session."
                )
            live_caps = api.list_captions(sess["id"])
            bks = api.list_bookmarks(sess["id"], st.session_state.student_id)
            bk_seqs = {b["transcript_seq"] for b in bks}
            if not live_caps:
                st.info(
                    "Terhubung! Menunggu dosen mulai berbicara..."
                    if lang == "id"
                    else "Connected! Waiting for the lecturer to begin..."
                )
                return
            render_katex_transcript_list(live_caps, bk_seqs, ui_lang=lang)
            latest_seq = live_caps[-1]["seq"]
            bk_col1, bk_col2 = st.columns([6, 4])
            with bk_col2:
                saved = latest_seq in bk_seqs
                lbl = (
                    f"★ Hapus Bookmark #{latest_seq}"
                    if saved
                    else f"☆ Bookmark Segmen Terbaru (#{latest_seq})"
                )
                if st.button(lbl, key=f"quick_bk_{latest_seq}", use_container_width=True):
                    if saved:
                        api.delete_bookmark(sess["id"], latest_seq, st.session_state.student_id)
                    else:
                        api.upsert_bookmark(sess["id"], latest_seq, st.session_state.student_id)
                    st.rerun()

        _live_student_feed()


# ---------------------------------------------------------------------------
# PAGE 5: TRANSCRIPT, GEMINI SUMMARY & DOCX/PDF EXPORT
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

    st.header(f"📄 {sess['course_title']} — {sess['topic']}")
    st.caption(
        f"Room `{sess['id']}` · 📅 {sess['date']} · {len(captions)} segmen · "
        f"★ {len(bookmarked_seqs)} private bookmarks"
    )

    if sess["glossary"]:
        chips = "".join(
            f'<span class="ll-pill ll-pill-blue">{g}</span>' for g in sess["glossary"]
        )
        st.markdown(f"**Glossary:** {chips}", unsafe_allow_html=True)

    # Export & Gemini Flash Summary Action Bar
    ex1, ex2, ex3, ex4 = st.columns(4)
    with ex1:
        if st.button(
            f"✨ {tr(lang, 'btn_summary')}",
            type="primary",
            disabled=len(captions) == 0,
            use_container_width=True,
        ):
            with st.spinner("Generating transcript-grounded summary via Google Gemini Flash..."):
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

    # Post-Session Summary Panel
    if sess.get("summary_md"):
        with st.container(border=True):
            st.subheader(f"✨ {tr(lang, 'summary_heading')}")
            st.markdown(sess["summary_md"])

    # Search & Private Bookmarks Filter
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
