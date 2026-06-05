import re
from pathlib import Path

import fitz
from django.conf import settings
from django.db import transaction

from reports.models import ReportChunk, ReportPage

MIN_TEXT_CHARS_FOR_OCR = 80


def estimate_tokens(text):
    return max(1, len(text) // 4)


def chunk_text(text, min_tokens=500, max_tokens=1000):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = []
    current_tokens = 0
    for paragraph in paragraphs:
        tokens = estimate_tokens(paragraph)
        if current and current_tokens + tokens > max_tokens:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0
        current.append(paragraph)
        current_tokens += tokens
        if current_tokens >= min_tokens:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0
    if current:
        chunks.append("\n\n".join(current))
    return chunks or ([text.strip()] if text.strip() else [])


@transaction.atomic
def parse_pdf(report):
    report.status = "parsing"
    report.save(update_fields=["status", "updated_at"])
    ReportPage.objects.filter(report=report).delete()
    ReportChunk.objects.filter(report=report).delete()

    pdf_path = report.file_record.pdf_file.path
    doc = fitz.open(pdf_path)
    report.total_pages = doc.page_count
    report.save(update_fields=["total_pages", "updated_at"])

    for index, page in enumerate(doc, start=1):
        raw_text = page.get_text("text").strip()
        needs_ocr = len(raw_text) < MIN_TEXT_CHARS_FOR_OCR
        final_text = raw_text
        image_path = ""
        if needs_ocr:
            image_dir = Path(settings.MEDIA_ROOT) / "extracted_pages" / str(report.id)
            image_dir.mkdir(parents=True, exist_ok=True)
            image_file = image_dir / f"page_{index}.png"
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pixmap.save(image_file)
            image_path = str(image_file.relative_to(settings.MEDIA_ROOT))
        page_obj = ReportPage.objects.create(
            report=report,
            page_number=index,
            raw_text=raw_text,
            final_text=final_text,
            extraction_method="pymupdf",
            confidence_score=0.95 if raw_text else 0,
            needs_ocr=needs_ocr,
            image_path=image_path,
        )
        for chunk in chunk_text(final_text):
            ReportChunk.objects.create(
                report=report,
                page_start=page_obj.page_number,
                page_end=page_obj.page_number,
                chunk_text=chunk,
                token_count=estimate_tokens(chunk),
                chunk_type="paragraph" if not needs_ocr else "ocr",
            )
    return report.pages.filter(needs_ocr=True).exists()
