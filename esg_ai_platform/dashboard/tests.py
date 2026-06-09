from django.test import TestCase
from django.urls import reverse

from analysis.models import AnalysisResult, IndustryMetricSnapshot
from organizations.models import Organization
from reports.models import IndustryCategory, Report


class IntroPageTests(TestCase):
    def test_intro_page_is_public_and_distinct_from_dashboard(self):
        response = self.client.get(reverse("dashboard:intro"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carbon Disclosure Intelligence Platform")
        self.assertContains(response, "讓永續報告")
        self.assertContains(response, "founder-portrait.png")

    def test_intro_page_uses_live_metric_snapshot_values(self):
        organization = Organization.objects.create(name="Intro Org")
        industry, _ = IndustryCategory.objects.get_or_create(code="24", defaults={"name_zh": "半導體業", "name_en": "Semiconductor"})
        report = Report.objects.create(
            organization=organization,
            company_name="台積電",
            report_year=2024,
            title="2024 Sustainability Report",
            status="completed",
            industry_category_ref=industry,
        )
        result = AnalysisResult.objects.create(report=report, total_score=88)
        IndustryMetricSnapshot.objects.create(
            report=report,
            analysis_result=result,
            industry=industry,
            raw_score=88,
            percentile_rank=76,
            disclosure_rate=64,
            benchmark_sample_size=1,
        )

        response = self.client.get(reverse("dashboard:intro"))

        self.assertContains(response, 'data-counter="76"')
        self.assertContains(response, 'data-counter="64" data-suffix="%"')
        self.assertContains(response, 'data-counter="1"')
