import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from benchmarks.models import BenchmarkBestPractice, BenchmarkCompany, BenchmarkReport, IndustryCategory


def main():
    industry, _ = IndustryCategory.objects.get_or_create(name="電子與電機設備", defaults={"code": "electronics"})
    companies = ["研華科技", "東元科技", "上銀科技"]
    for company_name in companies:
        company, _ = BenchmarkCompany.objects.get_or_create(name=company_name, defaults={"industry": industry, "is_active": True})
        report, _ = BenchmarkReport.objects.get_or_create(
            company=company,
            report_year=2024,
            title=f"{company_name} 永續報告書標竿示範資料",
        )
        for code in ["305-1", "305-2", "305-3", "305-4", "305-5"]:
            BenchmarkBestPractice.objects.get_or_create(
                company=company,
                disclosure_code=code,
                title=f"{company_name} {code} 揭露做法",
                defaults={
                    "description": "示範資料：用於初始化同業標竿資料結構，正式營運時應由管理者維護已授權的報告書引用、頁碼與揭露摘要。",
                    "example_text": "示範揭露摘要：公司依範疇揭露溫室氣體排放資訊，包含數值、單位、年度與管理措施。",
                    "priority": 1,
                    "is_active": True,
                },
            )
    print("Seeded benchmark companies and sample best practices.")


if __name__ == "__main__":
    main()
