from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

from analysis.models import GradeThreshold, IndustryMetricSnapshot
from reports.models import IndustryCategory, Report
from reports.services.industry_classification import (
    ensure_standard_industries,
    normalize_report_industry,
)

GRADE_DEFAULTS = [
    ("A+", Decimal("90"), 1),
    ("A", Decimal("75"), 2),
    ("B", Decimal("50"), 3),
    ("C", Decimal("25"), 4),
    ("D", Decimal("0"), 5),
]


def _round(value, places="0.01"):
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def ensure_grade_thresholds():
    thresholds = []
    for grade, min_pr, sort_order in GRADE_DEFAULTS:
        threshold, _ = GradeThreshold.objects.update_or_create(
            grade=grade,
            defaults={"min_percentile_rank": min_pr, "sort_order": sort_order, "is_active": True},
        )
        thresholds.append(threshold)
    return thresholds


def grade_for_pr(percentile_rank):
    ensure_grade_thresholds()
    percentile_rank = Decimal(percentile_rank)
    threshold = GradeThreshold.objects.filter(is_active=True, min_percentile_rank__lte=percentile_rank).order_by("-min_percentile_rank").first()
    return threshold.grade if threshold else "D"


def confidence_level(sample_size):
    if sample_size >= 20:
        return "High"
    if sample_size >= 8:
        return "Medium"
    return "Low"


def disclosure_rate_for_result(result):
    scores = list(result.disclosure_scores.all())
    if not scores:
        return Decimal("0")
    complete = sum(1 for score in scores if score.status == "complete")
    partial = sum(1 for score in scores if score.status == "partial")
    rate = ((Decimal(complete) + Decimal("0.5") * Decimal(partial)) / Decimal(len(scores))) * Decimal("100")
    return _round(rate)


def completed_reports_qs():
    return (
        Report.objects.filter(status="completed", latest_analysis_result__isnull=False, industry_category_ref__isnull=False)
        .select_related("latest_analysis_result", "industry_category_ref", "organization")
        .prefetch_related(
            "latest_analysis_result__disclosure_scores",
            "latest_analysis_result__missing_items",
            "latest_analysis_result__recommendations",
        )
    )


def normalize_all_report_industries():
    ensure_standard_industries()
    for report in Report.objects.all().select_related("industry_category_ref"):
        normalize_report_industry(report)


def recalculate_industry_metrics(industry=None):
    ensure_standard_industries()
    ensure_grade_thresholds()
    if industry is None:
        normalize_all_report_industries()
        industries = list(IndustryCategory.objects.filter(is_active=True))
    else:
        industries = [industry]
    for category in industries:
        _recalculate_one_industry(category)


def recalculate_report_industry_metrics(report):
    category = normalize_report_industry(report)
    if category:
        recalculate_industry_metrics(category)


def _recalculate_one_industry(category):
    reports = list(completed_reports_qs().filter(industry_category_ref=category))
    if not reports:
        return
    scores = [Decimal(report.latest_analysis_result.total_score) for report in reports]
    sample_size = len(scores)
    average = sum(scores, Decimal("0")) / Decimal(sample_size)
    variance = sum((score - average) ** 2 for score in scores) / Decimal(sample_size)
    stddev = Decimal(str(float(variance) ** 0.5)) if variance else Decimal("0")

    for report in reports:
        result = report.latest_analysis_result
        raw_score = Decimal(result.total_score)
        lower = sum(1 for score in scores if score < raw_score)
        tied = sum(1 for score in scores if score == raw_score)
        percentile_rank = ((Decimal(lower) + Decimal("0.5") * Decimal(tied)) / Decimal(sample_size)) * Decimal("100")
        z_score = (raw_score - average) / stddev if stddev else Decimal("0")
        IndustryMetricSnapshot.objects.update_or_create(
            report=report,
            defaults={
                "analysis_result": result,
                "industry": category,
                "raw_score": _round(raw_score),
                "percentile_rank": _round(percentile_rank),
                "z_score": _round(z_score, "0.001"),
                "grade": grade_for_pr(percentile_rank),
                "disclosure_rate": disclosure_rate_for_result(result),
                "missing_count": result.missing_items.count(),
                "recommendation_count": result.recommendations.count(),
                "benchmark_sample_size": sample_size,
            },
        )


