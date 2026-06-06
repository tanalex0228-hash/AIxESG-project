# 同業競爭者 ESG E1.1 (GRI 305-1~5) 詳細資料欄位規格書

## 項目一：基本資訊與中介資料 (Metadata)
在對比同業數據前，必須先定義同業的基本屬性，以便系統進行篩選與分類權重計算。

### 1. Competitor_Profile (同業基本檔案)
*   **Company_ID**: `TW_2395` 
*   **Company_Name**: `研華股份有限公司 (Advantech Co., Ltd.)` [1]
*   **Stock_Code**: `2395` 
*   **Industry_Class**: `電腦及周邊設備業` [1]
*   **Report_Year**: `2024` [2]
*   **Report_Page_Count**: `260` (預估頁數) [3]
*   **Verification_Status**: `TRUE` [4]
*   **Verification_Standard**: `AA1000AS v3 Type 2 高度保證等級, ISO 14064-1:2018, ISAE 3000` [4], [5]


## 項目二：GRI 305 核心指標結構化數據

### 1. GRI 305-1 直接溫室氣體排放 (範疇一 Scope 1)
用以記錄同業自身擁有或控制的營運據點所產生的直接排放。

*   **S1_Total_Emissions**: `3565.0395` (單位：tCO2e) [6]
*   **S1_Gases_Included**: `CO2, CH4, N2O, HFCs` (PFCs, SF6, NF3 為 0) [6]
*   **S1_Biogenic_Emissions**: `0` 
*   **S1_Base_Year**: `2019` [7]
*   **S1_Base_Year_Emissions**: `30598.85` (註：此為 2019 年範疇一+二之總和) [7]
*   **S1_Base_Year_Recalculation_Context**: `因應 2025 年設定更具挑戰性之 1.5°C SBT 減碳路徑目標而重新審視` [8]
*   **S1_Emission_Factors_Source**: `採用環保署發布版本及各區域國家公告之係數` [9]
*   **S1_GWP_Source**: `IPCC 評估報告` [10]
*   **S1_Consolidation_Approach**: `營運控制權` [11]
*   **S1_Methodology_Tools**: `ISO 14064-1:2018` [11]
*   **S1_Breakdown_Data**: `{"Taiwan_ACL": 804.3931, "China_AKMC": 2531.4193, "Japan_AJMC": 150.3177, "Korea_AKSC": 9.7673, "USA_ANA": 23.7654, "Europe_AEU": 45.3768}` [6]


### 2. GRI 305-2 能源間接溫室氣體排放 (範疇二 Scope 2)
用以記錄同業因消耗購買或取得之電力、供熱、製冷和蒸氣所產生的間接排放。

*   **S2_Location_Based_Emissions**: `25004.4689` (單位：tCO2e) [12]
*   **S2_Market_Based_Emissions**: `22726.6437` (單位：tCO2e) [12]
*   **S2_Gases_Included**: `CO2` (主要為電力與蒸氣) [9]
*   **S2_Base_Year**: `2019` [7]
*   **S2_Base_Year_Emissions**: `與 S1 合併計算為 30598.85` [7]
*   **S2_Base_Year_Recalculation_Context**: `同範疇一` [8]
*   **S2_Emission_Factors_Source**: `台灣經濟部能源署 (0.494 kg CO2e/kWh)、中國生態環境部 (0.5856kgCO2/kWh)、九州電力及當地國家公告之電力係數` [9]
*   **S2_GWP_Source**: `IPCC 評估報告` [10]
*   **S2_Consolidation_Approach**: `營運控制權` [11]
*   **S2_Methodology_Tools**: `ISO 14064-1:2018` [11]
*   **S2_Breakdown_Data**: `{"Taiwan_ACL": 9222.2612, "China_AKMC": 11974.1196, "Japan_AJMC": 1203.5099, "Korea_AKSC": 158.4522, "USA_ANA": 168.3008, "Europe_AEU": 0}` (Market-based 數據，歐洲因 100% 綠電為 0) [12]


### 3. GRI 305-3 其它間接溫室氣體排放 (範疇三 Scope 3)
用以記錄同業組織外部價值鏈的上游與下游排放。

