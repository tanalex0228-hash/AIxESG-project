from decimal import Decimal

from django.db import migrations


def seed_excel_gri305_scoring(apps, schema_editor):
    from analysis.services.gri305_excel_reference import SCORING_ITEMS, SECTION_WEIGHTS

    GRIDisclosureRule = apps.get_model("gri", "GRIDisclosureRule")
    GRIScoringWeight = apps.get_model("gri", "GRIScoringWeight")
    GRIRequiredField = apps.get_model("gri", "GRIRequiredField")

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
        disclosure_code = item["disclosure_code"]
        sort_by_disclosure[disclosure_code] = sort_by_disclosure.get(disclosure_code, 0) + 1
        sort_order = sort_by_disclosure[disclosure_code]
        GRIScoringWeight.objects.update_or_create(
            disclosure_code=disclosure_code,
            field_key=item["field_key"],
            defaults={
                "field_label": item["field_label"],
                "max_score": Decimal(item["max_score"]),
                "sort_order": sort_order,
                "is_active": True,
            },
        )
        GRIRequiredField.objects.update_or_create(
            disclosure_code=disclosure_code,
            field_key=item["field_key"],
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

    for row in GRIScoringWeight.objects.all():
        if (row.disclosure_code, row.field_key) not in active_pairs:
            row.is_active = False
            row.save(update_fields=["is_active"])
    for row in GRIRequiredField.objects.all():
        if (row.disclosure_code, row.field_key) not in active_pairs:
            row.is_active = False
            row.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("gri", "0003_grirequiredfield_is_critical_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_excel_gri305_scoring, migrations.RunPython.noop),
    ]
