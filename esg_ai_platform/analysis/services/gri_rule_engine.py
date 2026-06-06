import re
from decimal import Decimal

from django.db import transaction

from analysis.models import (
    AnalysisResult,
    DisclosureScore,
    EvidenceCitation,
    ImprovementRecommendation,
    MissingItem,
)
from benchmarks.models import BenchmarkGoldStandard, BenchmarkGri305
from gri.models import GRIRequiredField, GRIScoringWeight

from .gri_knowledge import CATEGORY_KEYWORDS, SCOPE3_CATEGORIES
from .knowledge_base_importer import seed_gri_rule_tables
from .llm_feedback import build_management_feedback

SCORE_CODES = ["305-1", "305-2", "305-3", "305-4", "305-5"]


def _report_chunks(report):
    return list(report.chunks.order_by("page_start", "id"))


def _match_keywords(text, keywords):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def _numeric_signal(text):
    return bool(re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:tco2e|公噸|噸|%)?", text, re.IGNORECASE))


def _find_field_evidence(chunks, required_field):
    keywords = required_field.keywords or [required_field.field_label]
    for chunk in chunks:
        if _match_keywords(chunk.chunk_text, keywords):
            if required_field.field_key in {"S1_Total_Emissions", "Location_Based", "Market_Based", "Total_Emissions"}:
                if not _numeric_signal(chunk.chunk_text):
                    continue
            return {
                "chunk": chunk,
                "quoted_text": chunk.chunk_text[:800],
                "confidence": Decimal("0.88") if _numeric_signal(chunk.chunk_text) else Decimal("0.72"),
            }
    return None


def _detected_scope3_categories(chunks):
    full_text = "\n".join(chunk.chunk_text for chunk in chunks)
    detected = []
    for category in SCOPE3_CATEGORIES:
        if _match_keywords(full_text, CATEGORY_KEYWORDS[category]):
            detected.append(category)
    return detected


def _benchmark_scope3_categories():
    categories_by_company = {}
    rows = BenchmarkGri305.objects.filter(field_key="S3_Categories_Breakdown").select_related("company")
    for row in rows:
        detected = []
        for category in SCOPE3_CATEGORIES:
            matched_keyword = next((keyword for keyword in CATEGORY_KEYWORDS[category] if keyword.lower() in row.value.lower()), "")
            if matched_keyword and "未揭露" not in _slice_around(row.value, matched_keyword):
                detected.append(category)
        categories_by_company[row.company.name] = detected
    return categories_by_company


def _slice_around(text, keyword):
    index = text.lower().find(keyword.lower())
    if index == -1:
        return ""
    return text[max(0, index - 30) : index + len(keyword) + 80]


def _gold_standard_for(disclosure_code):
    standards = BenchmarkGoldStandard.objects.filter(disclosure_code=disclosure_code).select_related("company")
    return [
        {
            "company": standard.company.name,
            "standard_id": standard.standard_id,
            "target_indicator": standard.target_indicator,
            "excellent_reason": standard.excellent_reason,
            "action_plan_template": standard.action_plan_template,
        }
        for standard in standards
    ]


def _recommendation_for_missing(missing_item, disclosure_code):
    standards = _gold_standard_for(disclosure_code)
    if standards:
        standard = standards[0]
        return (
            f"參考 {standard['company']} 的優秀揭露做法：{standard['excellent_reason']} "
            f"建議行動：{standard['action_plan_template']}"
        )
    return f"請補充 {missing_item.field_label}，包含數值、年度、方法、來源與管理責任。"


def _status(earned, max_score):
    if earned == 0:
        return "missing"
    if earned < max_score:
        return "partial"
    return "complete"


def _build_benchmark_comparison(report, detected_categories):
    benchmark_categories = _benchmark_scope3_categories()
    best_company = ""
    best_categories = []
    for company, categories in benchmark_categories.items():
        if len(categories) > len(best_categories):
            best_company = company
            best_categories = categories
    missing = [category for category in best_categories if category not in detected_categories]
    comparison_text = (
        f"{report.company_name} 範疇三揭露 {len(detected_categories)} 個類別；"
        f"同業標竿 {best_company or '標竿企業'} 揭露 {len(best_categories)} 個類別。"
    )
    if missing:
        comparison_text += " 目前範疇三揭露完整度低於同業標竿，缺少：" + "、".join(missing[:8]) + "。"
    return {
        "detected_scope3_categories": detected_categories,
        "benchmark_scope3_categories": benchmark_categories,
        "best_company": best_company,
        "missing_categories": missing,
        "summary": comparison_text,
    }


def _dynamic_conclusion(total_score, missing_items, benchmark_comparison, recommendations):
    high_missing = [item.item_name for item in missing_items if item.severity == "high"]
    benchmark_gap = benchmark_comparison.get("missing_categories", [])
    if total_score >= Decimal("85"):
        score_observation = "揭露架構已接近標竿水準，後續重點是提高方法與來源的一致性。"
    elif total_score >= Decimal("60"):
        score_observation = "揭露已有基礎，但仍存在會影響評級可信度的資料缺口。"
    else:
        score_observation = "目前揭露完整度偏低，需優先補齊核心量化資料與計算來源。"
    return {
        "executive_summary": f"本次 GRI 305 規則引擎評分為 {total_score}/100。{score_observation}",
        "strategic_observation": benchmark_comparison["summary"],
        "improvement_priority": high_missing[:5] or benchmark_gap[:5] or ["維持現有揭露並強化第三方佐證"],
        "future_risk": "若 Scope 3 類別、GWP 來源或基準年資訊不足，未來面對供應鏈查核與金融機構 ESG 評等時會提高補件與降評風險。",
        "management_recommendation": [item.recommendation for item in recommendations[:5]],
    }


