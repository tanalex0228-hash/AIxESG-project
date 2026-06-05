from .base import AgentResult, BaseAgent


class ReportWriterAgent(BaseAgent):
    name = "report_writer"

    def run(self, analysis_result):
        return AgentResult(
            total_score=float(analysis_result.total_score),
            confidence=float(analysis_result.confidence_score),
            summary=analysis_result.summary,
            scores=list(analysis_result.disclosure_scores.values()),
            missing_items=list(analysis_result.missing_items.values()),
            evidence=list(analysis_result.evidence_citations.values()),
            recommendations=list(analysis_result.recommendations.values()),
        )
