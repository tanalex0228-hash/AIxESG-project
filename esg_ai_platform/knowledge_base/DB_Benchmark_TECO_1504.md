# 同業競爭者 ESG E1.1 (GRI 305-1~5) 詳細資料欄位規格書

## 項目一：基本資訊與中介資料 (Metadata)

在對比同業數據前，必須先定義同業的基本屬性，以便系統進行篩選與分類權重計算。

### 1. Competitor_Profile (同業基本檔案)
*   **Company_ID**: `TW_1504` (主鍵，東元電機)
*   **Company_Name**: `東元電機股份有限公司` (公司名稱) [1]
*   **Stock_Code**: `1504` (股票代號)
*   **Industry_Class**: `機電、家電及工程` (產業分類) [2]
*   **Report_Year**: `2024` (報告書年度) [2]
*   **Report_Page_Count**: `115` (報告書總頁數) [3]
*   **Verification_Status**: `TRUE` (是否通過第三方查證) [1]
*   **Verification_Standard**: `AA1000AS v3 中度等級查證, ISO 14064-1:2018` (查證標準) [1, 4]

---

## 項目二：GRI 305 核心指標結構化數據

### 1. GRI 305-1 直接溫室氣體排放 (範疇一 Scope 1)
*   **S1_Total_Emissions**: `13728.00` (直接溫室氣體排放總量，單位：tCO2e) [5]
*   **S1_Gases_Included**: `CO2, CH4, N2O, HFCs, PFCs, SF6, NF3` (包含的氣體種類) [6]
*   **S1_Biogenic_Emissions**: `0.00` (報告書中未明列生物源排放)
*   **S1_Base_Year**: `2021` (範疇一計算基準年) [5]
*   **S1_Base_Year_Emissions**: `19505.00` (2021基準年範疇一盤查排放量，單位：tCO2e) [5]
*   **S1_Base_Year_Recalculation_Context**: `2023年前範疇100%為估算值，自2024年起採用合併子公司實際盤查量，依內部盤查結果揭露` [5]
*   **S1_Emission_Factors_Source**: `各國公告標準 (如當地能源局公告之當年度係數)` [4, 6]
*   **S1_GWP_Source**: `IPCC 第六次評估報告 (AR6版次)` [4]
*   **S1_Consolidation_Approach**: `營運控制` (認列擁有營運權子公司之所有排放) [6]
*   **S1_Methodology_Tools**: `ISO 14064-1:2018 溫室氣體盤查標準與內部全球溫室氣體盤查數位化系統平台` [1, 7]
*   **S1_Breakdown_Data**: 
    ```json
    {
      "Note": "報告書中未按設施或國家提供範疇一最細顆粒度分解數據，僅揭露整體盤查量 13,728 tCO2e"
    }
    ```

### 2. GRI 305-2 能源間接溫室氣體排放 (範疇二 Scope 2)
*   **S2_Location_Based_Emissions**: `38279.00` (地點基礎的能源間接排放總量，單位：tCO2e) [5]
*   **S2_Market_Based_Emissions**: `38279.00` (市場基礎的能源間接排放總量，單位：tCO2e) [5]
*   **S2_Gases_Included**: `CO2, CH4, N2O, HFCs, PFCs, SF6, NF3` [6]
*   **S2_Base_Year**: `2021` [5]
*   **S2_Base_Year_Emissions**: `54085.00` (2021基準年盤查量，單位：tCO2e) [5]
*   **S2_Base_Year_Recalculation_Context**: `2023年前範疇100%為估算值，2024年後為合併子公司實際盤查` [5]
*   **S2_Emission_Factors_Source**: `地區電力係數依照當地能源局公告當年度係數為主 (例如：台灣0.494；美國0.371；大陸0.792等)` [4, 8]
*   **S2_GWP_Source**: `IPCC AR6版次` [4]
*   **S2_Consolidation_Approach**: `營運控制` [6]
*   **S2_Methodology_Tools**: `ISO 14064-1:2018 溫室氣體盤查標準` [1]
*   **S2_Breakdown_Data**: 
    ```json
    {
      "Note": "總計 38,279 tCO2e，未詳細拆分單一國家或能源設施數據"
    }
    ```

