import json

from django.conf import settings

from analysis.models import AIUsageLog


def build_management_feedback(result):
    conclusion = result.raw_output.get("dynamic_conclusion", {})
    benchmark = result.raw_output.get("benchmark_comparison", {})
    missing_items = [
        {"gri": item.disclosure_code, "item": item.item_name, "severity": item.severity}
        for item in result.missing_items.order_by("priority", "disclosure_code")[:12]
    ]
    payload = {
        "company": result.report.company_name,
        "year": result.report.report_year,
        "total_score": str(result.total_score),
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
            "你是企業 ESG 顧問。根據輸入 JSON，產出繁體中文管理層回饋。"
            "必須包含 overall_rating、key_risks、improvement_advice、next_90_days，"
            "不得捏造未提供的數字。請只回 JSON。"
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
    advice = [
        "建立 GRI 305 欄位責任表，逐項補齊數值、年度、方法學與來源。",
        "將 Scope 1、Scope 2、Scope 3 資料來源與排放係數版本納入內控流程。",
        "把同業標竿缺口轉成季度改善計畫，優先處理高嚴重度缺漏。",
    ]
    if benchmark_missing:
        advice.append("優先補強 Scope 3 類別：" + "、".join(benchmark_missing) + "。")
    return {
        "source": "rule_engine_fallback",
        "overall_rating": rating,
        "executive_feedback": summary,
        "key_risks": risks or ["目前未偵測到高嚴重度缺漏，但仍建議維持年度更新與佐證留存。"],
        "improvement_advice": advice,
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
    score_rating = _rating_for_score(float(payload["total_score"]))
    rating = str(normalized.get("overall_rating", "")).strip().upper()
    if rating not in {"A", "B", "C", "D"}:
        if rating:
            normalized["executive_feedback"] = normalized.get("executive_feedback") or normalized.get("summary") or rating
        normalized["overall_rating"] = score_rating
    for key in ["key_risks", "improvement_advice", "next_90_days"]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [value]
        elif not isinstance(value, list):
            normalized[key] = []
    normalized["executive_feedback"] = normalized.get("executive_feedback") or _fallback_feedback(payload)["executive_feedback"]
    return normalized
