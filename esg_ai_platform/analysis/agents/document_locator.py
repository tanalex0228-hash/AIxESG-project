from .base import AgentResult, BaseAgent


class DocumentLocatorAgent(BaseAgent):
    name = "document_locator"

    KEYWORDS = {
        "305-1": ["scope 1", "範疇一", "直接溫室氣體"],
        "305-2": ["scope 2", "範疇二", "能源間接"],
        "305-3": ["scope 3", "範疇三", "其他間接"],
        "305-4": ["排放密集度", "intensity"],
        "305-5": ["減量", "reduction"],
    }

    def run(self, report, disclosure_code):
        keywords = self.KEYWORDS.get(disclosure_code, [])
        matches = []
        for chunk in report.chunks.all():
            text_lower = chunk.chunk_text.lower()
            if any(keyword.lower() in text_lower for keyword in keywords):
                matches.append(
                    {
                        "page_number": chunk.page_start,
                        "quoted_text": chunk.chunk_text[:900],
                        "confidence": 0.82,
                        "chunk_id": chunk.id,
                    }
                )
        return AgentResult(matches=matches[:5], confidence=0.82 if matches else 0.25)
