from django.contrib import admin

from .models import (
    AIUsageLog,
    AnalysisResult,
    DisclosureScore,
    EvidenceCitation,
    GeneratedReport,
    ImprovementRecommendation,
    MissingItem,
)

admin.site.register(AnalysisResult)
admin.site.register(DisclosureScore)
admin.site.register(MissingItem)
admin.site.register(EvidenceCitation)
admin.site.register(ImprovementRecommendation)
admin.site.register(GeneratedReport)
admin.site.register(AIUsageLog)
