from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_user_organization
from analysis.models import GeneratedReport

from .forms import ReportUploadForm
from .models import AnalysisJob, Report
from .tasks import parse_pdf_task


@login_required
def report_list(request):
    organization = get_user_organization(request.user)
    reports = Report.objects.filter(organization=organization).select_related("analysis_job") if organization else []
    return render(request, "reports/list.html", {"reports": reports})


@login_required
def upload_report(request):
    organization = get_user_organization(request.user)
    if not organization:
        messages.error(request, "尚未設定企業組織，請聯絡管理者。")
        return redirect("dashboard:index")

    if request.method == "POST":
        form = ReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save_with_file(organization=organization, user=request.user)
            job = AnalysisJob.objects.create(report=report, status="uploaded")
            async_result = parse_pdf_task.delay(report.id)
            job.celery_task_id = async_result.id
            job.save(update_fields=["celery_task_id"])
            messages.success(request, "報告書已上傳，系統已開始背景分析。")
            return redirect("reports:detail", pk=report.pk)
    else:
        form = ReportUploadForm()
    return render(request, "reports/upload.html", {"form": form})


@login_required
def report_detail(request, pk):
    organization = get_user_organization(request.user)
    report = get_object_or_404(
        Report.objects.select_related("analysis_result", "analysis_job"),
        pk=pk,
        organization=organization,
    )
    analysis_result = getattr(report, "analysis_result", None)
    generated_report = GeneratedReport.objects.filter(analysis_result=analysis_result).last() if analysis_result else None
    return render(request, "reports/detail.html", {"report": report, "generated_report": generated_report})
