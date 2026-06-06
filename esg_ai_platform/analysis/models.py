from django.db import models

from reports.models import AnalysisJob, Report, ReportChunk


class AnalysisResult(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="analysis_results")
    analysis_job = models.OneToOneField(
        AnalysisJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis_result",
    )
    version_number = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True, db_index=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    summary = models.TextField(blank=True)
    raw_output = models.JSONField(default=dict, blank=True)
    model_name = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=40, default="v1")
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version_number", "-analyzed_at"]
        unique_together = ("report", "version_number")

    def __str__(self):
        return f"{self.report} analysis v{self.version_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_latest and self.report_id:
            AnalysisResult.objects.filter(report_id=self.report_id, is_latest=True).exclude(pk=self.pk).update(is_latest=False)
            Report.objects.filter(pk=self.report_id).update(latest_analysis_result=self)


class DisclosureScore(models.Model):
    STATUS_CHOICES = [
        ("complete", "Complete"),
        ("partial", "Partial"),
        ("missing", "Missing"),
    ]
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="disclosure_scores")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="missing")
    raw_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    weight_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    summary = models.TextField(blank=True)
    agent_output = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("analysis_result", "disclosure_code")
        ordering = ["disclosure_code"]


class MissingItem(models.Model):
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="missing_items")
    disclosure_score = models.ForeignKey(DisclosureScore, on_delete=models.CASCADE, related_name="missing_items", null=True, blank=True)
    disclosure_code = models.CharField(max_length=40, db_index=True)
    item_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=40, default="medium")
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["priority", "disclosure_code"]


class EvidenceCitation(models.Model):
    EVIDENCE_TYPES = [
        ("text", "Text"),
        ("table", "Table"),
        ("ocr", "OCR"),
        ("inferred", "Inferred"),
    ]
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="evidence_citations")
    disclosure_score = models.ForeignKey(DisclosureScore, on_delete=models.CASCADE, related_name="evidence_citations", null=True, blank=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="evidence_citations")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    page_number = models.PositiveIntegerField()
    quoted_text = models.TextField()
    normalized_finding = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    source_chunk = models.ForeignKey(ReportChunk, on_delete=models.SET_NULL, null=True, blank=True)
    start_char = models.PositiveIntegerField(null=True, blank=True)
    end_char = models.PositiveIntegerField(null=True, blank=True)
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default="text")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["disclosure_code", "page_number"]


class ImprovementRecommendation(models.Model):
    TERM_CHOICES = [
        ("short", "Short Term"),
        ("medium", "Medium Term"),
        ("long", "Long Term"),
    ]
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="recommendations")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=255)
    recommendation = models.TextField()
    term = models.CharField(max_length=20, choices=TERM_CHOICES, default="short")
    priority = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "term"]


class GeneratedReport(models.Model):
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="generated_reports")
    file = models.FileField(upload_to="generated_reports/")
    html_snapshot = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.file)


class AIUsageLog(models.Model):
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True)
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.CharField(max_length=40, default="openai")
    model = models.CharField(max_length=80)
    operation = models.CharField(max_length=80)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
