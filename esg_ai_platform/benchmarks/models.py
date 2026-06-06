from django.db import models


class IndustryCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class BenchmarkCompany(models.Model):
    company_id = models.CharField(max_length=40, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    industry = models.ForeignKey(IndustryCategory, on_delete=models.SET_NULL, null=True, blank=True)
    stock_code = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "benchmark_companies"

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


class BenchmarkGri305(models.Model):
    company = models.ForeignKey(BenchmarkCompany, on_delete=models.CASCADE, related_name="gri305_records")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    indicator = models.CharField(max_length=120, db_index=True)
    field_key = models.CharField(max_length=120)
    value = models.TextField(blank=True)
    numeric_value = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=120, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    action_template = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "benchmark_gri305"
        unique_together = ("company", "year", "field_key")
        ordering = ["company__stock_code", "disclosure_code", "field_key"]

    def __str__(self):
        return f"{self.company} {self.field_key}"


class BenchmarkGoldStandard(models.Model):
    company = models.ForeignKey(BenchmarkCompany, on_delete=models.CASCADE, related_name="gold_standards")
    standard_id = models.CharField(max_length=120, db_index=True)
    target_indicator = models.CharField(max_length=120, db_index=True)
    disclosure_code = models.CharField(max_length=40, db_index=True)
    system_score_tag = models.CharField(max_length=120, blank=True)
    gold_standard_text = models.TextField()
    excellent_reason = models.TextField(blank=True)
    action_plan_template = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "benchmark_gold_standard"
        unique_together = ("company", "standard_id")
        ordering = ["disclosure_code", "standard_id"]

    def __str__(self):
        return self.standard_id