def industry_overview(accessible_reports):
    ensure_standard_industries()
    report_ids = list(accessible_reports.filter(status="completed", latest_analysis_result__isnull=False).values_list("id", flat=True))
    snapshots = (
        IndustryMetricSnapshot.objects.filter(report_id__in=report_ids)
        .select_related("industry", "report", "analysis_result")
        .prefetch_related("analysis_result__missing_items")
    )
    grouped = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.industry_id].append(snapshot)

    cards = []
    for category in IndustryCategory.objects.filter(is_active=True).order_by("code"):
        items = grouped.get(category.id, [])
        company_count = len({item.report.company_name for item in items})
        report_count = len(items)
        avg_raw = _average([item.raw_score for item in items])
        avg_pr = _average([item.percentile_rank for item in items])
        avg_disclosure = _average([item.disclosure_rate for item in items])
        avg_missing = _average([Decimal(item.missing_count) for item in items])
        missing_items = _most_common_missing(items)
        cards.append(
            {
                "industry": category,
                "company_count": company_count,
                "report_count": report_count,
                "average_raw_score": avg_raw,
                "average_pr": avg_pr,
                "average_disclosure_rate": avg_disclosure,
                "average_missing_count": avg_missing,
                "most_common_missing_items": missing_items,
                "confidence_level": confidence_level(company_count),
            }
        )
    return cards


def industry_detail_context(industry, accessible_reports):
    report_ids = list(accessible_reports.filter(status="completed", latest_analysis_result__isnull=False, industry_category_ref=industry).values_list("id", flat=True))
    snapshots = (
        IndustryMetricSnapshot.objects.filter(report_id__in=report_ids)
        .select_related("industry", "report", "analysis_result")
        .prefetch_related("analysis_result__missing_items")
    )
    items = list(snapshots)
    return {
        "industry": industry,
        "company_count": len({item.report.company_name for item in items}),
        "report_count": len(items),
        "average_raw_score": _average([item.raw_score for item in items]),
        "average_pr": _average([item.percentile_rank for item in items]),
        "average_disclosure_rate": _average([item.disclosure_rate for item in items]),
        "average_missing_count": _average([Decimal(item.missing_count) for item in items]),
        "most_common_missing_items": _most_common_missing(items),
        "scope_disclosure": _scope_disclosure(items),
        "best_performers": sorted(items, key=lambda item: (item.percentile_rank, item.raw_score), reverse=True)[:5],
        "confidence_level": confidence_level(len({item.report.company_name for item in items})),
        "snapshots": items,
    }


def _average(values):
    values = [Decimal(value) for value in values]
    if not values:
        return Decimal("0.00")
    return _round(sum(values, Decimal("0")) / Decimal(len(values)))


def _most_common_missing(snapshots, limit=3):
    counter = Counter()
    for snapshot in snapshots:
        for item in snapshot.analysis_result.missing_items.all():
            counter[f"{item.disclosure_code} {item.item_name}"] += 1
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def _scope_disclosure(snapshots):
    scope_codes = {
        "scope_1": "305-1",
        "scope_2": "305-2",
        "scope_3": "305-3",
        "reduction": "305-5",
    }
    totals = {key: 0 for key in scope_codes}
    disclosed = {key: 0 for key in scope_codes}
    for snapshot in snapshots:
        score_by_code = {score.disclosure_code: score for score in snapshot.analysis_result.disclosure_scores.all()}
        for key, code in scope_codes.items():
            totals[key] += 1
            score = score_by_code.get(code)
            if score and score.status in {"complete", "partial"}:
                disclosed[key] += 1
    return {
        key: _round((Decimal(disclosed[key]) / Decimal(totals[key])) * Decimal("100")) if totals[key] else Decimal("0.00")
        for key in scope_codes
    }
