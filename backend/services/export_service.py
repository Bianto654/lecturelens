from __future__ import annotations

import datetime
import io
import re
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


def _latex_to_readable(latex: str, latin1_safe: bool = False) -> str:
    """
    Converts common LaTeX math commands into clean, human-readable mathematical notation
    for .docx (full Unicode) and ReportLab .pdf (WinAnsi / Latin-1 safe to avoid glyph boxes).
    """
    s = latex.strip()
    # Replace \frac{a}{b} -> (a)/(b)
    s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", s)
    # Replace \sqrt{x}
    sqrt_sym = "sqrt" if latin1_safe else "√"
    s = re.sub(r"\\sqrt\{([^{}]+)\}", rf"{sqrt_sym}(\1)", s)
    # Replace \int_a^b and \int
    if latin1_safe:
        s = re.sub(r"\\int_\{?([^\s^]+)\}?\^\{?([^\s]+)\}?", r"integral[\1..\2] ", s)
        s = s.replace(r"\int", "integral ")
        s = s.replace(r"\sum", "sum ")
        s = s.replace(r"\lim_", "lim_")
        s = s.replace(r"\lim", "lim")
        s = s.replace(r"\to", " -> ")
        s = s.replace(r"\infty", "infinity")
        s = s.replace(r"\le", " <= ").replace(r"\ge", " >= ").replace(r"\neq", " != ")
    else:
        s = re.sub(r"\\int_\{?([^\s^]+)\}?\^\{?([^\s]+)\}?", r"∫[\1→\2] ", s)
        s = s.replace(r"\int", "∫ ")
        s = s.replace(r"\sum", "∑ ")
        s = s.replace(r"\lim", "lim")
        s = s.replace(r"\to", " → ")
        s = s.replace(r"\infty", "∞")
        s = s.replace(r"\le", " ≤ ").replace(r"\ge", " ≥ ").replace(r"\neq", " ≠ ")

    # Latin-1 safe symbols (supported in both Word and ReportLab Helvetica)
    s = s.replace(r"\pm", " ± ").replace(r"\times", " × ").replace(r"\cdot", " · ")
    s = s.replace(r"\left(", "(").replace(r"\right)", ")")
    s = s.replace(r"\,", " ").replace(r"\;", " ").replace(r"\sin", "sin").replace(r"\cos", "cos").replace(r"\tan", "tan")
    s = re.sub(r"\^\{?2\}?", "²", s)
    s = re.sub(r"\^\{?3\}?", "³", s)
    s = re.sub(r"\^\{([^{}]+)\}", r"^\1", s)
    s = re.sub(r"_\{([^{}]+)\}", r"_\1", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


# Inline Markdown token splitter: **bold**, *italic*, $$math$$, $math$
_INLINE_MD_RE = re.compile(
    r"(\*\*[^*]+\*\*|\$\$[^$]+\$\$|\$[^$\n]+\$|\*[^*\n]+\*)"
)


def _add_markdown_runs_docx(paragraph, text: str) -> None:
    """Adds styled runs (**bold**, *italic*, $LaTeX$) into a python-docx paragraph."""
    pos = 0
    for m in _INLINE_MD_RE.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos : m.start()])
        tok = m.group(0)
        if tok.startswith("**") and tok.endswith("**"):
            r = paragraph.add_run(tok[2:-2])
            r.bold = True
            r.font.color.rgb = RGBColor(0x00, 0x4D, 0x8F)
        elif tok.startswith("$$") and tok.endswith("$$"):
            r = paragraph.add_run(f" {_latex_to_readable(tok[2:-2], latin1_safe=False)} ")
            r.bold = True
            r.font.color.rgb = RGBColor(0xC2, 0x41, 0x0C)
        elif tok.startswith("$") and tok.endswith("$"):
            r = paragraph.add_run(_latex_to_readable(tok[1:-1], latin1_safe=False))
            r.bold = True
            r.font.color.rgb = RGBColor(0xC2, 0x41, 0x0C)
        elif tok.startswith("*") and tok.endswith("*"):
            r = paragraph.add_run(tok[1:-1])
            r.italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _markdown_inline_to_reportlab_html(text: str) -> str:
    """Converts inline Markdown (**bold**, *italic*, $LaTeX$) into safe ReportLab XML."""
    parts: list[str] = []
    pos = 0
    for m in _INLINE_MD_RE.finditer(text):
        if m.start() > pos:
            parts.append(escape(text[pos : m.start()]))
        tok = m.group(0)
        if tok.startswith("**") and tok.endswith("**"):
            parts.append(f"<b><font color='#004D8F'>{escape(tok[2:-2])}</font></b>")
        elif tok.startswith("$$") and tok.endswith("$$"):
            readable = _latex_to_readable(tok[2:-2], latin1_safe=True)
            parts.append(f" <b><font color='#C2410C'>{escape(readable)}</font></b> ")
        elif tok.startswith("$") and tok.endswith("$"):
            readable = _latex_to_readable(tok[1:-1], latin1_safe=True)
            parts.append(f"<b><font color='#C2410C'>{escape(readable)}</font></b>")
        elif tok.startswith("*") and tok.endswith("*"):
            parts.append(f"<i>{escape(tok[1:-1])}</i>")
        pos = m.end()
    if pos < len(text):
        parts.append(escape(text[pos:]))
    return "".join(parts)


