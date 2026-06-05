from pathlib import Path

import pytesseract
from django.conf import settings
from django.utils import timezone
from PIL import Image

from reports.models import OCRJob, ReportChunk
from reports.services.pdf_parser import estimate_tokens


def run_ocr_for_report(report):
    for page in report.pages.filter(needs_ocr=True):
        job = OCRJob.objects.create(report=report, page=page, status="processing", started_at=timezone.now())
        try:
            if not page.image_path:
                raise ValueError(f"Page {page.page_number} has no extracted image for OCR.")
            image_file = Path(settings.MEDIA_ROOT) / page.image_path
            if not image_file.exists():
                raise FileNotFoundError(f"OCR image not found: {image_file}")
            ocr_text = pytesseract.image_to_string(Image.open(image_file), lang="chi_tra+eng").strip()
            page.ocr_text = ocr_text
            page.final_text = ocr_text or page.raw_text
            page.extraction_method = "pytesseract" if ocr_text else "pymupdf_low_text"
            page.confidence_score = 0.85 if ocr_text else 0.35
            page.save(update_fields=["ocr_text", "final_text", "extraction_method", "confidence_score"])
            report.chunks.filter(page_start=page.page_number, page_end=page.page_number, chunk_type="ocr").delete()
            if page.final_text:
                ReportChunk.objects.create(
                    report=report,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    chunk_text=page.final_text,
                    token_count=estimate_tokens(page.final_text),
                    chunk_type="ocr",
                )
            job.status = "completed"
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
