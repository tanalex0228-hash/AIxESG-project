from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
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
        }
    )
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
