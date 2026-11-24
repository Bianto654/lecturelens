# LectureLens (Python Full-Stack Architecture)

Mobile-first live lecture captioning platform built with the exact planned stack:

| Layer | Technology | Implementation |
|---|---|---|
| **Frontend & UI** | **Streamlit** | `streamlit_app.py`, `frontend/` (mobile-first UI + live WebSocket KaTeX components) |
| **Backend & Real-Time Sync** | **FastAPI + WebSockets** | `backend/main.py`, `backend/ws_manager.py` (`/ws/host/{id}`, `/ws/student/{id}`) |
| **Database** | **Supabase PostgreSQL** | `backend/models.py`, `backend/db.py`, `supabase/schema.sql` (courses, sessions, glossaries, transcripts, private bookmarks) |
| **Speech-to-Text (STT)** | **Faster-Whisper (`large-v3-turbo`) + Silero VAD** | `backend/services/stt_service.py` (glossary `hotwords` + `initial_prompt`, built-in ONNX Silero VAD) |
| **Math Engine & Context Refinement** | **Google Gemini Flash API + KaTeX** | `backend/services/refinement_service.py` + KaTeX rendering in `frontend/components.py` |
| **Summarization & Export** | **Google Gemini Flash API, `python-docx`, `ReportLab`** | `backend/services/summary_service.py`, `backend/services/export_service.py` |
| **Hosting & Deployment** | **Streamlit Community Cloud + Render** | `render.yaml`, `.streamlit/config.toml`, `.streamlit/secrets.toml.example` |

---

## Project Structure

```text
lecturelens-py/
├── backend/
│   ├── config.py                     # Pydantic Settings (.env loader)
│   ├── db.py                         # SQLAlchemy engine (Supabase PostgreSQL / local SQLite fallback)
│   ├── main.py                       # FastAPI REST endpoints & WebSockets
│   ├── models.py                     # courses, sessions, glossaries, transcripts, bookmarks
│   ├── schemas.py                    # Pydantic request/response models
│   ├── ws_manager.py                 # Low-latency room WebSocket broadcast & presence manager
│   └── services/
│       ├── stt_service.py            # Faster-Whisper (large-v3-turbo) + Silero VAD + hotwords/initial_prompt
│       ├── refinement_service.py     # Google Gemini Flash API + rule-based ID/EN spoken math & fuzzy glossary
│       ├── summary_service.py        # Transcript-grounded post-session summary (Gemini Flash)
│       └── export_service.py         # .docx (python-docx), .pdf (ReportLab), .txt exporters
├── frontend/
│   ├── api_client.py                 # Typed httpx client for FastAPI backend
│   ├── components.py                 # Live WebSocket + KaTeX Host & Student HTML components
│   └── i18n.py                       # Indonesian (default) & English UI labels
├── supabase/
│   └── schema.sql                    # PostgreSQL DDL for Supabase SQL Editor
├── tests/
│   └── test_pipeline_and_api.py      # End-to-end pytest suite (math, glossary, WebSockets, bookmarks, docx/pdf)
├── .streamlit/
│   ├── config.toml                   # Streamlit theme & server config
│   └── secrets.toml.example          # Streamlit Community Cloud secrets template
├── streamlit_app.py                  # Streamlit Community Cloud entry point
├── render.yaml                       # Render backend deployment blueprint
├── requirements.txt                  # Full backend + frontend dependencies
├── requirements-frontend.txt         # Lightweight Streamlit Cloud requirements
└── .env.example                      # Environment variable template
```

---

## Local Development

### 1. Setup Virtual Environment & Install Packages
```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
- Add **`DATABASE_URL`** from Supabase PostgreSQL *(or leave blank to run immediately with local SQLite `./data/lecturelens.db`)*.
- Add **`GEMINI_API_KEY`** from Google AI Studio for Gemini Flash refinement & summaries.
- Adjust **`WHISPER_MODEL_SIZE`** (`large-v3-turbo` on GPU/server, or `base`/`small` for fast CPU laptops).

### 3. Run FastAPI Backend (Terminal 1)
```bash
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Streamlit Frontend (Terminal 2)
```bash
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501
```

Open **http://localhost:8501**!

### 5. Run Tests
```bash
.\.venv\Scripts\python.exe -m pytest -v
```

---

## Deployment Guide

### 1. Database — Supabase PostgreSQL
1. Create a project at https://supabase.com.
2. Open **SQL Editor** and run `supabase/schema.sql`.
3. Copy the **Connection String (URI)** from **Project Settings → Database** for `DATABASE_URL`.

### 2. Backend — Render
1. Push this folder to GitHub.
2. On https://dashboard.render.com, choose **New → Blueprint** and select `render.yaml`.
3. Set `DATABASE_URL` and `GEMINI_API_KEY` in Render Environment Variables.
4. Note your live backend URL (e.g. `https://lecturelens-api.onrender.com`).

### 3. Frontend — Streamlit Community Cloud
1. On https://share.streamlit.io, deploy `streamlit_app.py` from the same GitHub repo.
2. Under **App Settings → Secrets**, paste `.streamlit/secrets.toml.example` filled with your Render backend `https://` and `wss://` URLs.
