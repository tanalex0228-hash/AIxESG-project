# 同業競爭者 ESG E1.1 (GRI 305-1~5) 詳細資料欄位規格書

## 項目一：基本資訊與中介資料 (Metadata)
在對比同業數據前，必須先定義同業的基本屬性，以便系統進行篩選與分類權重計算。

```markdown
### 1. Competitor_Profile (同業基本檔案)
*   **Company_ID**: `TW_2049` 
*   **Company_Name**: `上銀科技股份有限公司`
*   **Stock_Code**: `2049`
*   **Industry_Class**: `精密機械 / 傳動控制與系統科技`
*   **Report_Year**: `2024`
*   **Report_Page_Count**: `157`
*   **Verification_Status**: `TRUE`
*   **Verification_Standard**: `AA1000AS v3, GRI 2021, SASB, TCFD, ISO 14064-1:2018`
```

## 項目二：GRI 305 核心指標結構化數據
嚴格對照 GRI 305 2016 官方準則規範的要求與彙編指引，將上銀科技數據拆解至最細顆粒度。

### 1. GRI 305-1 直接溫室氣體排放 (範疇一 Scope 1)
```markdown
*   **S1_Total_Emissions**: `13233.975`
*   **S1_Gases_Included**: `CO2, CH4, N2O, HFCs`
*   **S1_Biogenic_Emissions**: `NULL` (報告書中未明列生物源排放)
*   **S1_Base_Year**: `2021`
*   **S1_Base_Year_Emissions**: `11201.425`
*   **S1_Base_Year_Recalculation_Context**: `因應公司 2024 年度通過 SBTi 目標審核，2021~2022 年溫室氣體數據調整計算方法學及邊界。`
*   **S1_Emission_Factors_Source**: `依各廠區所在地之最新官方公告標準（如環境部溫室氣體排放係數管理表 6.0.4版）`
*   **S1_GWP_Source**: `IPCC 第六次評估報告 (AR6)`
*   **S1_Consolidation_Approach**: `營運控制`
*   **S1_Methodology_Tools**: `ISO 14064-1:2018`
*   **S1_Breakdown_Data**: 
    {
      "By_Entity": {
        "Parent_Company": 10899.6222,
        "Subsidiaries": 2334.3532
      }
    }
```

### 2. GRI 305-2 能源間接溫室氣體排放 (範疇二 Scope 2)
```markdown
*   **S2_Location_Based_Emissions**: `118164.483`
*   **S2_Market_Based_Emissions**: `116959.605`
*   **S2_Gases_Included**: `CO2, CH4, N2O, HFCs`
*   **S2_Base_Year**: `2021`
*   **S2_Base_Year_Emissions**: `165145.537` (Location-based 與 Market-based 基準年同值)
*   **S2_Base_Year_Recalculation_Context**: `因應公司 2024 年度通過 SBTi 目標審核，調整計算方法學及邊界。`
*   **S2_Emission_Factors_Source**: `2024 年採用當年度之電力排碳係數 0.474 公斤 CO2e/度`
*   **S2_GWP_Source**: `IPCC 第六次評估報告 (AR6)`
*   **S2_Consolidation_Approach**: `營運控制`
*   **S2_Methodology_Tools**: `ISO 14064-1:2018`
*   **S2_Breakdown_Data**: 
    {
      "Market_Based_By_Entity": {
        "Parent_Company": 112134.6824,
        "Subsidiaries": 4824.9222
      }
    }
```

### 3. GRI 305-3 其它間接溫室氣體排放 (範疇三 Scope 3)
```markdown
*   **S3_Total_Emissions**: `272986.573`
*   **S3_Gases_Included**: `CO2, CH4, N2O, HFCs`
*   **S3_Biogenic_Emissions**: `NULL`
*   **S3_Base_Year**: `2022`
*   **S3_Base_Year_Emissions**: `246074.597`
*   **S3_Emission_Factors_Source**: `環境部溫室氣體排放係數管理表 6.0.4版、環境部產品碳足跡資訊網、SimaPro 資料庫`
*   **S3_Methodology_Tools**: `ISO 14064:2018 及 GHG Protocol 標準`
*   **S3_Categories_Breakdown**: 
    {
      "Upstream": {
        "1_Purchased_Goods_Services": 131083.746,
        "2_Capital_Goods": 23207.7514,
        "3_Fuel_Energy_Activities": 27451.2622,
        "4_Upstream_Transportation": 10595.4699,
        "5_Waste_Generated": 774.42,
        "6_Business_Travel": 543.8104,
        "7_Employee_Commuting": 4429.9735,
        "8_Upstream_Leased_Assets": 0.73
      },
      "Downstream": {
        "9_Downstream_Transportation": 1425.11,
        "10_Processing_Sold_Products": 522.5941,
        "11_Use_Of_Sold_Products": 69596.3657,
        "12_End_Of_Life_Treatment": 131.4786,
        "13_Downstream_Leased_Assets": 0,
        "14_Franchises": 0,
        "15_Investments": 3223.8608
      }
    }
```
*(註：上述 JSON 數值已將報告書中「經第三方查證」與「僅內部盤查」數據進行精確加總)*

