import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from django.conf import settings
from django.db import transaction

from benchmarks.models import BenchmarkCompany, BenchmarkGoldStandard, BenchmarkGri305, IndustryCategory
from gri.models import GRIDisclosureRule, GRIRequiredField, GRIScoringWeight
from rag.models import Embedding, VectorChunk, VectorDocument
from rag.services import embedding_for_text

from .gri305_excel_reference import SCORING_ITEMS, SECTION_WEIGHTS

KNOWLEDGE_BASE_DIR = Path(settings.BASE_DIR) / "knowledge_base"
FIELD_LINE_RE = re.compile(r"^\s*\*\s+\*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*)$")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
SOURCE_RE = re.compile(r"\[(來源:[^\]]+|source:[^\]]+)\]", re.IGNORECASE)
UNIT_RE = re.compile(r"(?:單位|unit)[:：]\s*([^）)\];，,]+)", re.IGNORECASE)


def _clean_value(value):
    return value.strip().strip(";").strip()


def _code_value(value):
    match = INLINE_CODE_RE.search(value)
    return _clean_value(match.group(1) if match else value)


def _numeric_value(value):
    cleaned = _code_value(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def _source(value):
    match = SOURCE_RE.search(value)
    return match.group(1) if match else ""


def _unit(value):
    match = UNIT_RE.search(value)
    return match.group(1).strip() if match else ""


def _disclosure_for_key(field_key):
    if field_key.startswith("S1_"):
        return "305-1"
    if field_key.startswith("S2_") or field_key in {"Location_Based", "Market_Based"}:
        return "305-2"
    if field_key.startswith("S3_") or field_key in {"Total_Emissions", "Categories_Breakdown"}:
        return "305-3"
    if field_key.startswith("Intensity_"):
        return "305-4"
    if field_key.startswith("Reduction_") or field_key.startswith("Carbon_"):
        return "305-5"
    return ""


def _indicator_for_key(field_key):
    disclosure = _disclosure_for_key(field_key)
    return f"GRI_{disclosure.replace('-', '_')}" if disclosure else field_key


def _markdown_fields(body):
    fields = {}
    lines = body.splitlines()
    for index, line in enumerate(lines):
        match = FIELD_LINE_RE.match(line)
        if not match:
            continue
        key = match.group("key").strip()
        value = match.group("value").strip()
        if value in {"", "{"}:
            block = []
            for next_line in lines[index + 1 :]:
                if FIELD_LINE_RE.match(next_line):
                    break
                if next_line.strip().startswith("## "):
                    break
                block.append(next_line)
                if next_line.strip() == "}":
                    break
            value = "\n".join(block).strip()
        fields[key] = value
    return fields


def _chunk_markdown(body, max_chars=1800):
    current_title = ""
    buffer = []
    buffer_size = 0
    for line in body.splitlines():
        if line.startswith("#"):
            if buffer:
                yield current_title, "\n".join(buffer).strip()
                buffer = []
                buffer_size = 0
            current_title = line.lstrip("#").strip()
        buffer.append(line)
        buffer_size += len(line)
        if buffer_size >= max_chars:
            yield current_title, "\n".join(buffer).strip()
            buffer = []
            buffer_size = 0
    if buffer:
        yield current_title, "\n".join(buffer).strip()


def seed_gri_rule_tables():
    active_pairs = {(item["disclosure_code"], item["field_key"]) for item in SCORING_ITEMS}
    for section in SECTION_WEIGHTS:
        disclosure_code = "MGT" if section["section"] == "管理與報導基礎" else section["section"].split()[0]
        GRIDisclosureRule.objects.update_or_create(
            disclosure_code=disclosure_code,
            version="GRI 305:2016",
            defaults={
                "rule_name": section["section"],
                "description": section["reason"],
                "official_requirement": section["reason"],
                "source_document": "ESGxAI_GRI305評分標準與公司分類.xlsx",
                "is_active": True,
            },
        )

    sort_by_disclosure = {}
    for item in SCORING_ITEMS:
        disclosure_code = cast(str, item["disclosure_code"])
        field_key = cast(str, item["field_key"])
        sort_by_disclosure[disclosure_code] = sort_by_disclosure.get(disclosure_code, 0) + 1
        sort_order = sort_by_disclosure[disclosure_code]
        GRIScoringWeight.objects.update_or_create(
            disclosure_code=disclosure_code,
            field_key=field_key,
            defaults={
                "field_label": item["field_label"],
                "max_score": Decimal(cast(str, item["max_score"])),
                "sort_order": sort_order,
                "is_active": True,
            },
        )
        GRIRequiredField.objects.update_or_create(
            disclosure_code=disclosure_code,
            field_key=field_key,
            defaults={
                "field_label": item["field_label"],
                "source_clause": item["source_clause"],
                "requirement_type": item["requirement_type"],
                "keywords": item["keywords"],
                "patterns": [],
                "recommendation_template": item["weight_reason"],
                "severity": "high" if item["is_critical"] else "medium",
                "is_critical": item["is_critical"],
                "is_required": True,
                "sort_order": sort_order,
                "is_active": True,
            },
        )

    for scoring_weight in GRIScoringWeight.objects.all():
        if (scoring_weight.disclosure_code, scoring_weight.field_key) not in active_pairs:
            scoring_weight.is_active = False
            scoring_weight.save(update_fields=["is_active"])
    for required_field in GRIRequiredField.objects.all():
        if (required_field.disclosure_code, required_field.field_key) not in active_pairs:
            required_field.is_active = False
            required_field.save(update_fields=["is_active"])


def import_benchmark_markdown(path):
    body = path.read_text(encoding="utf-8")
    fields = _markdown_fields(body)
    company_id = _code_value(fields.get("Company_ID", path.stem))
    company_name = _code_value(fields.get("Company_Name", path.stem))
    stock_code = _code_value(fields.get("Stock_Code", ""))
    report_year = int(_numeric_value(fields.get("Report_Year", "2024")) or 2024)
    industry_name = _code_value(fields.get("Industry", "ESG Benchmark"))
    industry, _ = IndustryCategory.objects.get_or_create(name=industry_name)
    company, _ = BenchmarkCompany.objects.update_or_create(
        company_id=company_id,
        defaults={
            "name": company_name,
            "industry": industry,
            "stock_code": stock_code,
            "notes": f"Imported from {path.name}",
            "is_active": True,
        },
    )

    gold_fields = {
        "standard_id": _code_value(fields.get("Standard_ID", "")),
        "target_indicator": _code_value(fields.get("Target_Indicator", "")),
        "system_score_tag": _code_value(fields.get("System_Score_Tag", "")),
        "gold_standard_text": _code_value(fields.get("Gold_Standard_Text", "")),
        "excellent_reason": _code_value(fields.get("Excellent_Reason", "")),
        "action_plan_template": _code_value(fields.get("Action_Plan_Template", "")),
    }

    for field_key, raw_value in fields.items():
        if field_key in {
            "Company_ID",
            "Company_Name",
            "Stock_Code",
            "Industry",
            "Report_Year",
            "Report_Pages",
            "Third_Party_Verified",
            "Verification_Standard",
            "Standard_ID",
            "Target_Indicator",
            "System_Score_Tag",
            "Gold_Standard_Text",
            "Excellent_Reason",
            "Action_Plan_Template",
        }:
            continue
        disclosure_code = _disclosure_for_key(field_key)
        if not disclosure_code:
            continue
        BenchmarkGri305.objects.update_or_create(
            company=company,
            year=report_year,
            field_key=field_key,
            defaults={
                "disclosure_code": disclosure_code,
                "indicator": _indicator_for_key(field_key),
                "value": _code_value(raw_value),
                "numeric_value": _numeric_value(raw_value),
                "unit": _unit(raw_value),
                "source": _source(raw_value) or path.name,
                "reason": gold_fields["excellent_reason"] if field_key == gold_fields["target_indicator"] else "",
                "action_template": gold_fields["action_plan_template"] if field_key == gold_fields["target_indicator"] else "",
                "metadata": {"company_id": company_id, "source_file": path.name},
            },
        )

    if gold_fields["standard_id"]:
        BenchmarkGoldStandard.objects.update_or_create(
            company=company,
            standard_id=gold_fields["standard_id"],
            defaults={
                "target_indicator": gold_fields["target_indicator"],
                "disclosure_code": _disclosure_for_key(gold_fields["target_indicator"]) or "305-3",
                "system_score_tag": gold_fields["system_score_tag"],
                "gold_standard_text": gold_fields["gold_standard_text"],
                "excellent_reason": gold_fields["excellent_reason"],
                "action_plan_template": gold_fields["action_plan_template"],
            },
        )
    return company


def import_markdown_to_rag(path):
    body = path.read_text(encoding="utf-8")
    source_type = "gri" if path.name == "Database_Rules.md" else "benchmark"
    document, _ = VectorDocument.objects.update_or_create(
        source_type=source_type,
        source_id=path.name,
        defaults={
            "title": path.stem,
            "metadata": {
                "source_type": source_type,
                "company": _company_from_path(path),
                "indicator": "GRI 305",
                "gri_code": "305",
                "year": 2024 if source_type == "benchmark" else 2016,
                "source_file": path.name,
            },
        },
    )
    document.chunks.all().delete()
    created = 0
    for index, (section_title, chunk_text) in enumerate(_chunk_markdown(body), start=1):
        if not chunk_text:
            continue
        vector_chunk = VectorChunk.objects.create(
            document=document,
            chunk_text=chunk_text,
            page_number=index,
            section_title=section_title,
            metadata={
                "source_type": source_type,
                "company": _company_from_path(path),
                "indicator": _indicator_from_text(chunk_text),
                "gri_code": _gri_code_from_text(chunk_text),
                "year": 2024 if source_type == "benchmark" else 2016,
            },
        )
        Embedding.objects.create(
            vector_chunk=vector_chunk,
            model=settings.OPENAI_EMBEDDING_MODEL if settings.OPENAI_API_KEY else "deterministic-local",
            dimensions=3072,
            vector=embedding_for_text(chunk_text),
            token_count=max(1, len(chunk_text) // 4),
        )
        created += 1
    return created


def _company_from_path(path):
    if "Advantech" in path.name:
        return "研華2395"
    if "TECO" in path.name:
        return "東元1504"
    if "HIWIN" in path.name:
        return "上銀2049"
    return ""


def _gri_code_from_text(text):
    match = re.search(r"305-[1-7]", text)
    return match.group(0) if match else "305"


def _indicator_from_text(text):
    code = _gri_code_from_text(text)
    return f"GRI {code}" if code != "305" else "GRI 305"


@transaction.atomic
def import_knowledge_base(base_dir=None):
    base = Path(base_dir or KNOWLEDGE_BASE_DIR)
    seed_gri_rule_tables()
    benchmark_companies = []
    rag_chunks = 0
    for path in sorted(base.glob("*.md")):
        if path.name.startswith("DB_Benchmark_"):
            benchmark_companies.append(import_benchmark_markdown(path))
        rag_chunks += import_markdown_to_rag(path)
    return {
        "rules": GRIDisclosureRule.objects.filter(is_active=True).count(),
        "weights": GRIScoringWeight.objects.filter(is_active=True).count(),
        "required_fields": GRIRequiredField.objects.filter(is_active=True).count(),
        "benchmark_companies": len({company.id for company in benchmark_companies}),
        "benchmark_rows": BenchmarkGri305.objects.count(),
        "gold_standards": BenchmarkGoldStandard.objects.count(),
        "rag_chunks": rag_chunks,
    }
