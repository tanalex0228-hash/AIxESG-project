from django.contrib import admin

from .models import AnalysisJob, OCRJob, Report, ReportChunk, ReportFile, ReportPage, ReportTable

admin.site.register(Report)
admin.site.register(ReportFile)
admin.site.register(ReportPage)
admin.site.register(ReportChunk)
admin.site.register(ReportTable)
admin.site.register(OCRJob)
admin.site.register(AnalysisJob)