### 4. GRI 305-4 溫室氣體排放強度 (Emissions Intensity)
```markdown
*   **Intensity_Ratio**: `5.34`
*   **Intensity_Denominator_Type**: `貨幣單位(營收)`
*   **Intensity_Denominator_Value**: `24392`
*   **Intensity_Denominator_Unit**: `新台幣佰萬元`
*   **Intensity_Scopes_Included**: `範疇一 + 範疇二 (Market-based)`
*   **Intensity_Gases_Included**: `CO2, CH4, N2O, HFCs`
```

### 5. GRI 305-5 溫室氣體排放減量 (Reduction)
```markdown
*   **Reduction_Amount**: `3736` (2024 年推行節能專案之直接減碳量)
*   **Reduction_Gases_Included**: `CO2e`
*   **Reduction_Baseline_Type**: `與基準年比較(盤查法)`
*   **Reduction_Baseline_Rationale**: `配合 SBTi 科學基礎減量目標倡議，以 2021 年為範疇一與範疇二之基準年。`
*   **Reduction_Scopes_Included**: `範疇一 / 範疇二`
*   **Reduction_Effects_Sum**: `2024 年推動節能專案共計 27 件（包含空壓系統、空調系統、製程改善、防制設備、待機改善、照明系統等），總節電達 7,880,955 度。同時新增自發自用與外購再生電力 5,169 MWh。整體範疇 1+2 較基準年(2021)下降達 26.2%。`
*   **Carbon_Offsets_Used**: `FALSE` (目前以實質減碳為主，宣告未來淨零排放目標剩餘 10% 才會以碳權抵換)
*   **Carbon_Offsets_Details**: `NULL`
```

## 項目三：定性診斷與改善黃金範本庫 (用於系統優化建議)
這部分欄位用以儲存技術長要寫進資料庫的**「文字段落與評分標籤」**。當系統掃描到客戶端數據缺漏或不完整（被扣分）時，後端程式可以直接調用此處的同業優良原文進行展示與建議。

```markdown
### 2. Competitor_Gold_Standard_Paragraphs (同業黃金寫法範本表)
*   **Standard_ID**: `GRI_305_3_ValueChain_Transparency`
*   **Company_ID**: `TW_2049`
*   **Target_Indicator**: `GRI_305_3_Scope3`
*   **System_Score_Tag**: `2`
*   **Gold_Standard_Text**: `「上銀科技參考 ISO 14064:2018 及 GHG Protocol 標準，盤查各類別間接溫室氣體排放量。範疇 3的主要排放類別為 C1 採購商品及服務及 C11 售出產品使用... (並於報告書中詳細表列 15 項類別，並清晰切割出『經第三方查證』與『僅內部盤查』的具體數值)。」`
*   **Excellent_Reason**: `此段落完整度極高。上銀科技不僅詳細盤查了範疇三的 15 項子類別，更在數據呈現上具備高度的透明性，誠實且明確地區分出哪些數據已通過「第三方查證」，哪些目前為「僅內部盤查」。這種循序漸進且誠實揭露的盤查方法，極大提升了企業溫室氣體盤查的公信力與可驗證性。`
*   **Action_Plan_Template**: `建議貴公司在推動範疇三（價值鏈）溫室氣體盤查時，可優先盤點如「採購商品及服務」與「售出產品使用」等重大排放熱點。初期若資源有限，可先由內部團隊進行估算盤查，並於報告書中明確標示「經第三方查證」與「內部盤查」之數據界線，展現資訊透明度，並逐年擴大第三方查證的覆蓋率。`