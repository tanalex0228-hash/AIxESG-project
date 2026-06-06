from django.test import TestCase

from analysis.agents.document_locator import DocumentLocatorAgent
from analysis.services.analysis_runner import run_gri_305_analysis
from gri.models import GRICheckItem, GRIDisclosure, GRIStandard, ScoringWeight
from organizations.models import Organization
from reports.models import AnalysisJob, Report, ReportChunk


class AnalysisPipelineTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Acme ESG")
        self.report = Report.objects.create(
            organization=self.organization,
            company_name="Acme ESG",
            report_year=2025,
            title="Sustainability Report",
            industry_category="Electronics",
        )
        AnalysisJob.objects.create(report=self.report)
        self.standard = GRIStandard.objects.create(code="GRI 305", name="Emissions", version="2021")
        weights = {"305-1": 25, "305-2": 25, "305-3": 20, "305-4": 15, "305-5": 15}
        for code, weight in weights.items():
            disclosure = GRIDisclosure.objects.create(
                standard=self.standard,
                disclosure_code=code,
                disclosure_name=code,
                weight=weight,
                version="2021",
            )
            ScoringWeight.objects.create(disclosure=disclosure, weight_percent=weight)
            GRICheckItem.objects.create(disclosure=disclosure, name="排放量", sort_order=1)

    def test_document_locator_finds_scope_1_evidence(self):
        ReportChunk.objects.create(
            report=self.report,
            page_start=42,
            page_end=42,
            chunk_text="本公司 Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e。",
            token_count=30,
        )

        result = DocumentLocatorAgent().run(self.report, "305-1")

        self.assertEqual(result["matches"][0]["page_number"], 42)

    def test_analysis_runner_creates_scores_and_citations(self):
        ReportChunk.objects.create(
            report=self.report,
            page_start=42,
            page_end=42,
            chunk_text="本公司 Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e。",
            token_count=30,
        )

        result = run_gri_305_analysis(self.report)

        self.assertEqual(result.disclosure_scores.count(), 5)
        self.assertGreaterEqual(result.evidence_citations.count(), 1)

    def test_analysis_runner_preserves_previous_versions(self):
        ReportChunk.objects.create(
            report=self.report,
            page_start=42,
            page_end=42,
            chunk_text="本公司 Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e。",
            token_count=30,
        )

        first = run_gri_305_analysis(self.report)
        second = run_gri_305_analysis(self.report)
        self.report.refresh_from_db()

        self.assertEqual(self.report.analysis_results.count(), 2)
        self.assertEqual(first.version_number, 1)
        self.assertEqual(second.version_number, 2)
        self.assertFalse(self.report.analysis_results.get(pk=first.pk).is_latest)
        self.assertEqual(self.report.analysis_result, second)
