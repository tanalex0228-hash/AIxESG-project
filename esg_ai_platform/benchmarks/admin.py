from django.contrib import admin

from .models import BenchmarkBestPractice, BenchmarkCompany, BenchmarkDisclosure, BenchmarkReport, IndustryCategory

admin.site.register(IndustryCategory)
admin.site.register(BenchmarkCompany)
admin.site.register(BenchmarkReport)
admin.site.register(BenchmarkDisclosure)
admin.site.register(BenchmarkBestPractice)