def build_txt_bytes(session: dict, captions: list[dict]) -> bytes:
    lines = [
        "LECTURELENS ACADEMIC STUDY GUIDE & TRANSCRIPT",
        "=" * 60,
        f"Course  : {session['course_title']}",
        f"Topic   : {session['topic']}",
        f"Date    : {session['date']}",
        f"Room ID : {session['id']}",
        f"Glossary: {', '.join(session.get('glossary') or []) or '-'}",
        "=" * 60,
        "",
    ]

    if session.get("summary_md"):
        lines.extend(["POST-SESSION SUMMARY", "-" * 60, session["summary_md"], ""])

    if session.get("polished_transcript_md"):
        provider = session.get("polish_provider") or "academic-editor"
        lines.extend(
            [
                f"STRUCTURED STUDY GUIDE ({provider})",
                "-" * 60,
                session["polished_transcript_md"],
                "",
            ]
        )

    lines.extend(["APPENDIX: TIMESTAMPED SEGMENT LOG", "-" * 60, ""])
    for cap in captions:
        lines.append(f"[{_fmt_time(cap['timestamp_ms'])}] (#{cap['seq']}) {cap['processed_text']}")
        for f in cap.get("formulas") or []:
            tag = "automatic/ambiguous" if f.get("ambiguous") else "automatic"
            lines.append(f"    -> Formula ({tag}): \"{f['original_text']}\" => {f['latex']}")

    return "\n".join(lines).encode("utf-8")


