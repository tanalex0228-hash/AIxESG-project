import csv
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from analysis.models import GeneratedReport, IndustryMetricSnapshot
from analysis.services.industry_metrics import industry_comparison_context, recalculate_industry_metrics
from gri.models import GRIRequiredField
from organizations.models import Organization

from .forms import ReportUploadForm
from .models import AnalysisJob, IndustryCategory, Report
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


def _deletable_reports(user):
    return _reanalyzable_reports(user)


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
            "can_delete_reports": _deletable_reports(request.user).exists(),
        },
    )


@login_required
def delete_report(request, pk):
    if request.method != "POST":
        return redirect("reports:list")
    report = get_object_or_404(_deletable_reports(request.user), pk=pk)
    industry = report.industry_category_ref
    _delete_report_files(report)
    title = str(report)
    report.delete()
    if industry:
        recalculate_industry_metrics(industry)
    messages.success(request, f"已刪除 {title}。")
    return redirect("reports:list")


def _delete_report_files(report):
    file_record = getattr(report, "file_record", None)
    if file_record and file_record.pdf_file:
        file_record.pdf_file.delete(save=False)
    generated_reports = GeneratedReport.objects.filter(analysis_result__report=report)
    for generated in generated_reports:
        if generated.file:
            generated.file.delete(save=False)


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
    mode = request.GET.get("mode", "company")
    reports_qs = (
        _accessible_reports(request.user)
        .filter(latest_analysis_result__isnull=False)
        .select_related("latest_analysis_result", "organization", "industry_category_ref", "industry_metric", "industry_metric__industry")
        .prefetch_related("latest_analysis_result__missing_items", "latest_analysis_result__disclosure_scores")
        .order_by("-created_at")
    )
    selected_ids = [int(value) for value in request.GET.getlist("report_ids") if value.isdigit()]
    selected_industry_codes = [value for value in request.GET.getlist("industry_codes") if value]
    selected_reports = list(reports_qs.filter(id__in=selected_ids)) if selected_ids else list(_filter_compare_reports(reports_qs, request.GET)[:4])
    rows, tooltip_payloads = _comparison_rows(selected_reports)
    industry_comparison_rows = industry_comparison_context(_accessible_reports(request.user), selected_industry_codes) if mode == "industry" and selected_industry_codes else []

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
            "mode": mode,
            "industries": IndustryCategory.objects.filter(is_active=True).order_by("code"),
            "selected_industry_codes": selected_industry_codes,
            "industry_comparison_rows": industry_comparison_rows,
            "comparison_rows": rows,
            "comparison_tooltips": tooltip_payloads,
        },
    )


@login_required
def compare_options_json(request):
    mode = request.GET.get("mode", "company")
    reports = (
        _accessible_reports(request.user)
        .filter(latest_analysis_result__isnull=False)
        .select_related("industry_category_ref", "latest_analysis_result", "industry_metric", "industry_metric__industry")
    )
    reports = _filter_compare_reports(reports, request.GET)
    if mode == "industry":
        industry_codes = list(reports.filter(industry_category_ref__isnull=False).values_list("industry_category_ref__code", flat=True).distinct()[:100])
        industries = IndustryCategory.objects.filter(code__in=industry_codes).order_by("code")
        rows = industry_comparison_context(_accessible_reports(request.user), [industry.code for industry in industries])
        return JsonResponse(
            {
                "mode": "industry",
                "industries": [
                    {
                        "code": row["industry"].code,
                        "name": row["industry"].name_zh,
                        "company_count": row["company_count"],
                        "report_count": row["report_count"],
                        "average_raw_score": str(row["average_raw_score"]),
                        "average_pr": str(row["average_pr"]),
                        "average_disclosure_rate": str(row["average_disclosure_rate"]),
                        "average_missing_count": str(row["average_missing_count"]),
                        "confidence_level": row["confidence_level"],
                    }
                    for row in rows
                ],
            }
        )
    report_list = list(reports[:100])
    metrics = {
        metric.report_id: metric
        for metric in IndustryMetricSnapshot.objects.filter(report__in=report_list).select_related("industry")
    }
    return JsonResponse(
        {
            "mode": "company",
            "reports": [
                {
                    "id": report.id,
                    "company": report.company_name,
                    "year": report.report_year,
                    "title": report.title,
                    "industry": report.industry_category_ref.name_zh if report.industry_category_ref else report.industry_category,
                    "industry_code": report.industry_category_ref.code if report.industry_category_ref else "",
                    "grade": metrics.get(report.id).grade if metrics.get(report.id) else "",
                    "pr": str(metrics.get(report.id).percentile_rank) if metrics.get(report.id) else "",
                }
                for report in report_list
            ],
        }
    )


