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
DISCLOSURE_ANCHORS = {
    "305-1": ["305-1", "scope 1", "範疇一", "直接溫室氣體", "直接排放"],
    "305-2": ["305-2", "scope 2", "範疇二", "能源間接", "外購電力"],
    "305-3": ["305-3", "scope 3", "範疇三", "其他間接", "價值鏈"],
    "305-4": ["305-4", "密集度", "intensity"],
    "305-5": ["305-5", "減量", "reduction", "減少"],
}
FIELD_KEYWORD_OVERRIDES = {
    "Location_Based": ["location-based", "location based", "地點基礎", "地域基礎", "所在地基礎"],
    "Market_Based": ["market-based", "market based", "市場基礎", "綠電", "再生能源憑證"],
    "S1_Biogenic_Emissions": ["生質 co2", "生質二氧化碳", "生質燃料", "biogenic"],
    "Carbon_Offsets": ["碳抵換", "碳權", "抵換", "offset", "carbon credit", "未使用碳權", "未使用抵換"],
    "GWP": ["gwp", "全球暖化潛勢", "ipcc", "ar5", "ar6"],
    "S1_GWP_Source": ["gwp", "全球暖化潛勢", "ipcc", "ar5", "ar6"],
}
FIELD_RECOMMENDATIONS = {
    "Location_Based": "請補充 Scope 2 地點基礎排放量，列出用電量、電網排放係數、年度與係數來源。這能讓投資人看出公司所在地電力結構造成的真實碳風險，也能和同業用一致基準比較。",
    "Market_Based": "請補充 Scope 2 市場基礎排放量，說明綠電、再生能源憑證或供電合約如何影響排放量。這能呈現企業採購低碳電力的實際管理成效，避免只揭露 location-based 而低估能源轉型策略。",
    "S1_Biogenic_Emissions": "請補充生質 CO2 排放量，即使數值為 0 也應明確揭露。這能避免外部審查時誤判報告漏列生質燃料或生質來源排放，提升盤查完整性。",
    "GWP": "請補充 GWP 來源，例如 IPCC AR5 或 AR6，並說明各溫室氣體換算為 CO2e 的版本。這能提高不同年度與同業比較的一致性，降低查證時被要求補件的風險。",
    "S1_GWP_Source": "請補充 Scope 1 使用的 GWP 來源，例如 IPCC AR5 或 AR6。這能讓 CO2e 換算依據可追溯，避免不同氣體加總缺乏共同基準。",
    "Carbon_Offsets": "請說明是否使用碳權、抵換、憑證或其他 offset；若未使用，也應明確寫出未納入抵換。這能讓減量成果與抵換行為分開呈現，避免管理績效被質疑。",
    "S1_Base_Year_Emissions": "請補充基準年排放量與選定理由，並說明組織邊界或方法變更時是否重算。這能讓減量趨勢可驗證，而不是只有單年度排放數字。",
    "Base_Year": "請補充該範疇的基準年、選定理由與是否重算。這能讓後續減量成果有比較基準，避免改善幅度缺乏可信參照。",
    "Categories_Breakdown": "請把 Scope 3 依 15 類別拆分，至少標示適用、不適用、未盤查或數值為 0。這能讓供應鏈與產品使用階段的重大排放熱點被看見，也能明確規劃下一年度盤查優先序。",
    "Emission_Factor": "請補充排放係數名稱、版本、來源與適用活動資料。這能讓數值可被第三方重算與追蹤，降低模型或人工估算被質疑的風險。",
    "Methodology": "請補充計算方法、假設、工具與採用標準，例如 ISO 14064-1 或 GHG Protocol。這能提升報告可稽核性，也方便跨年度維持一致算法。",
    "Reduction_Method": "請補充每項減量措施如何造成減排，例如設備汰換、製程改善、綠電採購或能效提升。這能把減量成果從口號變成可追蹤的管理行動。",
}


def _report_chunks(report):
    return list(report.chunks.order_by("page_start", "id"))


def _match_keywords(text, keywords):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)


def _numeric_signal(text):
    return bool(re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:tco2e|公噸|噸|%)?", text, re.IGNORECASE))


def _detected_value(text):
    match = re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:tco2e|公噸|噸|%)?", text, re.IGNORECASE)
    return match.group(0) if match else ""


def _scoped_chunks(chunks, disclosure_code):
    anchors = DISCLOSURE_ANCHORS[disclosure_code]
    scoped = []
    for chunk in chunks:
        text = chunk.chunk_text
        lowered = text.lower()
        indexes = [lowered.find(anchor.lower()) for anchor in anchors if anchor.lower() in lowered]
        if not indexes:
            continue
        start = max(0, min(indexes) - 450)
        end = min(len(text), min(indexes) + 1800)
        scoped.append((chunk, text[start:end]))
    return scoped or [(chunk, chunk.chunk_text) for chunk in chunks]


def _field_keywords(required_field):
    return FIELD_KEYWORD_OVERRIDES.get(required_field.field_key, required_field.keywords or [required_field.field_label])


def _find_field_evidence(scoped_chunks, required_field):
    keywords = _field_keywords(required_field)
    for chunk, scoped_text in scoped_chunks:
        if _match_keywords(scoped_text, keywords):
            if required_field.field_key in {"S1_Total_Emissions", "Location_Based", "Market_Based", "Total_Emissions"}:
                if not _numeric_signal(scoped_text):
                    continue
            return {
                "chunk": chunk,
                "quoted_text": scoped_text[:800],
                "confidence": Decimal("0.88") if _numeric_signal(scoped_text) else Decimal("0.72"),
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
    if missing_item.field_key in FIELD_RECOMMENDATIONS:
        return FIELD_RECOMMENDATIONS[missing_item.field_key]
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
def run_rule_engine_analysis(report, analysis_job=None):
    seed_gri_rule_tables()
    AnalysisResult.objects.filter(report=report, is_latest=True).update(is_latest=False)
    version_number = (AnalysisResult.objects.filter(report=report).order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1
    result = AnalysisResult.objects.create(
        report=report,
        analysis_job=analysis_job,
        version_number=version_number,
        is_latest=True,
        summary="GRI 305 規則引擎、標竿比較與改善建議已完成。",
        model_name="gri-rule-engine-v1",
    )

    chunks = _report_chunks(report)
    total_score = Decimal("0")
    confidence_values = []
    score_payload = []

    for disclosure_code in SCORE_CODES:
        scoped_chunks = _scoped_chunks(chunks, disclosure_code)
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
            evidence = _find_field_evidence(scoped_chunks, required_field) if required_field else None
            field_score = weight.max_score if evidence else Decimal("0")
            earned += field_score
            field_result = {
                "field_key": weight.field_key,
                "field_label": weight.field_label,
                "max_score": float(weight.max_score),
                "score": float(field_score),
                "status": "complete" if evidence else "missing",
                "detected_value": _detected_value(evidence["quoted_text"]) if evidence else "",
                "page_number": evidence["chunk"].page_start if evidence else None,
                "evidence_excerpt": evidence["quoted_text"][:240] if evidence else "",
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
    report.latest_analysis_result = result
    report.save(update_fields=["latest_analysis_result", "updated_at"])
    return result
