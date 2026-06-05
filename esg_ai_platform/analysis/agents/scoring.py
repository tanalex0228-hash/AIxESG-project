from decimal import Decimal

from .base import AgentResult, BaseAgent


class ScoringAgent(BaseAgent):
    name = "scoring"

    def run(self, disclosure, check_result, quantitative):
        raw_score = Decimal(str(check_result["raw_score"]))
        if check_result["status"] == "complete" and quantitative["completeness"] < 0.5:
            raw_score = Decimal("1")
        try:
            weight = disclosure.scoring_weight
        except Exception:
            weight = None
        weight_percent = Decimal(str(weight.weight_percent if weight else disclosure.weight))
        weighted_score = (raw_score / Decimal("2")) * weight_percent
        return AgentResult(
            raw_score=float(raw_score),
            weighted_score=float(weighted_score),
            weight_percent=float(weight_percent),
            status="complete" if raw_score >= 2 else "partial" if raw_score >= 1 else "missing",
        )
