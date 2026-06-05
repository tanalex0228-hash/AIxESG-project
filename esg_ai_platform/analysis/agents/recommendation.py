from .base import AgentResult, BaseAgent


class RecommendationAgent(BaseAgent):
    name = "recommendation"

    def run(self, disclosure_code, status):
        if status == "complete":
            return AgentResult(recommendations=[])
        return AgentResult(
            recommendations=[
                {
                    "title": f"補強 {disclosure_code} 量化揭露",
                    "recommendation": "補充數值、單位、年度、組織邊界、計算方法與資料來源，並明確標示報告頁碼。",
                    "term": "short",
                    "priority": 1,
                },
                {
                    "title": f"建立 {disclosure_code} 內控資料流程",
                    "recommendation": "將溫室氣體盤查資料來源、審核責任與版本紀錄制度化，以利年度報告一致揭露。",
                    "term": "medium",
                    "priority": 2,
                },
            ]
        )
