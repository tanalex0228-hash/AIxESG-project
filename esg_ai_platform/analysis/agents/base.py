from django.conf import settings


class AgentResult(dict):
    pass


class BaseAgent:
    name = "base"

    def model_name(self):
        return settings.OPENAI_ANALYSIS_MODEL if settings.OPENAI_API_KEY else "mock-local"