def build_docx_bytes(session: dict, captions: list[dict]) -> bytes:
    """
    Exports session metadata, optional Gemini summary, polished academic study-guide
    paragraphs, and timestamped segment log appendix as .docx via python-docx.
    """
    doc = Document()
    doc.core_properties.author = "LectureLens"
    doc.core_properties.title = f"{session['course_title']} — {session['topic']}"

    doc.add_heading(session["course_title"], level=1)
    p_topic = doc.add_paragraph()
    run_topic = p_topic.add_run(session["topic"])
    run_topic.bold = True
    run_topic.font.size = Pt(13)
    run_topic.font.color.rgb = RGBColor(0x00, 0x4D, 0x8F)

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
        for raw_line in session["summary_md"].splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("### "):
                doc.add_heading(line[4:].strip(), level=3)
            elif line.startswith("## "):
                doc.add_heading(line[3:].strip(), level=3)
            elif line.startswith("- "):
                p = doc.add_paragraph(style="List Bullet")
                _add_markdown_runs_docx(p, line[2:].strip())
            else:
                p = doc.add_paragraph()
                _add_markdown_runs_docx(p, line.lstrip("> ").strip())

    if session.get("polished_transcript_md"):
        provider = session.get("polish_provider") or "Academic Editor"
        doc.add_heading("Structured Academic Study Guide", level=2)
        p_note = doc.add_paragraph()
        nr = p_note.add_run(f"Post-session refined transcript ({provider})")
        nr.italic = True
        nr.font.size = Pt(9.5)
        nr.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

        for raw_line in session["polished_transcript_md"].splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("### "):
                doc.add_heading(line[4:].strip(), level=3)
            elif line.startswith("## "):
                doc.add_heading(line[3:].strip(), level=3)
            elif line.startswith("> "):
                p = doc.add_paragraph()
                r = p.add_run(line[2:].strip().strip("*"))
                r.italic = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
            elif line.startswith("- "):
                p = doc.add_paragraph(style="List Bullet")
                _add_markdown_runs_docx(p, line[2:].strip())
            else:
                p = doc.add_paragraph()
                _add_markdown_runs_docx(p, line)

    appendix_title = (
        "Appendix: Timestamped Segment Log"
        if session.get("polished_transcript_md")
        else "Full Transcript"
    )
    doc.add_heading(appendix_title, level=2)
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
                r.font.color.rgb = RGBColor(0x00, 0x4D, 0x8F)
            elif st == "formula":
                readable = _latex_to_readable(seg.get("latex", ""), latin1_safe=False)
                r = p.add_run(
                    f" \"{seg.get('original_text', '')}\" [{readable} · auto] "
                )
                r.italic = True
                r.font.color.rgb = RGBColor(0xC2, 0x41, 0x0C)
            elif st == "unclear":
                r = p.add_run(" [unclear] ")
                r.italic = True
                r.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf_bytes(session: dict, captions: list[dict]) -> bytes:
    """
    Exports session metadata, optional Gemini summary, polished academic study-guide
    paragraphs, and timestamped segment log appendix as .pdf via ReportLab.
    """
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
        textColor=colors.HexColor("#0C2337"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "LLSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#004D8F"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "LLSection",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0C2337"),
        spaceBefore=12,
        spaceAfter=6,
    )
    subhead_style = ParagraphStyle(
        "LLSubhead",
        parent=styles["Heading3"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#004D8F"),
        spaceBefore=8,
        spaceAfter=4,
    )
    note_style = ParagraphStyle(
        "LLNote",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "LLBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15.5,
        textColor=colors.HexColor("#0C2337"),
        spaceAfter=7,
    )
    bullet_style = ParagraphStyle(
        "LLBullet",
        parent=body_style,
        leftIndent=14,
        spaceAfter=4,
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
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#004D8F")),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#004D8F")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
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
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("### ") or line.startswith("## "):
                story.append(Paragraph(escape(line.lstrip("#").strip()), subhead_style))
            elif line.startswith("- "):
                story.append(
                    Paragraph(
                        f"&bull; {_markdown_inline_to_reportlab_html(line[2:].strip())}",
                        bullet_style,
                    )
                )
            else:
                story.append(
                    Paragraph(
                        _markdown_inline_to_reportlab_html(line.lstrip("> ").strip()),
                        body_style,
                    )
                )

    if session.get("polished_transcript_md"):
        provider = session.get("polish_provider") or "Academic Editor"
        story.append(Paragraph("Structured Academic Study Guide", section_style))
        story.append(
            Paragraph(
                f"<i>Post-session refined transcript ({escape(provider)})</i>",
                note_style,
            )
        )
        for raw_line in session["polished_transcript_md"].splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("### ") or line.startswith("## "):
                story.append(Paragraph(escape(line.lstrip("#").strip()), subhead_style))
            elif line.startswith("> "):
                story.append(
                    Paragraph(
                        f"<i>{escape(line[2:].strip().strip('*'))}</i>",
                        note_style,
                    )
                )
            elif line.startswith("- "):
                story.append(
                    Paragraph(
                        f"&bull; {_markdown_inline_to_reportlab_html(line[2:].strip())}",
                        bullet_style,
                    )
                )
            else:
                story.append(
                    Paragraph(_markdown_inline_to_reportlab_html(line), body_style)
                )

    appendix_title = (
        "Appendix: Timestamped Segment Log"
        if session.get("polished_transcript_md")
        else "Full Transcript"
    )
    story.append(Paragraph(appendix_title, section_style))
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
                        f"<b><font color='#004D8F'>{escape(seg.get('matched_term', ''))}</font></b>"
                    )
                elif st == "formula":
                    readable = _latex_to_readable(seg.get("latex", ""), latin1_safe=True)
                    parts.append(
                        f" <i><font color='#C2410C'>\"{escape(seg.get('original_text', ''))}\" "
                        f"[{escape(readable)} - auto]</font></i> "
                    )
                elif st == "unclear":
                    parts.append(" <b><font color='#B45309'>[unclear]</font></b> ")
        story.append(Paragraph("".join(parts), body_style))

    doc.build(story)
    return buf.getvalue()
