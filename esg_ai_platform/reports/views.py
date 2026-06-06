import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from analysis.models import GeneratedReport
from gri.models import GRIRequiredField
from organizations.models import Organization

from .forms import ReportUploadForm
from .models import AnalysisJob, Report
from .tasks import parse_pdf_task


def _accessible_reports(user):
    if is_system_admin_user(user):
        return Report.objects.all()
    if is_individual_user(user):
        return Report.objects.filter(status="completed")
    organization = get_user_organization(user)
    if not organization:
        return Report.objects.none()
    return Report.objects.filter(organization=organization)


def _comparison_rows(reports):
    required_fields = list(GRIRequiredField.objects.filter(is_active=True, is_required=True).order_by("disclosure_code", "sort_order"))
    report_missing = {
        report.id: {
            (item.disclosure_code, item.item_name)
            for item in report.analysis_result.missing_items.all()
        }
        if hasattr(report, "analysis_result")
        else set()
        for report in reports
    }
    rows = []
    for field in required_fields:
        label = field.field_label
        key = (field.disclosure_code, label)
        rows.append(
            {
                "disclosure_code": field.disclosure_code,
                "field_label": label,
                "cells": [
                    {
                        "report": report,
                        "status": "missing" if key in report_missing.get(report.id, set()) else "complete",
                    }
                    for report in reports
                ],
            }
        )
    return rows


@login_required
def report_list(request):
    reports = _accessible_reports(request.user).select_related("analysis_job", "analysis_result", "organization")
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
        _accessible_reports(request.user).select_related("analysis_result", "analysis_job", "organization"),
        pk=pk,
    )
    analysis_result = getattr(report, "analysis_result", None)
    generated_report = GeneratedReport.objects.filter(analysis_result=analysis_result).last() if analysis_result else None
    return render(request, "reports/detail.html", {"report": report, "generated_report": generated_report})


@login_required
def report_status(request, pk):
    report = get_object_or_404(
        _accessible_reports(request.user).select_related("analysis_job", "analysis_result", "organization"),
        pk=pk,
    )
    return render(request, "reports/status.html", {"report": report})


@login_required
def report_status_json(request, pk):
    report = get_object_or_404(
        _accessible_reports(request.user).select_related("analysis_job", "analysis_result"),
        pk=pk,
    )
    job = getattr(report, "analysis_job", None)
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
        .filter(analysis_result__isnull=False)
        .select_related("analysis_result", "organization")
        .prefetch_related("analysis_result__missing_items")
        .order_by("-created_at")
    )
    selected_ids = [int(value) for value in request.GET.getlist("report_ids") if value.isdigit()]
    selected_reports = list(reports_qs.filter(id__in=selected_ids)) if selected_ids else list(reports_qs[:4])
    rows = _comparison_rows(selected_reports)

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
        },
    )
