import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

import fitz
from django.core.files import File

from analysis.services.analysis_runner import run_gri_305_analysis
from analysis.services.pdf_report import generate_pdf_report
from organizations.models import Organization
from rag.services import create_report_vector_records
from reports.models import AnalysisJob, Report, ReportFile
from reports.services.ocr import run_ocr_for_report
from reports.services.pdf_parser import parse_pdf


def build_sample_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "GRI 305 Emissions\n"
        "本公司 Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e，年度為 2025。\n"
        "本公司 Scope 2 範疇二能源間接溫室氣體排放量為 2,345 tCO2e。\n"
        "本公司 Scope 3 範疇三其他間接排放量為 3,456 tCO2e。\n"
        "溫室氣體排放密集度為每百萬元營收 0.88 tCO2e。\n"
        "相較基準年，溫室氣體排放減量 12%，主要措施包含能源效率提升。"
    )
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


def main():
    sample_path = BASE_DIR / "media" / "uploaded_reports" / "smoke_gri_305.pdf"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    build_sample_pdf(sample_path)

    organization, _ = Organization.objects.get_or_create(name="Smoke Test Organization")
    report = Report.objects.create(
        organization=organization,
        company_name="Smoke Test Organization",
        report_year=2025,
        title="Smoke Test GRI 305 Report",
        industry_category="Electronics",
        status="uploaded",
    )
    with sample_path.open("rb") as handle:
        ReportFile.objects.create(
            report=report,
            pdf_file=File(handle, name="smoke_gri_305.pdf"),
            original_filename="smoke_gri_305.pdf",
            file_size=sample_path.stat().st_size,
        )
    AnalysisJob.objects.create(report=report, status="uploaded")

    needs_ocr = parse_pdf(report)
    if needs_ocr:
        run_ocr_for_report(report)
    create_report_vector_records(report)
    result = run_gri_305_analysis(report)
    generated = generate_pdf_report(result)
    report.status = "completed"
    report.save(update_fields=["status", "updated_at"])
    report.analysis_job.mark("completed", 100)

    print(f"report_id={report.id}")
    print(f"pages={report.pages.count()}")
    print(f"chunks={report.chunks.count()}")
    print(f"scores={result.disclosure_scores.count()}")
    print(f"citations={result.evidence_citations.count()}")
    print(f"generated_report={generated.file}")


if __name__ == "__main__":
    main()
