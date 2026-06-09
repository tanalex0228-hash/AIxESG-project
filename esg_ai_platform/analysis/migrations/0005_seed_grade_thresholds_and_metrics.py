from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


GRADE_DEFAULTS = [
    ("A+", Decimal("90"), 1),
    ("A", Decimal("75"), 2),
    ("B", Decimal("50"), 3),
    ("C", Decimal("25"), 4),
    ("D", Decimal("0"), 5),
]


def _round(value, places="0.01"):
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _grade_for_pr(percentile_rank):
    for grade, minimum, _sort_order in GRADE_DEFAULTS:
        if percentile_rank >= minimum:
            return grade
    return "D"


def seed_thresholds_and_metrics(apps, schema_editor):
    GradeThreshold = apps.get_model("analysis", "GradeThreshold")
    IndustryMetricSnapshot = apps.get_model("analysis", "IndustryMetricSnapshot")
    Report = apps.get_model("reports", "Report")

    for grade, min_pr, sort_order in GRADE_DEFAULTS:
        GradeThreshold.objects.update_or_create(
            grade=grade,
            defaults={"min_percentile_rank": min_pr, "sort_order": sort_order, "is_active": True},
        )

    industry_ids = list(
        Report.objects.filter(status="completed", latest_analysis_result__isnull=False, industry_category_ref__isnull=False)
        .values_list("industry_category_ref_id", flat=True)
        .distinct()
    )
    for industry_id in industry_ids:
        reports = list(
            Report.objects.filter(
                status="completed",
                latest_analysis_result__isnull=False,
                industry_category_ref_id=industry_id,
            ).select_related("latest_analysis_result", "industry_category_ref")
        )
        if not reports:
            continue
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
            disclosure_scores = list(result.disclosure_scores.all())
            if disclosure_scores:
                complete = sum(1 for score in disclosure_scores if score.status == "complete")
                partial = sum(1 for score in disclosure_scores if score.status == "partial")
                disclosure_rate = ((Decimal(complete) + Decimal("0.5") * Decimal(partial)) / Decimal(len(disclosure_scores))) * Decimal("100")
            else:
                disclosure_rate = Decimal("0")
            IndustryMetricSnapshot.objects.update_or_create(
                report=report,
                defaults={
                    "analysis_result": result,
                    "industry_id": industry_id,
                    "raw_score": _round(raw_score),
                    "percentile_rank": _round(percentile_rank),
                    "z_score": _round(z_score, "0.001"),
                    "grade": _grade_for_pr(percentile_rank),
                    "disclosure_rate": _round(disclosure_rate),
                    "missing_count": result.missing_items.count(),
                    "recommendation_count": result.recommendations.count(),
                    "benchmark_sample_size": sample_size,
                },
            )


def reverse_seed(apps, schema_editor):
    GradeThreshold = apps.get_model("analysis", "GradeThreshold")
    IndustryMetricSnapshot = apps.get_model("analysis", "IndustryMetricSnapshot")
    IndustryMetricSnapshot.objects.all().delete()
    GradeThreshold.objects.filter(grade__in=[grade for grade, _minimum, _sort_order in GRADE_DEFAULTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0004_seed_industry_categories"),
        ("analysis", "0004_gradethreshold_industrymetricsnapshot"),
    ]

    operations = [
        migrations.RunPython(seed_thresholds_and_metrics, reverse_seed),
    ]
