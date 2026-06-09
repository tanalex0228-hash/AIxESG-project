import json

from django.conf import settings

from analysis.models import AIUsageLog, IndustryMetricSnapshot
from analysis.services.industry_metrics import confidence_level, industry_detail_context
from reports.models import Report


def build_management_feedback(result):
    conclusion = result.raw_output.get("dynamic_conclusion", {})
    benchmark = result.raw_output.get("benchmark_comparison", {})
    metric = IndustryMetricSnapshot.objects.filter(analysis_result=result).select_related("industry").first()
    industry_context = _industry_context_for(result, metric)
    missing_items = [
        {"gri": item.disclosure_code, "item": item.item_name, "severity": item.severity}
        for item in result.missing_items.order_by("priority", "disclosure_code")[:12]
    ]
    payload = {
        "company": result.report.company_name,
        "year": result.report.report_year,
        "raw_score": str(result.total_score),
        "total_score": str(result.total_score),
        "relative_performance": _metric_payload(metric),
        "industry": industry_context,
        "conclusion": conclusion,
        "benchmark": benchmark,
        "missing_items": missing_items,
    }
    if settings.OPENAI_API_KEY:
        llm_output = _openai_feedback(result, payload)
        if llm_output:
            return llm_output
    return _fallback_feedback(payload)


