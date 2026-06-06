from celery import shared_task
from django.utils import timezone

from analysis.services.analysis_runner import run_gri_305_analysis
from analysis.services.pdf_report import generate_pdf_report
from rag.services import create_report_vector_records

from .models import AnalysisJob, Report
from .services.ocr import run_ocr_for_report
from .services.pdf_parser import parse_pdf


def _job(report_id, job_id=None):
    report = Report.objects.get(id=report_id)
    job = AnalysisJob.objects.select_related("report").get(id=job_id) if job_id else report.analysis_job
    if not job.started_at:
        job.started_at = timezone.now()
        job.save(update_fields=["started_at"])
    return report, job


@shared_task(bind=True)
def parse_pdf_task(self, report_id, job_id=None):
    report, job = _job(report_id, job_id)
    try:
        job.celery_task_id = self.request.id
        job.mark("parsing", 10)
        needs_ocr = parse_pdf(report)
        if needs_ocr:
            return ocr_pdf_task.delay(report_id, job.id).id
        return create_report_embeddings_task.delay(report_id, job.id).id
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise


@shared_task(bind=True)
def ocr_pdf_task(self, report_id, job_id=None):
    report, job = _job(report_id, job_id)
    try:
        job.celery_task_id = self.request.id
        job.mark("ocr_processing", 30)
        run_ocr_for_report(report)
        return create_report_embeddings_task.delay(report_id, job.id).id
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise


@shared_task(bind=True)
def create_report_embeddings_task(self, report_id, job_id=None):
    report, job = _job(report_id, job_id)
    try:
        job.celery_task_id = self.request.id
        job.mark("embedding", 50)
        create_report_vector_records(report)
        return run_gri_analysis_task.delay(report_id, job.id).id
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise


@shared_task(bind=True)
def run_gri_analysis_task(self, report_id, job_id=None):
    report, job = _job(report_id, job_id)
    try:
        job.celery_task_id = self.request.id
        job.mark("analyzing", 75)
        result = run_gri_305_analysis(report, analysis_job=job)
        return generate_pdf_report_task.delay(result.id, job.id).id
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise


@shared_task(bind=True)
def generate_pdf_report_task(self, analysis_result_id, job_id=None):
    from analysis.models import AnalysisResult

    result = AnalysisResult.objects.select_related("report").get(id=analysis_result_id)
    job = AnalysisJob.objects.get(id=job_id) if job_id else result.analysis_job or result.report.analysis_job
    try:
        job.celery_task_id = self.request.id
        job.mark("generating_pdf", 90)
        generate_pdf_report(result)
        job.completed_at = timezone.now()
        job.mark("completed", 100)
        job.save(update_fields=["completed_at"])
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise


@shared_task(bind=True)
def reanalyze_report_task(self, report_id, job_id):
    report, job = _job(report_id, job_id)
    try:
        job.celery_task_id = self.request.id
        if not report.pages.exists() or not report.chunks.exists():
            job.mark("parsing", 15)
            needs_ocr = parse_pdf(report)
            if needs_ocr:
                job.mark("ocr_processing", 35)
                run_ocr_for_report(report)
        elif report.pages.filter(needs_ocr=True, ocr_text="").exists():
            job.mark("ocr_processing", 35)
            run_ocr_for_report(report)

        if not report.chunks.filter(embedding_status="embedded").exists() or report.chunks.exclude(embedding_status="embedded").exists():
            job.mark("embedding", 55)
            create_report_vector_records(report)

        job.mark("analyzing", 75)
        result = run_gri_305_analysis(report, analysis_job=job)
        job.mark("generating_pdf", 90)
        generate_pdf_report(result)
        job.completed_at = timezone.now()
        job.mark("completed", 100)
        job.save(update_fields=["completed_at"])
    except Exception as exc:
        job.mark("failed", 0, str(exc))
        raise
