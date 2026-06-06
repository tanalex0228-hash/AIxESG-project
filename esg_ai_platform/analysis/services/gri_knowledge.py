from decimal import Decimal

DISCLOSURE_RULES = {
    "305-1": {
        "name": "直接溫室氣體排放 Scope 1",
        "requirement": "揭露範疇一直接溫室氣體排放總量、涵蓋氣體、生質 CO2、基準年、排放係數、GWP 來源、盤查邊界與方法學。",
    },
    "305-2": {
        "name": "能源間接溫室氣體排放 Scope 2",
        "requirement": "揭露地點基礎與市場基礎能源間接排放、排放係數、GWP、方法學與基準年。",
    },
    "305-3": {
        "name": "其他間接溫室氣體排放 Scope 3",
        "requirement": "揭露範疇三排放總量、類別明細、方法學、排放係數與基準年。",
    },
    "305-4": {
        "name": "溫室氣體排放密集度",
        "requirement": "揭露排放密集度、分母與納入計算的範疇。",
    },
    "305-5": {
        "name": "溫室氣體排放減量",
        "requirement": "揭露減量數值、減量基準、減量方法、減量範疇與碳抵換資訊。",
    },
}

SCORING_WEIGHTS = {
    "305-1": [
        ("S1_Total_Emissions", "排放總量", Decimal("4")),
        ("S1_Gases_Included", "氣體種類", Decimal("3")),
        ("S1_Base_Year", "基準年", Decimal("3")),
        ("S1_Base_Year_Emissions", "基準年排放量", Decimal("2")),
        ("S1_Emission_Factors_Source", "排放係數", Decimal("3")),
        ("S1_GWP_Source", "GWP來源", Decimal("2")),
        ("S1_Consolidation_Approach", "盤查邊界", Decimal("1")),
        ("S1_Methodology_Tools", "方法學", Decimal("2")),
    ],
    "305-2": [
        ("Location_Based", "Location Based", Decimal("5")),
        ("Market_Based", "Market Based", Decimal("5")),
        ("Emission_Factor", "Emission Factor", Decimal("3")),
        ("Methodology", "Methodology", Decimal("3")),
        ("Base_Year", "Base Year", Decimal("4")),
    ],
    "305-3": [
        ("Total_Emissions", "Scope3總量", Decimal("5")),
        ("Categories_Breakdown", "Category揭露", Decimal("10")),
        ("Methodology", "Methodology", Decimal("5")),
        ("Emission_Factor", "Emission Factor", Decimal("5")),
    ],
    "305-4": [
        ("Intensity_Ratio", "Intensity Ratio", Decimal("5")),
        ("Denominator", "Denominator", Decimal("5")),
        ("Scopes_Included", "Scopes Included", Decimal("5")),
    ],
    "305-5": [
        ("Reduction_Amount", "Reduction Amount", Decimal("5")),
        ("Reduction_Baseline", "Baseline", Decimal("5")),
        ("Reduction_Method", "Reduction Method", Decimal("5")),
        ("Reduction_Scope", "Reduction Scope", Decimal("5")),
    ],
}

REQUIRED_FIELDS = {
    "305-1": [
        "S1_Total_Emissions",
        "S1_Gases_Included",
        "S1_Biogenic_Emissions",
        "S1_Base_Year",
        "S1_Base_Year_Emissions",
        "S1_Emission_Factors_Source",
        "S1_GWP_Source",
        "S1_Consolidation_Approach",
        "S1_Methodology_Tools",
    ],
    "305-2": ["Location_Based", "Market_Based", "Emission_Factor", "GWP", "Methodology", "Base_Year"],
    "305-3": ["Total_Emissions", "Categories_Breakdown", "Methodology", "Emission_Factor", "Base_Year"],
    "305-4": ["Intensity_Ratio", "Denominator", "Scopes_Included"],
    "305-5": ["Reduction_Amount", "Reduction_Baseline", "Reduction_Method", "Carbon_Offsets"],
}

FIELD_LABELS = {
    field_key: label
    for disclosure_weights in SCORING_WEIGHTS.values()
    for field_key, label, _score in disclosure_weights
} | {
    "S1_Biogenic_Emissions": "生質 CO2 排放",
    "GWP": "GWP",
    "Base_Year": "Base Year",
    "Carbon_Offsets": "Carbon Offsets",
}

