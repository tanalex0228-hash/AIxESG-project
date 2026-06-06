from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from analysis.models import GeneratedReport
from organizations.models import Organization

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
    is_system_admin = is_system_admin_user(request.user)
    is_individual = is_individual_user(request.user)
    organizations = Organization.objects.filter(is_active=True).order_by("name") if is_system_admin else Organization.objects.none()

    if request.method == "POST" and is_system_admin:
        selected_organization = request.POST.get("organization_id", "")
        new_organization_name = request.POST.get("new_organization_name", "").strip()
        if selected_organization:
            organization = get_object_or_404(Organization, pk=selected_organization, is_active=True)
        elif new_organization_name:
            organization, _ = Organization.objects.get_or_create(name=new_organization_name)
        else:
            messages.error(request, "系統管理者測試上傳時，請選擇企業或建立測試企業。")

    if not organization:
        form = ReportUploadForm(request.POST or None, request.FILES or None)
        return render(
            request,
            "reports/upload.html",
            {
                "form": form,
                "upload_blocked": True,
                "is_system_admin": is_system_admin,
                "is_individual": is_individual,
                "organizations": organizations,
            },
        )

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
    return render(
        request,
        "reports/upload.html",
        {
            "form": form,
            "organization": organization,
            "is_system_admin": is_system_admin,
            "is_individual": is_individual,
            "organizations": organizations,
        },
    )


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