def _openai_feedback(result, payload):
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = (
            "你是企業碳揭露與 GRI 305 顧問。根據輸入 JSON 產出繁體中文管理層評論，"
            "評論必須基於 raw_score、PR、grade、z_score、industry sample、industry averages、top missing items 與同業比較。"
            "必須只回 JSON，包含 overall_rating、confidence_level、benchmark_sample、executive_summary、"
            "benchmark_commentary、action_plan、industry_insight、key_risks、improvement_advice、next_90_days。"
            "action_plan 必須包含 short_term、medium_term、long_term 三個陣列。不得捏造未提供的數字。"
        )
        response = client.chat.completions.create(
            model=settings.OPENAI_ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        AIUsageLog.objects.create(
            report=result.report,
            analysis_result=result,
            provider="openai",
            model=settings.OPENAI_ANALYSIS_MODEL,
            operation="management_feedback",
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
            total_tokens=getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            metadata={"mode": "llm"},
        )
        parsed = json.loads(content)
        parsed = _normalize_feedback(parsed, payload)
        parsed["source"] = "openai"
        return parsed
    except Exception as exc:
        AIUsageLog.objects.create(
            report=result.report,
            analysis_result=result,
            provider="local",
            model="fallback",
            operation="management_feedback",
            metadata={"mode": "fallback_after_error", "error": str(exc)[:300]},
        )
        return None


def _fallback_feedback(payload):
    rating = _rating_for_score(float(payload["total_score"]))
    relative = payload.get("relative_performance", {})
    industry = payload.get("industry", {})
    confidence = industry.get("confidence_level") or confidence_level(int(industry.get("company_count") or 0))
    sample = industry.get("company_count") or relative.get("benchmark_sample_size") or 0
    pr = relative.get("percentile_rank") or "-"
    grade = relative.get("grade") or rating
    z_score = relative.get("z_score") or "-"
    if rating == "A":
        summary = "揭露品質接近標竿，後續應強化一致性與第三方佐證。"
    elif rating == "B":
        summary = "揭露基礎良好，但仍有會影響評級的資料缺口。"
    elif rating == "C":
        summary = "已具備部分核心揭露，需要優先補齊方法、來源與 Scope 3 類別。"
    else:
        summary = "揭露完整度不足，短期需先建立可稽核的碳資料盤點流程。"
    missing = payload.get("missing_items", [])
    risks = [f"{item['gri']} 缺少 {item['item']}" for item in missing[:4]]
    benchmark_missing = payload.get("benchmark", {}).get("missing_categories", [])[:4]
    top_missing = industry.get("top_missing_items", [])[:4]
    advice = [
        "建立 GRI 305 欄位責任表，逐項補齊數值、年度、方法學與來源。",
        "將 Scope 1、Scope 2、Scope 3 資料來源與排放係數版本納入內控流程。",
        "把同業標竿缺口轉成季度改善計畫，優先處理高嚴重度缺漏。",
    ]
    if benchmark_missing:
        advice.append("優先補強 Scope 3 類別：" + "、".join(benchmark_missing) + "。")
    return {
        "source": "rule_engine_fallback",
        "overall_rating": grade,
        "confidence_level": confidence,
        "benchmark_sample": sample,
        "executive_summary": f"{payload['company']} 在同產業 PR 為 {pr}，Grade 為 {grade}，Z-score 為 {z_score}。{summary}",
        "executive_feedback": f"{payload['company']} 在同產業 PR 為 {pr}，Grade 為 {grade}，Z-score 為 {z_score}。{summary}",
        "benchmark_commentary": _benchmark_commentary(payload, top_missing),
        "industry_insight": _industry_insight(industry),
        "key_risks": risks or ["目前未偵測到高嚴重度缺漏，但仍建議維持年度更新與佐證留存。"],
        "improvement_advice": advice,
        "action_plan": {
            "short_term": ["確認各 GRI 305 欄位資料 owner。", "補齊缺漏欄位與引用來源。"],
            "medium_term": ["用產業標竿格式重整 GRI 305 揭露章節。", "建立 Scope 3 類別資料蒐集流程。"],
            "long_term": ["將排放數據、排放係數版本與內部覆核流程制度化。"],
        },
        "next_90_days": [
            "確認各 GRI 305 欄位資料 owner。",
            "補齊缺漏欄位與引用來源。",
            "用標竿公司格式重整揭露章節。",
        ],
    }


def _rating_for_score(score):
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _normalize_feedback(feedback, payload):
    normalized = dict(feedback)
    score_rating = payload.get("relative_performance", {}).get("grade") or _rating_for_score(float(payload["total_score"]))
    rating = str(normalized.get("overall_rating", "")).strip().upper()
    if rating not in {"A+", "A", "B", "C", "D"}:
        if rating:
            normalized["executive_feedback"] = normalized.get("executive_feedback") or normalized.get("summary") or rating
        normalized["overall_rating"] = score_rating
    for key in ["key_risks", "improvement_advice", "next_90_days"]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [value]
        elif not isinstance(value, list):
            normalized[key] = []
    action_plan = normalized.get("action_plan")
    if not isinstance(action_plan, dict):
        action_plan = {}
    for key in ["short_term", "medium_term", "long_term"]:
        value = action_plan.get(key)
        if isinstance(value, str):
            action_plan[key] = [value]
        elif not isinstance(value, list):
            action_plan[key] = []
    normalized["action_plan"] = action_plan
    normalized["confidence_level"] = normalized.get("confidence_level") or payload.get("industry", {}).get("confidence_level") or "Low"
    normalized["benchmark_sample"] = normalized.get("benchmark_sample") or payload.get("industry", {}).get("company_count") or 0
    normalized["executive_summary"] = normalized.get("executive_summary") or normalized.get("executive_feedback") or _fallback_feedback(payload)["executive_summary"]
    normalized["executive_feedback"] = normalized.get("executive_feedback") or _fallback_feedback(payload)["executive_feedback"]
    normalized["benchmark_commentary"] = normalized.get("benchmark_commentary") or _fallback_feedback(payload)["benchmark_commentary"]
    normalized["industry_insight"] = normalized.get("industry_insight") or _fallback_feedback(payload)["industry_insight"]
    return normalized


def _metric_payload(metric):
    if not metric:
        return {}
    return {
        "industry_code": metric.industry.code,
        "industry_name": metric.industry.name_zh,
        "raw_score": str(metric.raw_score),
        "percentile_rank": str(metric.percentile_rank),
        "grade": metric.grade,
        "z_score": str(metric.z_score),
        "disclosure_rate": str(metric.disclosure_rate),
        "missing_count": metric.missing_count,
        "benchmark_sample_size": metric.benchmark_sample_size,
    }


def _industry_context_for(result, metric):
    if not metric:
        return {}
    accessible_reports = Report.objects.filter(status="completed", latest_analysis_result__isnull=False)
    context = industry_detail_context(metric.industry, accessible_reports)
    return {
        "industry_code": metric.industry.code,
        "industry_name": metric.industry.name_zh,
        "company_count": context["company_count"],
        "report_count": context["report_count"],
        "average_raw_score": str(context["average_raw_score"]),
        "average_pr": str(context["average_pr"]),
        "average_disclosure_rate": str(context["average_disclosure_rate"]),
        "average_missing_count": str(context["average_missing_count"]),
        "confidence_level": context["confidence_level"],
        "top_missing_items": context["top_missing_items"][:5],
        "leaders": [
            {"company": item.report.company_name, "raw_score": str(item.raw_score), "pr": str(item.percentile_rank), "grade": item.grade}
            for item in context["best_performers"][:5]
        ],
    }


def _benchmark_commentary(payload, top_missing):
    industry = payload.get("industry", {})
    relative = payload.get("relative_performance", {})
    if not industry:
        return "目前缺少同產業樣本，建議先累積更多可比較報告後再解讀相對表現。"
    missing_text = "、".join(item["label"] for item in top_missing) if top_missing else "目前未形成明顯共同缺漏"
    return (
        f"本公司 Raw Score 為 {relative.get('raw_score', payload['total_score'])}，"
        f"產業平均 Raw Score 為 {industry.get('average_raw_score', '-')}；"
        f"PR 為 {relative.get('percentile_rank', '-')}，樣本公司數為 {industry.get('company_count', 0)}。"
        f"同產業常見缺漏包含：{missing_text}。"
    )


def _industry_insight(industry):
    if not industry:
        return "目前尚無足夠產業資料可形成趨勢洞察。"
    missing = industry.get("top_missing_items", [])[:3]
    missing_text = "、".join(f"{item['label']}（{item['ratio']}%）" for item in missing) if missing else "尚無集中缺漏"
    return (
        f"本系統目前分析 {industry.get('company_count', 0)} 家{industry.get('industry_name', '')}企業，"
        f"平均揭露率為 {industry.get('average_disclosure_rate', '-')}%，"
        f"主要缺口為 {missing_text}。"
    )