@transaction.atomic
def run_rule_engine_analysis(report):
    seed_gri_rule_tables()
    result, _ = AnalysisResult.objects.update_or_create(
        report=report,
        defaults={
            "summary": "GRI 305 規則引擎、標竿比較與改善建議已完成。",
            "model_name": "gri-rule-engine-v1",
        },
    )
    result.disclosure_scores.all().delete()
    result.missing_items.all().delete()
    result.evidence_citations.all().delete()
    result.recommendations.all().delete()

    chunks = _report_chunks(report)
    total_score = Decimal("0")
    confidence_values = []
    score_payload = []

    for disclosure_code in SCORE_CODES:
        weights = list(GRIScoringWeight.objects.filter(disclosure_code=disclosure_code, is_active=True))
        required_fields = {
            field.field_key: field
            for field in GRIRequiredField.objects.filter(disclosure_code=disclosure_code, is_active=True, is_required=True)
        }
        earned = Decimal("0")
        max_score = sum((weight.max_score for weight in weights), Decimal("0"))
        field_results = []
        disclosure_evidence = []

        for weight in weights:
            required_field = required_fields.get(weight.field_key)
            evidence = _find_field_evidence(chunks, required_field) if required_field else None
            field_score = weight.max_score if evidence else Decimal("0")
            earned += field_score
            field_result = {
                "field_key": weight.field_key,
                "field_label": weight.field_label,
                "max_score": float(weight.max_score),
                "score": float(field_score),
                "status": "complete" if evidence else "missing",
            }
            field_results.append(field_result)
            if evidence:
                disclosure_evidence.append((weight, evidence))

        status = _status(earned, max_score)
        disclosure_score = DisclosureScore.objects.create(
            analysis_result=result,
            disclosure_code=disclosure_code,
            status=status,
            raw_score=earned,
            weighted_score=earned,
            weight_percent=max_score,
            confidence=Decimal("0.9") if status == "complete" else Decimal("0.62") if status == "partial" else Decimal("0.35"),
            summary=f"{disclosure_code} 得分 {earned}/{max_score}，由規則權重表計算。",
            agent_output={"field_results": field_results},
        )
        total_score += earned
        confidence_values.append(disclosure_score.confidence)

        for weight, evidence in disclosure_evidence:
            chunk = evidence["chunk"]
            EvidenceCitation.objects.create(
                analysis_result=result,
                disclosure_score=disclosure_score,
                report=report,
                disclosure_code=disclosure_code,
                page_number=chunk.page_start,
                quoted_text=evidence["quoted_text"],
                normalized_finding=f"{weight.field_label} 已找到揭露證據。",
                confidence_score=evidence["confidence"],
                source_chunk=chunk,
                start_char=0,
                end_char=len(evidence["quoted_text"]),
                evidence_type=chunk.chunk_type,
            )

        for field in required_fields.values():
            matching_weight = next((weight for weight in weights if weight.field_key == field.field_key), None)
            if matching_weight and any(item["field_key"] == field.field_key and item["status"] == "complete" for item in field_results):
                continue
            missing_item = MissingItem.objects.create(
                analysis_result=result,
                disclosure_score=disclosure_score,
                disclosure_code=disclosure_code,
                item_name=field.field_label,
                description=field.recommendation_template,
                severity=field.severity,
                priority=field.sort_order,
            )
            recommendation = _recommendation_for_missing(field, disclosure_code)
            ImprovementRecommendation.objects.create(
                analysis_result=result,
                disclosure_code=disclosure_code,
                title=f"補強 {disclosure_code}：{field.field_label}",
                recommendation=recommendation,
                term="short" if field.severity == "high" else "medium",
                priority=field.sort_order,
            )
            missing_item.description = recommendation
            missing_item.save(update_fields=["description"])

        score_payload.append(
            {
                "disclosure_code": disclosure_code,
                "score": float(earned),
                "max_score": float(max_score),
                "status": status,
                "fields": field_results,
            }
        )

    detected_categories = _detected_scope3_categories(chunks)
    benchmark_comparison = _build_benchmark_comparison(report, detected_categories)
    recommendations = list(result.recommendations.order_by("priority", "term"))
    missing_items = list(result.missing_items.order_by("priority", "disclosure_code"))
    conclusion = _dynamic_conclusion(total_score, missing_items, benchmark_comparison, recommendations)
    result.total_score = total_score
    result.confidence_score = sum(confidence_values, Decimal("0")) / len(confidence_values) if confidence_values else Decimal("0")
    result.summary = conclusion["executive_summary"]
    result.raw_output = {
        "score_source": "rule_engine",
        "scores": score_payload,
        "benchmark_comparison": benchmark_comparison,
        "gold_standard_recommendations": {
            code: _gold_standard_for(code)
            for code in SCORE_CODES
        },
        "dynamic_conclusion": conclusion,
    }
    result.save(update_fields=["total_score", "confidence_score", "summary", "raw_output", "updated_at"])
    result.raw_output["llm_management_feedback"] = build_management_feedback(result)
    result.save(update_fields=["raw_output", "updated_at"])
    return result
