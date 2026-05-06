"""Generate a polished cover letter PDF using ReportLab."""

from __future__ import annotations

from datetime import date

from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def generate_cover_letter_pdf(
    letter_body: str,
    candidate_name: str,
    company: str,
    role: str,
    output_path: str,
    candidate_email: str | None = None,
) -> str:
    """Render the cover letter to a clean, single-page-friendly PDF.

    Returns the output path on success.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        title=f"Cover Letter - {candidate_name}",
        author=candidate_name,
    )

    base = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "Header",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    name_style = ParagraphStyle(
        "Name",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )
    subject_style = ParagraphStyle(
        "Subject",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=12,
    )

    elements: list = []
    elements.append(Paragraph(_escape(candidate_name), name_style))
    if candidate_email:
        elements.append(Paragraph(_escape(candidate_email), header_style))
    elements.append(Paragraph(date.today().strftime("%B %d, %Y"), header_style))
    elements.append(Spacer(1, 0.25 * inch))

    elements.append(
        Paragraph(_escape(f"Re: Application for {role} at {company}"), subject_style)
    )

    elements.append(Paragraph("Dear Hiring Manager,", body_style))

    for para in _split_paragraphs(letter_body):
        elements.append(Paragraph(_escape(para), body_style))

    elements.append(Spacer(1, 0.05 * inch))
    elements.append(Paragraph("Sincerely,", body_style))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(_escape(candidate_name), name_style))

    doc.build(elements)
    return output_path


def _split_paragraphs(text: str) -> list[str]:
    """Split letter body into paragraphs, collapsing single newlines into spaces."""
    paragraphs: list[str] = []
    for chunk in text.strip().split("\n\n"):
        cleaned = " ".join(line.strip() for line in chunk.splitlines() if line.strip())
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def _escape(text: str) -> str:
    """Escape XML-ish chars that ReportLab's Paragraph parser cares about."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
