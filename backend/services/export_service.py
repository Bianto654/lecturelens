from __future__ import annotations

import datetime
import io
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_time(ts_ms: int) -> str:
    return datetime.datetime.fromtimestamp(ts_ms / 1000.0).strftime("%H:%M:%S")


def build_txt_bytes(session: dict, captions: list[dict]) -> bytes:
    lines = [
        "LECTURELENS TRANSCRIPT",
        "=" * 56,
        f"Course  : {session['course_title']}",
        f"Topic   : {session['topic']}",
        f"Date    : {session['date']}",
        f"Room ID : {session['id']}",
        f"Glossary: {', '.join(session.get('glossary') or []) or '-'}",
        "=" * 56,
        "",
    ]

    if session.get("summary_md"):
        lines.extend(["SUMMARY", "-" * 56, session["summary_md"], "", "TRANSCRIPT", "-" * 56, ""])

    for cap in captions:
        lines.append(f"[{_fmt_time(cap['timestamp_ms'])}] (#{cap['seq']}) {cap['processed_text']}")
        for f in cap.get("formulas") or []:
            tag = "automatic/ambiguous" if f.get("ambiguous") else "automatic"
            lines.append(f"    -> Formula ({tag}): \"{f['original_text']}\" => {f['latex']}")

    return "\n".join(lines).encode("utf-8")


def build_docx_bytes(session: dict, captions: list[dict]) -> bytes:
    """Exports session metadata, optional Gemini summary, and full transcript as .docx via python-docx."""
    doc = Document()
    doc.core_properties.author = "LectureLens"
    doc.core_properties.title = f"{session['course_title']} — {session['topic']}"

    doc.add_heading(session["course_title"], level=1)
    p_topic = doc.add_paragraph()
    run_topic = p_topic.add_run(session["topic"])
    run_topic.bold = True
    run_topic.font.size = Pt(13)

    p_meta = doc.add_paragraph()
    meta_run = p_meta.add_run(
        f"Date: {session['date']}   |   Room: {session['id']}   |   Language: {session['language']}"
    )
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    glossary = session.get("glossary") or []
    if glossary:
        p_gl = doc.add_paragraph()
        r1 = p_gl.add_run("Glossary: ")
        r1.bold = True
        r1.font.size = Pt(10)
        r2 = p_gl.add_run(", ".join(glossary))
        r2.italic = True
        r2.font.size = Pt(10)

    if session.get("summary_md"):
        doc.add_heading("Post-Session Summary", level=2)
        for line in session["summary_md"].splitlines():
            clean = line.strip().lstrip("#").strip()
            if clean:
                doc.add_paragraph(clean)

    doc.add_heading("Full Transcript", level=2)
    for cap in captions:
        p = doc.add_paragraph()
        t_run = p.add_run(f"[{_fmt_time(cap['timestamp_ms'])}] (#{cap['seq']}) ")
        t_run.font.size = Pt(9.5)
        t_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

        segments = cap.get("segments") or []
        if not segments:
            p.add_run(cap["processed_text"])
            continue

        for seg in segments:
            st = seg.get("type")
            if st == "text":
                p.add_run(seg.get("text", ""))
            elif st == "glossary":
                r = p.add_run(seg.get("matched_term", ""))
                r.bold = True
                r.font.color.rgb = RGBColor(0x15, 0x49, 0xC7)
            elif st == "formula":
                r = p.add_run(
                    f" \"{seg.get('original_text', '')}\" [LaTeX: {seg.get('latex', '')} · auto] "
                )
                r.italic = True
                r.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
            elif st == "unclear":
                r = p.add_run(" [unclear] ")
                r.italic = True
                r.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf_bytes(session: dict, captions: list[dict]) -> bytes:
    """Exports session metadata, optional Gemini summary, and full transcript as .pdf via ReportLab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=f"{session['course_title']} - {session['topic']}",
        author="LectureLens",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LLTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "LLSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1549C7"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "LLSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "LLBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )

    story = [
        Paragraph(escape(session["course_title"]), title_style),
        Paragraph(escape(session["topic"]), subtitle_style),
    ]

    meta_rows = [
        ["Date", session["date"], "Room ID", session["id"]],
        [
            "Language",
            session["language"],
            "Segments",
            str(len(captions)),
        ],
    ]
    meta_table = Table(meta_rows, colWidths=[2.6 * cm, 5.5 * cm, 2.6 * cm, 6.2 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#475569")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    glossary = session.get("glossary") or []
    if glossary:
        story.append(
            Paragraph(
                f"<b>Glossary:</b> {escape(', '.join(glossary))}",
                body_style,
            )
        )

    if session.get("summary_md"):
        story.append(Paragraph("Post-Session Summary", section_style))
        for raw_line in session["summary_md"].splitlines():
            clean = raw_line.strip().lstrip("#").strip()
            if clean:
                story.append(Paragraph(escape(clean), body_style))

    story.append(Paragraph("Full Transcript", section_style))
    for cap in captions:
        ts = _fmt_time(cap["timestamp_ms"])
        parts = [f"<font color='#64748B'>[{ts}] (#{cap['seq']})</font> "]
        segments = cap.get("segments") or []
        if not segments:
            parts.append(escape(cap["processed_text"]))
        else:
            for seg in segments:
                st = seg.get("type")
                if st == "text":
                    parts.append(escape(seg.get("text", "")))
                elif st == "glossary":
                    parts.append(
                        f"<b><font color='#1549C7'>{escape(seg.get('matched_term', ''))}</font></b>"
                    )
                elif st == "formula":
                    parts.append(
                        f" <i><font color='#0F766E'>\"{escape(seg.get('original_text', ''))}\" "
                        f"[LaTeX: {escape(seg.get('latex', ''))} · auto]</font></i> "
                    )
                elif st == "unclear":
                    parts.append(" <b><font color='#B45309'>[unclear]</font></b> ")
        story.append(Paragraph("".join(parts), body_style))

    doc.build(story)
    return buf.getvalue()
