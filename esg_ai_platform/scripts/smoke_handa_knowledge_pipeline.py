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
from analysis.services.knowledge_base_importer import import_knowledge_base
from analysis.services.pdf_report import generate_pdf_report
from organizations.models import Organization
from rag.services import create_report_vector_records
from reports.models import AnalysisJob, Report, ReportFile
from reports.services.ocr import run_ocr_for_report
from reports.services.pdf_parser import parse_pdf


def build_handa_sample_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "桓達企業永續報告書 2025\n"
        "GRI 305 Emissions\n\n"
        "305-1 Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e。"
        "涵蓋氣體包含 CO2、CH4、N2O。基準年為 2022，基準年排放量為 1,380 tCO2e。"
        "排放係數採環境部公告係數，盤查邊界採營運控制法，方法學依 ISO 14064-1:2018。\n\n"
        "305-2 Scope 2 範疇二能源間接排放採地點基礎 Location-based 為 2,345 tCO2e，"
        "市場基礎 Market-based 為 2,120 tCO2e。排放係數採台電公告係數，基準年為 2022。\n\n"
        "305-3 Scope 3 範疇三其他間接排放總量為 9,876 tCO2e，"
        "揭露類別包含 Purchased Goods and Services、Capital Goods、Waste Generated in Operations、Use of Sold Products。"
        "計算方法依 GHG Protocol Scope 3，排放係數參考 DEFRA。\n\n"
        "305-4 排放密集度 intensity ratio 為每百萬元營收 0.77 tCO2e，分母為年度營收，"
        "納入範疇一與範疇二。\n\n"
        "305-5 溫室氣體排放減量 Reduction Amount 為 520 tCO2e，減量基準 baseline 為 2022，"
        "減量方法包含節能空壓機汰換與再生能源採購，減量範疇包含 Scope 1 與 Scope 2。"
    )
    page.insert_textbox((48, 48, 540, 780), text, fontsize=10)
    doc.save(path)
    doc.close()


def main():
    import_summary = import_knowledge_base()
    sample_path = BASE_DIR / "media" / "uploaded_reports" / "handa_gri_305_smoke.pdf"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    build_handa_sample_pdf(sample_path)

    organization, _ = Organization.objects.get_or_create(name="桓達企業")
    report = Report.objects.create(
        organization=organization,
        company_name="桓達企業",
        report_year=2025,
        title="桓達企業永續報告書 測試樣本",
        industry_category="工業感測與製造",
        status="uploaded",
    )
    with sample_path.open("rb") as handle:
        ReportFile.objects.create(
            report=report,
            pdf_file=File(handle, name="handa_gri_305_smoke.pdf"),
            original_filename="handa_gri_305_smoke.pdf",
            file_size=sample_path.stat().st_size,
        )
    AnalysisJob.objects.create(report=report, status="uploaded")

    needs_ocr = parse_pdf(report)
    if needs_ocr:
        run_ocr_for_report(report)
    vector_count = create_report_vector_records(report)
    result = run_gri_305_analysis(report)
    generated = generate_pdf_report(result)
    report.analysis_job.mark("completed", 100)

    print(f"import_summary={import_summary}")
    print(f"report_id={report.id}")
    print(f"pages={report.pages.count()}")
    print(f"chunks={report.chunks.count()}")
    print(f"report_vectors_created={vector_count}")
    print(f"total_score={result.total_score}")
    print(f"disclosure_scores={result.disclosure_scores.count()}")
    print(f"missing_items={result.missing_items.count()}")
    print(f"recommendations={result.recommendations.count()}")
    print(f"citations={result.evidence_citations.count()}")
    print(f"generated_report={generated.file}")
    print(f"benchmark_summary={result.raw_output['benchmark_comparison']['summary']}")


if __name__ == "__main__":
    main()