def _filter_compare_reports(reports, params):
    industry = params.get("industry", "").strip()
    year = params.get("year", "").strip()
    grade = params.get("grade", "").strip()
    company = params.get("company", "").strip()
    pr_min = params.get("pr_min", "").strip()
    pr_max = params.get("pr_max", "").strip()
    if industry:
        reports = reports.filter(industry_category_ref__code=industry)
    if year.isdigit():
        reports = reports.filter(report_year=int(year))
    if company:
        reports = reports.filter(company_name__icontains=company)
    metric_filters = Q()
    if grade:
        metric_filters &= Q(industry_metric__grade=grade)
    min_pr = _parse_decimal(pr_min)
    max_pr = _parse_decimal(pr_max)
    if min_pr is not None:
        metric_filters &= Q(industry_metric__percentile_rank__gte=min_pr)
    if max_pr is not None:
        metric_filters &= Q(industry_metric__percentile_rank__lte=max_pr)
    if metric_filters:
        reports = reports.filter(metric_filters)
    return reports.order_by("-report_year", "company_name")


@login_required
def ranking_reports(request):
    accessible_ids = _accessible_reports(request.user).filter(latest_analysis_result__isnull=False).values_list("id", flat=True)
    metrics = (
        IndustryMetricSnapshot.objects.filter(report_id__in=accessible_ids)
        .select_related("industry", "report", "analysis_result")
        .order_by("-percentile_rank", "-raw_score", "report__company_name")
    )
    company = request.GET.get("company", "").strip()
    year = request.GET.get("year", "").strip()
    industry = request.GET.get("industry", "").strip()
    grade = request.GET.get("grade", "").strip()
    pr_min = request.GET.get("pr_min", "").strip()
    pr_max = request.GET.get("pr_max", "").strip()
    raw_min = request.GET.get("raw_min", "").strip()
    raw_max = request.GET.get("raw_max", "").strip()
    sort = request.GET.get("sort", "pr").strip()
    direction = request.GET.get("direction", "desc").strip()
    if company:
        metrics = metrics.filter(report__company_name__icontains=company)
    if year.isdigit():
        metrics = metrics.filter(report__report_year=int(year))
    if industry:
        metrics = metrics.filter(industry__code=industry)
    if grade:
        metrics = metrics.filter(grade=grade)
    metrics = _apply_decimal_range(metrics, "percentile_rank", pr_min, pr_max)
    metrics = _apply_decimal_range(metrics, "raw_score", raw_min, raw_max)
    order_field = _ranking_order_field(sort)
    if direction == "asc":
        metrics = metrics.order_by(order_field, "report__company_name")
    else:
        metrics = metrics.order_by(f"-{order_field}", "report__company_name")
    if request.GET.get("export") == "csv":
        return _ranking_csv_response(metrics)
    return render(
        request,
        "reports/ranking.html",
        {
            "metrics": metrics[:100],
            "industries": IndustryCategory.objects.filter(is_active=True).order_by("code"),
            "filters": {
                "company": company,
                "year": year,
                "industry": industry,
                "grade": grade,
                "pr_min": pr_min,
                "pr_max": pr_max,
                "raw_min": raw_min,
                "raw_max": raw_max,
                "sort": sort,
                "direction": direction,
            },
            "sort_links": _ranking_sort_links(request),
            "export_url": _export_url(request, "csv"),
        },
    )


def _ranking_csv_response(metrics):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="aixesg_ranking.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["排名", "公司", "年度", "產業代碼", "產業名稱", "報告", "Raw Score", "PR", "Grade", "Z-score", "缺漏數", "揭露率", "分析日期"])
    for index, metric in enumerate(metrics, start=1):
        writer.writerow(
            [
                index,
                metric.report.company_name,
                metric.report.report_year,
                metric.industry.code,
                metric.industry.name_zh,
                metric.report.title,
                metric.raw_score,
                metric.percentile_rank,
                metric.grade,
                metric.z_score,
                metric.missing_count,
                f"{metric.disclosure_rate}%",
                metric.analysis_result.analyzed_at.strftime("%Y-%m-%d"),
            ]
        )
    return response


def _export_url(request, export_value):
    params = request.GET.copy()
    params["export"] = export_value
    return f"?{params.urlencode()}"


def _apply_decimal_range(queryset, field, minimum, maximum):
    minimum_value = _parse_decimal(minimum)
    maximum_value = _parse_decimal(maximum)
    if minimum_value is not None:
        queryset = queryset.filter(**{f"{field}__gte": minimum_value})
    if maximum_value is not None:
        queryset = queryset.filter(**{f"{field}__lte": maximum_value})
    return queryset


def _parse_decimal(value):
    if value == "":
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def _ranking_order_field(sort):
    return {
        "company": "report__company_name",
        "year": "report__report_year",
        "industry": "industry__code",
        "raw": "raw_score",
        "pr": "percentile_rank",
        "grade": "grade",
        "z": "z_score",
        "missing": "missing_count",
        "disclosure": "disclosure_rate",
        "analyzed": "analysis_result__analyzed_at",
    }.get(sort, "percentile_rank")


def _ranking_sort_links(request):
    links = {}
    current_sort = request.GET.get("sort", "pr")
    current_direction = request.GET.get("direction", "desc")
    for key in ["company", "year", "industry", "raw", "pr", "grade", "z", "missing", "disclosure", "analyzed"]:
        params = request.GET.copy()
        next_direction = "asc" if current_sort != key or current_direction == "desc" else "desc"
        params["sort"] = key
        params["direction"] = next_direction
        links[key] = f"?{params.urlencode()}"
    return links
