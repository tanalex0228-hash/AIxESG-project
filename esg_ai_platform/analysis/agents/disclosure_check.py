from .base import AgentResult, BaseAgent


class DisclosureCheckAgent(BaseAgent):
    name = "disclosure_check"

    def run(self, disclosure, located):
        matches = located.get("matches", [])
        if len(matches) >= 2:
            status = "complete"
            score = 2
        elif matches:
            status = "partial"
            score = 1
        else:
            status = "missing"
            score = 0
        return AgentResult(
            disclosure_code=disclosure.disclosure_code,
            status=status,
            raw_score=score,
            confidence=located.get("confidence", 0.2),
            summary=f"{disclosure.disclosure_code} {disclosure.disclosure_name} 初步判定為 {status}。",
        )
