import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from analysis.models import GeneratedReport
from gri.models import GRIRequiredField
from organizations.models import Organization

from .forms import ReportUploadForm
from .models import AnalysisJob, Report
from .tasks import parse_pdf_task, reanalyze_report_task


def _accessible_reports(user):
    if is_system_admin_user(user):
        return Report.objects.all()
    if is_individual_user(user):
        return Report.objects.filter(status="completed")
    organization = get_user_organization(user)
    if not organization:
        return Report.objects.none()
    return Report.objects.filter(organization=organization)


def _reanalyzable_reports(user):
    if is_system_admin_user(user):
        return Report.objects.all()
    if is_individual_user(user):
        return Report.objects.none()
    organization = get_user_organization(user)
    if not organization:
        return Report.objects.none()
    return Report.objects.filter(organization=organization)


def _field_meaning(field):
    if field.recommendation_template:
        return field.recommendation_template
    return f"{field.disclosure_code} 的「{field.field_label}」用於判斷報告書是否揭露必要的量化數據、方法、來源與管理責任。"


def _comparison_rows(reports):
    required_fields = list(GRIRequiredField.objects.filter(is_active=True, is_required=True).order_by("disclosure_code", "sort_order"))
    field_results_by_report = {}
    report_missing = {
        report.id: {
            (item.disclosure_code, item.item_name)
            for item in report.analysis_result.missing_items.all()
        }
        if report.analysis_result
        else set()
        for report in reports
    }
    for report in reports:
        result = report.analysis_result
        field_map = {}
        if result:
            for disclosure_score in result.disclosure_scores.all():
                for field_result in disclosure_score.agent_output.get("field_results", []):
                    field_map[(disclosure_score.disclosure_code, field_result.get("field_label", ""))] = field_result
        field_results_by_report[report.id] = field_map
    rows = []
    tooltip_payloads = {}
    for field in required_fields:
        label = field.field_label
        key = (field.disclosure_code, label)
        disclosures = []
        for report in reports:
            is_missing = key in report_missing.get(report.id, set())
            if not is_missing:
                disclosures.append(f"{report.company_name} {report.report_year}")
        cells = []
        for report in reports:
            status = "missing" if key in report_missing.get(report.id, set()) else "complete"
            field_result = field_results_by_report.get(report.id, {}).get(key, {})
            tooltip_key = f"{field.disclosure_code}-{field.field_key}-{report.id}"
            tooltip_payloads[tooltip_key] = {
                "company": report.company_name,
                "year": report.report_year,
                "status": status,
                "disclosure_code": field.disclosure_code,
                "field_label": label,
                "page_number": field_result.get("page_number"),
                "evidence_excerpt": field_result.get("evidence_excerpt", ""),
                "meaning": _field_meaning(field),
                "disclosed_companies": disclosures,
            }
            cells.append(
                {
                    "report": report,
                    "status": status,
                    "field_result": field_result,
                    "tooltip_key": tooltip_key,
                }
            )
        rows.append(
            {
                "disclosure_code": field.disclosure_code,
                "field_label": label,
                "cells": cells,
            }
        )
    return rows, tooltip_payloads


@login_required
def report_list(request):
    reports = _accessible_reports(request.user).select_related("latest_analysis_job", "latest_analysis_result", "organization")
    company = request.GET.get("company", "").strip()
    year = request.GET.get("year", "").strip()
    status = request.GET.get("status", "").strip()
    if company:
        reports = reports.filter(company_name__icontains=company)
    if year.isdigit():
        reports = reports.filter(report_year=int(year))
    if status:
        reports = reports.filter(status=status)
    return render(
        request,
        "reports/list.html",
        {
            "reports": reports,
            "filters": {"company": company, "year": year, "status": status},
        },
    )


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
            report.latest_analysis_job = job
            report.save(update_fields=["latest_analysis_job", "updated_at"])
            async_result = parse_pdf_task.delay(report.id, job.id)
            job.celery_task_id = async_result.id
            job.save(update_fields=["celery_task_id"])
            messages.success(request, "報告書已上傳，系統已開始背景分析。")
            return redirect("reports:status", pk=report.pk)
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
    report = get_object_or_404(
        _accessible_reports(request.user).select_related("latest_analysis_result", "latest_analysis_job", "organization"),
        pk=pk,
    )
    analysis_result = report.analysis_result
    generated_report = GeneratedReport.objects.filter(analysis_result=analysis_result).last() if analysis_result else None
    analysis_history = report.analysis_results.select_related("analysis_job").all()
    return render(
        request,
        "reports/detail.html",
        {
            "report": report,
            "generated_report": generated_report,
            "analysis_history": analysis_history,
            "can_reanalyze": _reanalyzable_reports(request.user).filter(pk=report.pk).exists(),
        },
    )


