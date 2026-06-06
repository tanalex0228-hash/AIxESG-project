from django.test import TestCase

from analysis.services.analysis_runner import run_gri_305_analysis
from analysis.services.knowledge_base_importer import import_knowledge_base
from benchmarks.models import BenchmarkCompany, BenchmarkGoldStandard, BenchmarkGri305
from gri.models import GRIDisclosureRule, GRIRequiredField, GRIScoringWeight
from organizations.models import Organization
from rag.models import Embedding, VectorChunk, VectorDocument
from reports.models import Report, ReportChunk


class KnowledgeBaseImportTests(TestCase):
    def test_import_knowledge_base_creates_structured_rules_benchmarks_and_vectors(self):
        summary = import_knowledge_base()

        self.assertEqual(summary["rules"], 5)
        self.assertEqual(summary["weights"], 24)
        self.assertEqual(summary["required_fields"], 27)
        self.assertEqual(BenchmarkCompany.objects.filter(company_id__in=["TW_2395", "TW_1504", "TW_2049"]).count(), 3)
        self.assertGreaterEqual(BenchmarkGri305.objects.count(), 60)
        self.assertEqual(BenchmarkGoldStandard.objects.count(), 3)
        self.assertGreaterEqual(VectorDocument.objects.count(), 4)
        self.assertGreaterEqual(VectorChunk.objects.count(), 4)
        self.assertEqual(Embedding.objects.count(), VectorChunk.objects.count())
        self.assertTrue(GRIDisclosureRule.objects.filter(disclosure_code="305-1").exists())
        self.assertTrue(GRIScoringWeight.objects.filter(disclosure_code="305-3", field_key="Categories_Breakdown").exists())
        self.assertTrue(GRIRequiredField.objects.filter(disclosure_code="305-5", field_key="Carbon_Offsets").exists())

    def test_rule_engine_scores_from_weights_and_creates_gap_analysis(self):
        import_knowledge_base()
        organization = Organization.objects.create(name="桓達企業")
        report = Report.objects.create(
            organization=organization,
            company_name="桓達企業",
            report_year=2025,
            title="桓達企業永續報告書",
            industry_category="工業感測",
        )
        ReportChunk.objects.create(
            report=report,
            page_start=1,
            page_end=1,
            chunk_text=(
                "Scope 1 範疇一直接溫室氣體排放量為 1,234 tCO2e。氣體包含 CO2、CH4、N2O。"
                "基準年為 2022，基準年排放量為 1,380 tCO2e，排放係數採環境部公告係數，"
                "盤查邊界採營運控制法，方法學依 ISO 14064-1:2018。"
                "Scope 3 範疇三其他間接排放總量為 9,876 tCO2e，類別包含 Purchased Goods and Services、"
                "Capital Goods、Waste Generated in Operations、Use of Sold Products，方法學依 GHG Protocol，排放係數採 DEFRA。"
            ),
            token_count=160,
        )

        result = run_gri_305_analysis(report)

        self.assertEqual(result.raw_output["score_source"], "rule_engine")
        self.assertEqual(result.disclosure_scores.count(), 5)
        self.assertGreater(result.total_score, 0)
        self.assertGreater(result.missing_items.count(), 0)
        self.assertIn("benchmark_comparison", result.raw_output)
        self.assertIn("dynamic_conclusion", result.raw_output)
        self.assertIn("Business Travel", result.raw_output["benchmark_comparison"]["missing_categories"])
