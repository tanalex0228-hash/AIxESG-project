from django.db import models


class IndustryCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class BenchmarkCompany(models.Model):
    name = models.CharField(max_length=255)
    industry = models.ForeignKey(IndustryCategory, on_delete=models.SET_NULL, null=True, blank=True)
    stock_code = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BenchmarkReport(models.Model):
    company = models.ForeignKey(BenchmarkCompany, on_delete=models.CASCADE, related_name="reports")
    report_year = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="benchmark_reports/", blank=True)
    source_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "report_year", "title")

    def __str__(self):
        return f"{self.company} {self.report_year}"


class BenchmarkDisclosure(models.Model):
    report = models.ForeignKey(BenchmarkReport, on_delete=models.CASCADE, related_name="disclosures")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    summary = models.TextField()
    quoted_text = models.TextField(blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    quality_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report} {self.disclosure_code}"


class BenchmarkBestPractice(models.Model):
    company = models.ForeignKey(BenchmarkCompany, on_delete=models.CASCADE, related_name="best_practices")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    example_text = models.TextField(blank=True)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["disclosure_code", "priority"]

    def __str__(self):
        return self.title