FIELD_KEYWORDS = {
    "S1_Total_Emissions": ["scope 1", "範疇一", "直接溫室氣體", "直接排放"],
    "S1_Gases_Included": ["CO2", "CH4", "N2O", "HFC", "PFC", "SF6", "NF3", "氣體"],
    "S1_Biogenic_Emissions": ["生質", "biogenic"],
    "S1_Base_Year": ["基準年", "base year"],
    "S1_Base_Year_Emissions": ["基準年排放", "base year emissions"],
    "S1_Emission_Factors_Source": ["排放係數", "emission factor"],
    "S1_GWP_Source": ["GWP", "全球暖化潛勢", "IPCC"],
    "S1_Consolidation_Approach": ["營運控制", "財務控制", "股權比例", "組織邊界", "盤查邊界"],
    "S1_Methodology_Tools": ["ISO 14064", "GHG Protocol", "方法學", "計算工具", "盤查方法"],
    "Location_Based": ["location-based", "地點基礎", "所在地基礎"],
    "Market_Based": ["market-based", "市場基礎"],
    "Emission_Factor": ["排放係數", "emission factor"],
    "GWP": ["GWP", "全球暖化潛勢", "IPCC"],
    "Methodology": ["ISO 14064", "GHG Protocol", "方法學", "計算方法", "盤查方法"],
    "Base_Year": ["基準年", "base year"],
    "Total_Emissions": ["scope 3", "範疇三", "其他間接", "總量"],
    "Categories_Breakdown": ["類別", "category", "Business Travel", "Employee Commuting", "Purchased Goods"],
    "Intensity_Ratio": ["密集度", "intensity"],
    "Denominator": ["分母", "營收", "產量", "denominator"],
    "Scopes_Included": ["範疇一", "範疇二", "scope 1", "scope 2", "scopes included"],
    "Reduction_Amount": ["減量", "reduction", "減少"],
    "Reduction_Baseline": ["基準", "baseline", "基準年"],
    "Reduction_Method": ["節能", "再生能源", "汰換", "能源效率", "減量方法"],
    "Reduction_Scope": ["範疇一", "範疇二", "範疇三", "scope 1", "scope 2", "scope 3"],
    "Carbon_Offsets": ["碳抵換", "offset", "憑證", "certificate"],
}

SCOPE3_CATEGORIES = [
    "Purchased Goods and Services",
    "Capital Goods",
    "Fuel- and Energy-Related Activities",
    "Upstream Transportation and Distribution",
    "Waste Generated in Operations",
    "Business Travel",
    "Employee Commuting",
    "Upstream Leased Assets",
    "Downstream Transportation and Distribution",
    "Processing of Sold Products",
    "Use of Sold Products",
    "End-of-Life Treatment of Sold Products",
    "Downstream Leased Assets",
    "Franchises",
    "Investments",
]

CATEGORY_KEYWORDS = {
    "Purchased Goods and Services": ["Purchased Goods", "Purchased_Goods", "採購商品", "購買商品", "服務"],
    "Capital Goods": ["Capital Goods", "Capital_Goods", "資本財"],
    "Fuel- and Energy-Related Activities": ["Fuel", "Fuel_Energy", "Energy-Related", "燃料", "能源相關"],
    "Upstream Transportation and Distribution": ["Upstream Transportation", "Upstream_Transportation", "上游運輸"],
    "Waste Generated in Operations": ["Waste Generated", "Waste_Generated", "營運廢棄物", "廢棄物"],
    "Business Travel": ["Business Travel", "Business_Travel", "商務旅行", "差旅"],
    "Employee Commuting": ["Employee Commuting", "Employee_Commuting", "員工通勤"],
    "Upstream Leased Assets": ["Upstream Leased", "Upstream_Leased", "上游租賃"],
    "Downstream Transportation and Distribution": ["Downstream Transportation", "Downstream_Transportation", "下游運輸"],
    "Processing of Sold Products": ["Processing of Sold Products", "Processing_of_Sold", "售出產品加工"],
    "Use of Sold Products": ["Use of Sold Products", "Use_of_Sold", "售出產品使用"],
    "End-of-Life Treatment of Sold Products": ["End-of-Life", "End_of_Life", "產品生命終止", "廢棄處理"],
    "Downstream Leased Assets": ["Downstream Leased", "Downstream_Leased", "下游租賃"],
    "Franchises": ["Franchises", "加盟"],
    "Investments": ["Investments", "投資"],
}
