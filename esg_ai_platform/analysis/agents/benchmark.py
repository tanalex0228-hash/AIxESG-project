from benchmarks.models import BenchmarkBestPractice

from .base import AgentResult, BaseAgent


class BenchmarkAgent(BaseAgent):
    name = "benchmark"

    def run(self, disclosure_code):
        practices = BenchmarkBestPractice.objects.filter(disclosure_code=disclosure_code, is_active=True)[:3]
        return AgentResult(
            examples=[
                {"company": item.company.name, "title": item.title, "description": item.description}
                for item in practices
            ]
        )
