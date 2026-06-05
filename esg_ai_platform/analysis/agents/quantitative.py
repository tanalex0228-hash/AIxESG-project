import re

from .base import AgentResult, BaseAgent


class QuantitativeCompletenessAgent(BaseAgent):
    name = "quantitative_completeness"

    REQUIRED_SIGNALS = ["tco2e", "噸", "年度", "scope", "範疇", "gwp", "基準", "%"]

    def run(self, matches):
        text = "\n".join(item.get("quoted_text", "") for item in matches)
        has_number = bool(re.search(r"\d[\d,]*(\.\d+)?", text))
        found = [signal for signal in self.REQUIRED_SIGNALS if signal.lower() in text.lower()]
        return AgentResult(has_number=has_number, found_signals=found, completeness=min(1, (len(found) + int(has_number)) / 6))
