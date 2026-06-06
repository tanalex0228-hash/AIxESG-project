from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from analysis.models import GeneratedReport


def generate_pdf_report(analysis_result):
    html = render_to_string("pdf/gri_305_report.html", {"analysis": analysis_result, "report": analysis_result.report})
    filename = f"gri_305_analysis_{analysis_result.report_id}_v{analysis_result.version_number}.pdf"
    generated = GeneratedReport.objects.create(analysis_result=analysis_result, html_snapshot=html)

    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
        generated.file.save(filename, ContentFile(pdf_bytes), save=True)
    except Exception:
        fallback_path = Path(settings.MEDIA_ROOT) / "generated_reports" / filename.replace(".pdf", ".html")
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text(html, encoding="utf-8")
        generated.file = f"generated_reports/{fallback_path.name}"
        generated.save(update_fields=["file"])
    return generated
