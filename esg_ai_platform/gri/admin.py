from django.contrib import admin

from .models import (
    GRICheckItem,
    GRIDisclosure,
    GRIStandard,
    RegulationChunk,
    RegulationDocument,
    RuleVersion,
    ScoringRule,
    ScoringWeight,
)

admin.site.register(GRIStandard)
admin.site.register(GRIDisclosure)
admin.site.register(GRICheckItem)
admin.site.register(ScoringRule)
admin.site.register(ScoringWeight)
admin.site.register(RuleVersion)
admin.site.register(RegulationDocument)
admin.site.register(RegulationChunk)
