import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from gri.models import GRICheckItem, GRIDisclosure, GRIStandard, RuleVersion, ScoringRule, ScoringWeight

DISCLOSURES = [
    ("305-1", "直接溫室氣體排放 Scope 1", 25, ["scope 1", "範疇一", "直接溫室氣體"], ["排放量", "單位", "年度", "組織邊界", "GWP 來源"]),
    ("305-2", "能源間接溫室氣體排放 Scope 2", 25, ["scope 2", "範疇二", "能源間接"], ["排放量", "單位", "年度", "市場基礎或地點基礎", "排放係數"]),
    ("305-3", "其他間接溫室氣體排放 Scope 3", 20, ["scope 3", "範疇三", "其他間接"], ["類別", "排放量", "單位", "計算方法", "邊界"]),
    ("305-4", "溫室氣體排放密集度", 15, ["排放密集度", "intensity"], ["密集度數值", "分母", "範疇", "年度", "比較基準"]),
    ("305-5", "溫室氣體排放減量", 15, ["減量", "reduction"], ["減量數值", "基準年", "範疇", "方法", "減量措施"]),
]


def main():
    standard, _ = GRIStandard.objects.get_or_create(
        code="GRI 305",
        version="2021",
        defaults={"name": "Emissions", "description": "GRI 305 溫室氣體與排放揭露標準。"},
    )
    rule_version, _ = RuleVersion.objects.get_or_create(name="GRI 305 default", version="v1", defaults={"is_active": True})

    for code, name, weight, keywords, data_points in DISCLOSURES:
        disclosure, _ = GRIDisclosure.objects.update_or_create(
            disclosure_code=code,
            version="2021",
            defaults={
                "standard": standard,
                "disclosure_name": name,
                "description": name,
                "required_keywords": keywords,
                "required_data_points": data_points,
                "scoring_logic": "0 分未揭露；1 分有揭露但不完整；2 分完整揭露，再依權重換算百分制。",
                "weight": weight,
                "is_active": True,
            },
        )
        ScoringWeight.objects.update_or_create(disclosure=disclosure, defaults={"weight_percent": weight, "is_active": True})
        ScoringRule.objects.update_or_create(
            disclosure=disclosure,
            name=f"{code} default scoring",
            defaults={
                "rule_version": rule_version,
                "logic": "檢查是否具備數值、單位、年度、範疇、邊界、計算方法與來源引用。",
                "is_active": True,
            },
        )
        for index, point in enumerate(data_points, start=1):
            GRICheckItem.objects.update_or_create(
                disclosure=disclosure,
                name=point,
                defaults={
                    "description": f"{code} 必備資料點：{point}",
                    "keywords": [point],
                    "data_points": [point],
                    "is_required": True,
                    "sort_order": index,
                    "is_active": True,
                },
            )
    print("Seeded GRI 305 disclosures, check items, scoring rules, and weights.")


if __name__ == "__main__":
    main()
