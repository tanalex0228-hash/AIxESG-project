from decimal import Decimal

from django.db import transaction

from analysis.agents.benchmark import BenchmarkAgent
from analysis.agents.disclosure_check import DisclosureCheckAgent
from analysis.agents.document_locator import DocumentLocatorAgent
from analysis.agents.quantitative import QuantitativeCompletenessAgent
from analysis.agents.recommendation import RecommendationAgent
from analysis.agents.scoring import ScoringAgent
from analysis.models import (
    AnalysisResult,
    DisclosureScore,
    EvidenceCitation,
    ImprovementRecommendation,
    MissingItem,
)
from gri.models import GRIDisclosure


@transaction.atomic
def run_gri_305_analysis(report):
    result, _ = AnalysisResult.objects.update_or_create(
        report=report,
        defaults={
            "summary": "GRI 305 溫室氣體揭露智慧診斷已完成。",
            "model_name": "mock-local",
        },
    )
    result.disclosure_scores.all().delete()
    result.missing_items.all().delete()
    result.evidence_citations.all().delete()
    result.recommendations.all().delete()

    locator = DocumentLocatorAgent()
    checker = DisclosureCheckAgent()
    quantitative_agent = QuantitativeCompletenessAgent()
    scorer = ScoringAgent()
    benchmark_agent = BenchmarkAgent()
    recommender = RecommendationAgent()

    total_score = Decimal("0")
    confidence_values = []
    disclosures = GRIDisclosure.objects.filter(disclosure_code__in=["305-1", "305-2", "305-3", "305-4", "305-5"], is_active=True)

    for disclosure in disclosures:
        located = locator.run(report, disclosure.disclosure_code)
        check = checker.run(disclosure, located)
        quantitative = quantitative_agent.run(located["matches"])
        score = scorer.run(disclosure, check, quantitative)
        benchmark = benchmark_agent.run(disclosure.disclosure_code)

        disclosure_score = DisclosureScore.objects.create(
            analysis_result=result,
            disclosure_code=disclosure.disclosure_code,
            status=score["status"],
            raw_score=score["raw_score"],
            weighted_score=score["weighted_score"],
            weight_percent=score["weight_percent"],
            confidence=check["confidence"],
            summary=check["summary"],
            agent_output={"located": located, "quantitative": quantitative, "benchmark": benchmark},
        )
        total_score += Decimal(str(score["weighted_score"]))
        confidence_values.append(Decimal(str(check["confidence"])))

        for match in located["matches"]:
            EvidenceCitation.objects.create(
                analysis_result=result,
                disclosure_score=disclosure_score,
                report=report,
                disclosure_code=disclosure.disclosure_code,
                page_number=match["page_number"],
                quoted_text=match["quoted_text"],
                normalized_finding=f"系統定位到與 {disclosure.disclosure_code} 相關揭露。",
                confidence_score=match["confidence"],
                source_chunk_id=match["chunk_id"],
                start_char=0,
                end_char=len(match["quoted_text"]),
                evidence_type="text",
            )

        if score["status"] != "complete":
            for check_item in disclosure.check_items.filter(is_active=True, is_required=True):
                MissingItem.objects.create(
                    analysis_result=result,
                    disclosure_score=disclosure_score,
                    disclosure_code=disclosure.disclosure_code,
                    item_name=check_item.name,
                    description=check_item.description,
                    severity="high" if score["status"] == "missing" else "medium",
                    priority=check_item.sort_order,
                )
            for item in recommender.run(disclosure.disclosure_code, score["status"])["recommendations"]:
                ImprovementRecommendation.objects.create(
                    analysis_result=result,
                    disclosure_code=disclosure.disclosure_code,
                    title=item["title"],
                    recommendation=item["recommendation"],
                    term=item["term"],
                    priority=item["priority"],
                )

    result.total_score = total_score
    result.confidence_score = sum(confidence_values, Decimal("0")) / len(confidence_values) if confidence_values else 0
    result.raw_output = {
        "schema": {
            "disclosure_code": "305-1",
            "status": "complete | partial | missing",
            "raw_score": 0,
            "weighted_score": 0,
            "confidence": 0.0,
            "summary": "",
            "evidence": [{"page_number": 42, "quoted_text": "", "finding": "", "evidence_type": "text"}],
            "missing_items": [],
            "recommendations": [],
        }
    }
    result.save(update_fields=["total_score", "confidence_score", "raw_output", "updated_at"])
    return result
