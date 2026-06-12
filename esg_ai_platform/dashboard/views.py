import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from analysis.models import IndustryMetricSnapshot
from analysis.services.industry_metrics import industry_detail_context, industry_overview
from reports.models import IndustryCategory, Report


def intro(request):
    return render(request, "dashboard/intro.html", {"intro_metrics": _intro_metrics()})


@login_required
def index(request):
    organization = get_user_organization(request.user)
    if is_system_admin_user(request.user):
        reports = Report.objects.all().select_related("latest_analysis_result", "organization")
        public_reports = reports.filter(status="completed")
    elif is_individual_user(request.user):
        reports = Report.objects.none()
        public_reports = Report.objects.filter(status="completed").select_related("latest_analysis_result", "organization")
    else:
        reports = Report.objects.filter(organization=organization).select_related("latest_analysis_result", "organization") if organization else Report.objects.none()
        public_reports = Report.objects.none()
    completed_reports = reports.filter(status="completed", latest_analysis_result__isnull=False)
    industry_cards = industry_overview(reports)
    total_companies = completed_reports.values("company_name").distinct().count()
    total_reports = completed_reports.count()
    visible_cards = [card for card in industry_cards if card["report_count"]]
    avg_raw = _average_card_value(visible_cards, "average_raw_score")
    avg_disclosure = _average_card_value(visible_cards, "average_disclosure_rate")
    return render(
        request,
        "dashboard/index.html",
        {
            "organization": organization,
            "reports": reports[:8],
            "public_reports": public_reports[:20],
            "is_individual": is_individual_user(request.user),
            "is_system_admin": is_system_admin_user(request.user),
            "industry_cards": industry_cards,
            "total_companies": total_companies,
            "total_reports": total_reports,
            "average_raw_score": avg_raw,
            "average_disclosure_rate": avg_disclosure,
        },
    )


@login_required
def industry_detail(request, industry_name):
    reports = _accessible_reports_for_dashboard(request.user)
    industry = get_object_or_404(IndustryCategory, Q(code=industry_name) | Q(name_zh=industry_name), is_active=True)
    context = industry_detail_context(industry, reports)
    snapshots = context["snapshots"]
    company = request.GET.get("company", "").strip()
    year = request.GET.get("year", "").strip()
    grade = request.GET.get("grade", "").strip()
    sort = request.GET.get("sort", "pr")
    direction = request.GET.get("direction", "desc")
    if company:
        snapshots = [item for item in snapshots if company.lower() in item.report.company_name.lower()]
    if year.isdigit():
        snapshots = [item for item in snapshots if item.report.report_year == int(year)]
    if grade:
        snapshots = [item for item in snapshots if item.grade == grade]
    sort_map = {
        "company": lambda item: item.report.company_name,
        "year": lambda item: item.report.report_year,
        "raw": lambda item: item.raw_score,
        "pr": lambda item: item.percentile_rank,
        "grade": lambda item: _grade_sort_value(item.grade),
        "analyzed": lambda item: item.analysis_result.analyzed_at,
    }
    snapshots = sorted(snapshots, key=sort_map.get(sort, sort_map["pr"]), reverse=direction != "asc")
    context.update(
        {
            "snapshots": snapshots,
            "filters": {"company": company, "year": year, "grade": grade, "sort": sort, "direction": direction},
            "missing_export_url": _export_url(request, "missing_csv"),
            "companies_export_url": _export_url(request, "companies_csv"),
        }
    )
    if request.GET.get("export") == "missing_csv":
        return _industry_missing_csv_response(industry, context["top_missing_items"])
    if request.GET.get("export") == "companies_csv":
        return _industry_companies_csv_response(industry, snapshots)
    return render(request, "dashboard/industry_detail.html", context)


def _accessible_reports_for_dashboard(user):
    if is_system_admin_user(user):
        return Report.objects.all()
    if is_individual_user(user):
        return Report.objects.filter(status="completed")
    organization = get_user_organization(user)
    return Report.objects.filter(organization=organization) if organization else Report.objects.none()


def _average_card_value(cards, key):
    values = [card[key] for card in cards if card["report_count"]]
    if not values:
        return 0
    return sum(values) / len(values)


def _grade_sort_value(grade):
    order = {"A+": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    return order.get(grade, 0)


def _intro_metrics():
    metrics = IndustryMetricSnapshot.objects.filter(report__status="completed")
    aggregate = metrics.aggregate(
        average_pr=Avg("percentile_rank"),
        average_disclosure_rate=Avg("disclosure_rate"),
        benchmark_sample=Count("report_id", distinct=True),
    )
    return {
        "average_pr": _round_metric(aggregate["average_pr"]),
        "average_disclosure_rate": _round_metric(aggregate["average_disclosure_rate"]),
        "benchmark_sample": aggregate["benchmark_sample"] or 0,
    }


def _round_metric(value):
    if value is None:
        return 0
    return int(round(float(value)))


def _export_url(request, export_value):
    params = request.GET.copy()
    params["export"] = export_value
    return f"?{params.urlencode()}"


def _industry_missing_csv_response(industry, top_missing_items):
    response = _csv_response(f"grab_{industry.code}_missing_items.csv")
    writer = csv.writer(response)
    writer.writerow(["排名", "產業代碼", "產業名稱", "缺漏項目", "缺漏次數", "缺漏比例"])
    for index, item in enumerate(top_missing_items, start=1):
        writer.writerow([index, industry.code, industry.name_zh, item["label"], item["count"], f"{item['ratio']}%"])
    return response


def _industry_companies_csv_response(industry, snapshots):
    response = _csv_response(f"grab_{industry.code}_companies.csv")
    writer = csv.writer(response)
    writer.writerow(["公司", "年度", "產業代碼", "產業名稱", "Raw Score", "PR", "Grade", "Z-score", "缺漏數", "揭露完整度", "分析日期"])
    for item in snapshots:
        writer.writerow(
            [
                item.report.company_name,
                item.report.report_year,
                industry.code,
                industry.name_zh,
                item.raw_score,
                item.percentile_rank,
                item.grade,
                item.z_score,
                item.missing_count,
                f"{item.disclosure_rate}%",
                item.analysis_result.analyzed_at.strftime("%Y-%m-%d"),
            ]
        )
    return response


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response