### 3. GRI 305-3 其它間接溫室氣體排放 (範疇三 Scope 3)
*   **S3_Total_Emissions**: `27167070.91` (其它間接排放總量，單位：tCO2e) [4]
*   **S3_Gases_Included**: `CO2e` (以二氧化碳當量統稱) [4]
*   **S3_Biogenic_Emissions**: `0.00` (未提及)
*   **S3_Base_Year**: `2019` (2019年起啟動範疇三盤查) [4]
*   **S3_Base_Year_Emissions**: `NULL` (報告書未明列2019基準年範疇三總量) 
*   **S3_Emission_Factors_Source**: `供應商、東元自身廠區盤查數據、台灣環保署產品碳足跡計算服務平台、Ecoinvent 3.0及中國產品全生命週期溫室氣體排放係數庫` [9]
*   **S3_Methodology_Tools**: `ISO 14064-1:2018 (台灣地區通過查證)` [4]
*   **S3_Categories_Breakdown**: 
    ```json
    {
      "Upstream": {
        "1_Purchased_Goods_Services": "327238.30",
        "2_Capital_Goods": "153.81",
        "3_Fuel_Energy_Activities": "15017.18",
        "4_Upstream_Transportation": "7472.48",
        "5_Waste_Generated": "2212.29",
        "6_Business_Travel": "未揭露",
        "7_Employee_Commuting": "1385.89",
        "8_Upstream_Leased_Assets": "未揭露"
      },
      "Downstream": {
        "9_Downstream_Transportation": "4830.96",
        "10_Processing_Sold_Products": "未揭露",
        "11_Use_Of_Sold_Products": "26808760.00",
        "12_End_Of_Life_Treatment": "未揭露",
        "13_Downstream_Leased_Assets": "未揭露",
        "14_Franchises": "未揭露",
        "15_Investments": "未揭露"
      }
    }
    ```
    *(備註：S3數據主要來自於銷售產品使用，佔範疇三總排放量 98.7% [10])*

### 4. GRI 305-4 溫室氣體排放強度 (Emissions Intensity)
*   **Intensity_Ratio**: `1.12` [5]
*   **Intensity_Denominator_Type**: `貨幣單位(營收)` [5]
*   **Intensity_Denominator_Value**: `55234.746` (合併營收55,234,746仟元，即55,234.746百萬元) [5]
*   **Intensity_Denominator_Unit**: `百萬元台幣` [5]
*   **Intensity_Scopes_Included**: `範疇一+二` (強度比值公式為：範疇一+範疇二 / 合併營收) [5]
*   **Intensity_Gases_Included**: `CO2, CH4, N2O, HFCs, PFCs, SF6, NF3` [6]

### 5. GRI 305-5 溫室氣體排放減量 (Reduction)
*   **Reduction_Amount**: `14467.00` (類別1即範疇一減量14,467 tCO2e) 或 `292.00` (2024年特定節能計畫減碳量) [11, 12]
*   **Reduction_Gases_Included**: `CO2e` (溫室氣體總當量) [12]
*   **Reduction_Baseline_Type**: `與基準年比較(盤查法)` [12]
*   **Reduction_Baseline_Rationale**: `宣示十年營運減排50%目標，以2021年為減碳比較基準年` [12, 13]
*   **Reduction_Scopes_Included**: `範疇一 / 範疇二 / 範疇三` (類別1減量14,467噸，類別2減量15,635噸，類別3~6減量14,533,307噸) [12]
*   **Reduction_Effects_Sum**: `2024年共提出27項節能減碳計畫，包含設備升級、空間管理及再生能源導入，共節電591,654度電，減碳量為292噸CO2e` [11, 14]
*   **Carbon_Offsets_Used**: `FALSE` (推行內部碳定價制度ICP 1,600元/噸，並未提及依賴碳抵換達成目標) [15]
*   **Carbon_Offsets_Details**: `NULL`

---

## 項目三：定性診斷與改善黃金範本庫 (用於系統優化建議)

### 2. Competitor_Gold_Standard_Paragraphs (同業黃金寫法範本表)
*   **Standard_ID**: `TECO_305_4_001`
*   **Company_ID**: `TW_1504`
*   **Target_Indicator**: `GRI_305_4_Intensity`
*   **System_Score_Tag**: `2`
*   **Gold_Standard_Text**: "溫室氣體盤查邊界設定方法為營運控制，認列擁有營運權子公司之所有排放... 2021年～2023年採用「推估排放總量」以「實際盤查量」除以「覆蓋率」計算... 「排放量密集度」以「排放預估總量」除以「集團合併營收」計算。密集度＝(範疇一＋範疇二)／合併營收(以百萬元為單位)。" [5, 6]
*   **Excellent_Reason**: 這段文字獲得高分的原因在於**極度透明的計算邏輯**。同業明確揭露了溫室氣體排放強度的「分子」（範疇一＋範疇二）與「分母」（集團合併營收 百萬元），甚至清晰交待了歷史數據（2021-2023）因盤查覆蓋率不足而採用的「推估」假設邏輯，使得數據呈現具備高度的可追溯性與可比性 [5, 6]。
*   **Action_Plan_Template**: "建議受稽核企業在撰寫『排放強度（GRI 305-4）』時，應明確列出計算公式（如：強度 = [範疇1+範疇2總量] / [分母數值]），並具體標示分母單位（例如：百萬元營收、噸產量）。若遇歷史盤查範圍擴大的情形，應於備註欄清晰說明數據推估或重新計算的假設方法，以符合GRI的完整揭露精神。"