from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.refinement_service import (
    find_formula_spans,
    find_glossary_spans,
    refine_caption,
)
from backend.services.stt_service import build_hotwords, build_initial_prompt


def test_spoken_math_indonesian_and_english():
    f1 = find_formula_spans("Hitung x kuadrat di titik ini")
    assert len(f1) == 1 and f1[0].latex == "x^2"

    f2 = find_formula_spans("Fungsinya akar dari x tambah satu")
    assert len(f2) == 1 and f2[0].latex == r"\sqrt{x+1}" and f2[0].ambiguous is True

    f3 = find_formula_spans("Mari hitung integral dari nol sampai satu x kuadrat dx")
    assert len(f3) == 1 and f3[0].latex == r"\int_0^1 x^2\,dx"

    f4 = find_formula_spans("Evaluate integral from zero to one of x squared dx")
    assert len(f4) == 1 and f4[0].latex == r"\int_0^1 x^2\,dx"


def test_glossary_fuzzy_and_whisper_prompt_builders():
    glossary = ["Eigenvalue", "Transformasi Fourier", "Konvergensi"]
    spans = find_glossary_spans("Kita pakai eiginvalue dan konvergensy", glossary)
    assert [s.matched_term for s in spans] == ["Eigenvalue", "Konvergensi"]
    assert all(s.was_corrected for s in spans)

    prompt = build_initial_prompt("Kalkulus II", "Integral", glossary, "id-ID")
    assert "Eigenvalue" in prompt
    assert build_hotwords(glossary) == "Eigenvalue, Transformasi Fourier, Konvergensi"


def test_refinement_preserves_original_text_and_handles_unclear():
    res = refine_caption(
        raw_text="Dalam eiginvalue kita pakai akar dari x tambah satu",
        course_title="Kalkulus II",
        topic="Integral",
        glossary=["Eigenvalue"],
        language="id-ID",
        confidence=0.92,
        use_gemini=False,
    )
    assert "akar dari x tambah satu" in res.processed_text
    assert res.formulas[0]["latex"] == r"\sqrt{x+1}"
    assert res.glossary_matches[0]["matched_term"] == "Eigenvalue"

    unclear = refine_caption(
        raw_text="hmm jauh",
        course_title="Kalkulus II",
        topic="Integral",
        glossary=[],
        confidence=0.2,
        use_gemini=False,
    )
    assert unclear.is_unclear is True
    assert unclear.processed_text == "[unclear]"


def test_fastapi_end_to_end_session_ws_bookmarks_summary_and_exports():
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200 and h.json()["ok"] is True

        # Create session + glossary
        created = client.post(
            "/api/sessions",
            json={
                "course_title": "Kalkulus II",
                "course_code": "KALK201",
                "topic": "Bab 4 Integral Tentu",
                "date": "2026-11-24",
                "language": "id-ID",
                "glossary": ["Eigenvalue", "Integral Riemann"],
            },
        )
        assert created.status_code == 201
        sid = created.json()["id"]

        # Submit caption via WebSocket host and verify student WebSocket receives it
        with client.websocket_connect(f"/ws/student/{sid}?client_id=stu-1") as stu_ws:
            snap = stu_ws.receive_json()
            assert snap["type"] == "snapshot"
            assert snap["student_count"] == 1
            # Consume own student_count broadcast
            cnt_msg = stu_ws.receive_json()
            assert cnt_msg["type"] == "student_count"

            with client.websocket_connect(f"/ws/host/{sid}") as host_ws:
                host_snap = host_ws.receive_json()
                assert host_snap["type"] == "snapshot"
                host_ws.send_json(
                    {
                        "type": "final",
                        "text": "Hitung eiginvalue dan integral dari nol sampai satu x kuadrat dx",
                        "use_gemini": False,
                    }
                )
                # Student receives interim clear + finalized refined caption
                got_caption = None
                for _ in range(3):
                    msg = stu_ws.receive_json()
                    if msg["type"] == "caption":
                        got_caption = msg["caption"]
                        break
                assert got_caption is not None
                assert got_caption["formulas"][0]["latex"] == r"\int_0^1 x^2\,dx"
                assert got_caption["glossary_matches"][0]["matched_term"] == "Eigenvalue"

        # Private bookmark CRUD
        bk = client.post(
            f"/api/sessions/{sid}/bookmarks",
            json={"transcript_seq": 1, "student_id": "stu-1", "note": "Penting untuk UTS"},
        )
        assert bk.status_code == 201
        bks = client.get(f"/api/sessions/{sid}/bookmarks", params={"student_id": "stu-1"})
        assert len(bks.json()) == 1

        # Post-session grounded summary
        summ = client.post(f"/api/sessions/{sid}/summary")
        assert summ.status_code == 200
        assert "[#1]" in summ.json()["summary_md"]

        # Exports: .docx (python-docx), .pdf (ReportLab), .txt
        docx_r = client.get(f"/api/sessions/{sid}/export/docx")
        assert docx_r.status_code == 200
        assert docx_r.content[:2] == b"PK"  # valid zip/.docx header

        pdf_r = client.get(f"/api/sessions/{sid}/export/pdf")
        assert pdf_r.status_code == 200
        assert pdf_r.content[:4] == b"%PDF"

        txt_r = client.get(f"/api/sessions/{sid}/export/txt")
        assert txt_r.status_code == 200
        assert b"\\int_0^1 x^2\\,dx" in txt_r.content
