STANDARD_INDUSTRIES = {
    "05": {"name_zh": "電機機械", "name_en": "Electrical Machinery"},
    "24": {"name_zh": "半導體業", "name_en": "Semiconductors"},
    "25": {"name_zh": "電腦及週邊設備業", "name_en": "Computer and Peripherals"},
    "27": {"name_zh": "通信網路業", "name_en": "Communications and Network"},
    "28": {"name_zh": "電子零組件業", "name_en": "Electronic Components"},
}

COMPANY_INDUSTRY_BY_CODE = {
    "1503": "05",
    "1504": "05",
    "1513": "05",
    "1519": "05",
    "1560": "05",
    "1590": "05",
    "2049": "05",
    "4549": "05",
    "7750": "05",
    "8996": "05",
    "2303": "24",
    "2330": "24",
    "2344": "24",
    "2408": "24",
    "2454": "24",
    "3443": "24",
    "3711": "24",
    "5274": "24",
    "6223": "24",
    "7769": "24",
    "2301": "25",
    "2356": "25",
    "2357": "25",
    "2376": "25",
    "2382": "25",
    "2395": "25",
    "3017": "25",
    "3231": "25",
    "4938": "25",
    "6669": "25",
    "2345": "27",
    "2455": "27",
    "3081": "27",
    "3163": "27",
    "3363": "27",
    "3491": "27",
    "3596": "27",
    "4979": "27",
    "6285": "27",
    "6442": "27",
    "2059": "28",
    "2308": "28",
    "2327": "28",
    "2368": "28",
    "2383": "28",
    "3037": "28",
    "3653": "28",
    "4958": "28",
    "6274": "28",
    "8046": "28",
}

COMPANY_INDUSTRY_BY_NAME = {
    "東元": "05",
    "華城": "05",
    "士電": "05",
    "中興電": "05",
    "亞德客-KY": "05",
    "亞德客": "05",
    "新代": "05",
    "上銀": "05",
    "高力": "05",
    "中砂": "05",
    "桓達": "05",
    "桓達企業": "05",
    "台積電": "24",
    "聯電": "24",
    "聯發科": "24",
    "南亞科": "24",
    "華邦電": "24",
    "創意": "24",
    "信驊": "24",
    "旺矽": "24",
    "日月光投控": "24",
    "鴻勁": "24",
    "廣達": "25",
    "緯創": "25",
    "緯穎": "25",
    "華碩": "25",
    "和碩": "25",
    "研華": "25",
    "英業達": "25",
    "光寶科": "25",
    "技嘉": "25",
    "奇鋐": "25",
    "智邦": "27",
    "啟碁": "27",
    "智易": "27",
    "光聖": "27",
    "聯亞": "27",
    "華星光": "27",
    "波若威": "27",
    "上詮": "27",
    "全新": "27",
    "昇達科": "27",
    "台達電": "28",
    "國巨": "28",
    "欣興": "28",
    "金像電": "28",
    "南電": "28",
    "台光電": "28",
    "川湖": "28",
    "健策": "28",
    "臻鼎-KY": "28",
    "臻鼎": "28",
    "台燿": "28",
}


def ensure_standard_industries():
    from reports.models import IndustryCategory

    categories = {}
    for code, values in STANDARD_INDUSTRIES.items():
        category, _ = IndustryCategory.objects.update_or_create(
            code=code,
            defaults={
                "name_zh": values["name_zh"],
                "name_en": values["name_en"],
                "is_active": True,
            },
        )
        categories[code] = category
    return categories


def industry_code_for_company(company_code="", company_name=""):
    code = str(company_code or "").strip()
    if code in COMPANY_INDUSTRY_BY_CODE:
        return COMPANY_INDUSTRY_BY_CODE[code]
    normalized_name = str(company_name or "").strip()
    for name, industry_code in COMPANY_INDUSTRY_BY_NAME.items():
        if name and name in normalized_name:
            return industry_code
    return ""


def normalize_report_industry(report, save=True):
    categories = ensure_standard_industries()
    industry_code = industry_code_for_company(report.company_code, report.company_name)
    category = categories.get(industry_code)
    if category:
        report.industry_category_ref = category
        report.industry_category = category.name_zh
        if save:
            report.save(update_fields=["industry_category_ref", "industry_category", "updated_at"])
    return category