@login_required
def reanalyze_report(request, pk):
    if request.method != "POST":
        return redirect("reports:detail", pk=pk)
    report = get_object_or_404(_reanalyzable_reports(request.user).select_related("organization"), pk=pk)
    job = AnalysisJob.objects.create(report=report, status="uploaded", purpose=AnalysisJob.PURPOSE_REANALYSIS)
    report.latest_analysis_job = job
    report.save(update_fields=["latest_analysis_job", "updated_at"])
    async_result = reanalyze_report_task.delay(report.id, job.id)
    job.celery_task_id = async_result.id
    job.save(update_fields=["celery_task_id"])
    messages.success(request, "已開始重新分析，系統會使用既有 PDF 與最新 GRI 305 規則重新產生結果。")
    return redirect("reports:status", pk=report.pk)


@login_required
def download_original_report(request, pk):
    report = get_object_or_404(_accessible_reports(request.user).select_related("file_record"), pk=pk)
    file_record = getattr(report, "file_record", None)
    if not file_record or not file_record.pdf_file:
        raise Http404("Original PDF not found.")
    return FileResponse(file_record.pdf_file.open("rb"), as_attachment=True, filename=file_record.original_filename)


@login_required
def download_generated_report(request, pk):
    report = get_object_or_404(_accessible_reports(request.user).select_related("latest_analysis_result"), pk=pk)
    generated = GeneratedReport.objects.filter(analysis_result=report.analysis_result).last()
    if not generated or not generated.file:
        raise Http404("Generated report not found.")
    filename = generated.file.name.rsplit("/", 1)[-1]
    return FileResponse(generated.file.open("rb"), as_attachment=True, filename=filename)


@login_required
def report_status(request, pk):
    report = get_object_or_404(
        _accessible_reports(request.user).select_related("latest_analysis_job", "latest_analysis_result", "organization"),
        pk=pk,
    )
    return render(request, "reports/status.html", {"report": report})


@login_required
def report_status_json(request, pk):
    report = get_object_or_404(
        _accessible_reports(request.user).select_related("latest_analysis_job", "latest_analysis_result"),
        pk=pk,
    )
    job = report.analysis_job
    status = job.status if job else report.status
    progress = job.progress if job else 0
    return JsonResponse(
        {
            "status": status,
            "progress": progress,
            "completed": status == "completed",
            "failed": status == "failed",
            "detail_url": reverse("reports:detail", kwargs={"pk": report.pk}) if status == "completed" else "",
            "dashboard_url": reverse("dashboard:index") if status == "completed" else "",
            "error_message": job.error_message if job else "",
        }
    )


@login_required
def compare_reports(request):
    reports_qs = (
        _accessible_reports(request.user)
        .filter(latest_analysis_result__isnull=False)
        .select_related("latest_analysis_result", "organization")
        .prefetch_related("latest_analysis_result__missing_items", "latest_analysis_result__disclosure_scores")
        .order_by("-created_at")
    )
    selected_ids = [int(value) for value in request.GET.getlist("report_ids") if value.isdigit()]
    selected_reports = list(reports_qs.filter(id__in=selected_ids)) if selected_ids else list(reports_qs[:4])
    rows, tooltip_payloads = _comparison_rows(selected_reports)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="aixesg_report_comparison.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["GRI", "欄位", *[f"{report.company_name} {report.report_year}" for report in selected_reports]])
        for row in rows:
            writer.writerow([row["disclosure_code"], row["field_label"], *[cell["status"] for cell in row["cells"]]])
        return response

    return render(
        request,
        "reports/compare.html",
        {
            "reports": reports_qs[:50],
            "selected_reports": selected_reports,
            "selected_ids": selected_ids,
            "comparison_rows": rows,
            "comparison_tooltips": tooltip_payloads,
        },
    )


@login_required
def ranking_reports(request):
    reports = (
        _accessible_reports(request.user)
        .filter(latest_analysis_result__isnull=False)
        .select_related("latest_analysis_result", "organization")
        .order_by("-latest_analysis_result__total_score", "-report_year", "company_name")
    )
    company = request.GET.get("company", "").strip()
    year = request.GET.get("year", "").strip()
    if company:
        reports = reports.filter(company_name__icontains=company)
    if year.isdigit():
        reports = reports.filter(report_year=int(year))
    return render(request, "reports/ranking.html", {"reports": reports[:100], "filters": {"company": company, "year": year}})