*   **S3_Total_Emissions**: `750942.4011` (單位：tCO2e) [13]
*   **S3_Gases_Included**: `CO2e 總和` 
*   **S3_Biogenic_Emissions**: `0` 
*   **S3_Base_Year**: `2019` [7]
*   **S3_Base_Year_Emissions**: `N/A` 
*   **S3_Emission_Factors_Source**: `GHG Protocol Scope 3 Evaluator 等資料庫` [14]
*   **S3_Methodology_Tools**: `ISO 14064-1:2018` [13]
*   **S3_Categories_Breakdown**: 
    {
      "Upstream": {
        "1_Purchased_Goods_Services": "218120.4187",
        "2_Capital_Goods": "5610.8359",
        "3_Fuel_Energy_Activities": "2909.8535",
        "4_Upstream_Transportation": "380.0811",
        "5_Waste_Generated": "65.9594",
        "6_Business_Travel": "162.1535",
        "7_Employee_Commuting": "731.7524",
        "8_Upstream_Leased_Assets": "52.1071"
      },
      "Downstream": {
        "9_Downstream_Transportation": "95.0531",
        "10_Processing_Sold_Products": "0",
        "11_Use_Of_Sold_Products": "513625.6319",
        "12_End_Of_Life_Treatment": "9.6846",
        "13_Downstream_Leased_Assets": "0",
        "14_Franchises": "0",
        "15_Investments": "9178.8698"
      }
    } [13]


### 4. GRI 305-4 溫室氣體排放強度 (Emissions Intensity)
追蹤同業如何將絕對排放量與組織特定度量標準（分母）進行正規化比對。

*   **Intensity_Ratio**: `0.440` [15]
*   **Intensity_Denominator_Type**: `貨幣單位(營收)` [15]
*   **Intensity_Denominator_Value**: `59786` (百萬元新台幣) [16]
*   **Intensity_Denominator_Unit**: `百萬元新台幣營收` [15]
*   **Intensity_Scopes_Included**: `範疇一 + 範疇二` [15]
*   **Intensity_Gases_Included**: `CO2e 總量` [15]


### 5. GRI 305-5 溫室氣體排放減量 (Reduction)
記錄同業因採取流程重新設計、設備更新、燃料轉換或行為改變等減量措施所產生的直接減碳成效。

*   **Reduction_Amount**: `202927.42` (註：C11產品使用階段減碳量；另透過再生能源抵減 2277.83 tCO2e) [7], [17]
*   **Reduction_Gases_Included**: `CO2e 總量` 
*   **Reduction_Baseline_Type**: `與基準年比較(盤查法)` [15]
*   **Reduction_Baseline_Rationale**: `SBTi 目標設定與追蹤，與 2019 基準年相比下降 28.0%` [15]
*   **Reduction_Scopes_Included**: `範疇一 / 範疇二 / 範疇三` [7], [17]
*   **Reduction_Effects_Sum**: `導入 iEMS 智慧能源管理系統、產線 eSOP 電腦自動關機排程(省 4,555 kWh)、產品製程印刷優化(省 1,830M³天然氣)、液體烤漆改粉體烤漆，以及提升綠電使用比例。` [18], [19], [20]
*   **Carbon_Offsets_Used**: `TRUE` (採認購綠電與憑證抵減) [7]
*   **Carbon_Offsets_Details**: `{"Type": "綠電採購與再生能源憑證 (GEC)", "Amount_tCO2e": 2277.83, "Note": "昆山購買RE100認可之憑證，歐洲100%直接綠電採購"}` [7], [21]


## 項目三：定性診斷與改善黃金範本庫 (用於系統優化建議)

### 2. Competitor_Gold_Standard_Paragraphs (同業黃金寫法範本表)
*   **Standard_ID**: `Gold_GRI_305_3_001`
*   **Company_ID**: `TW_2395`
*   **Target_Indicator**: `GRI_305_3_Scope3`
*   **System_Score_Tag**: `2`
*   **Gold_Standard_Text**: `研華 2024 年單位營收範疇三溫室氣體排放量較 2023 年下降 16.9%，主要與 C11（產品使用）減量幅度達 22.6%（減碳量為 202,927.42 公噸 CO2e）最為相關，未來將持續透過內部節能標章、產品節能設計、電源效率提升及內部碳定價之推動，持續降低範疇三的排放量。` [17]
*   **Excellent_Reason**: `此揭露不僅詳盡盤查了最困難的範疇三 15 項子類別，更精確抓出了「C11 產品使用階段」為主要碳排熱點（高達 51萬噸）。最優秀之處在於其將減碳績效具體量化（減碳 20萬噸），並明確連結到「內部碳定價 (ICP)」與「產品綠色設計」等實質行動策略，為防洗綠的最佳實證。` 
*   **Action_Plan_Template**: `建議貴公司於進行範疇三盤查時，不應僅停留於 C1(採購) 或 C6(差旅) 的初步估算。應效仿標竿同業，針對下游之「C11 產品使用階段」進行生命週期評估 (LCA)，並提出具體的產品節能改款計畫與量化減碳數據，以展現真實的氣候行動力。`