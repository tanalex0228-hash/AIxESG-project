from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from organizations.models import Organization

REPORT_STATUS_CHOICES = [
    ("uploaded", "Uploaded"),
    ("parsing", "Parsing"),
    ("ocr_processing", "OCR Processing"),
    ("embedding", "Embedding"),
    ("retrieving", "Retrieving"),
    ("analyzing", "Analyzing"),
    ("scoring", "Scoring"),
    ("generating_pdf", "Generating PDF"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]


def validate_pdf(file):
    if not file.name.lower().endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed.")
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(f"File must be smaller than {settings.MAX_UPLOAD_SIZE_MB} MB.")


class Report(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="reports")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    company_name = models.CharField(max_length=255)
    report_year = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    industry_category = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=40, choices=REPORT_STATUS_CHOICES, default="uploaded", db_index=True)
    latest_analysis_job = models.ForeignKey(
        "AnalysisJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    latest_analysis_result = models.ForeignKey(
        "analysis.AnalysisResult",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    total_pages = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=20, default="zh-Hant")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} {self.report_year}"

    @property
    def analysis_job(self):
        if self.latest_analysis_job_id:
            return self.latest_analysis_job
        return self.analysis_jobs.order_by("-created_at").first()

    @property
    def analysis_result(self):
        if self.latest_analysis_result_id:
            return self.latest_analysis_result
        return self.analysis_results.order_by("-version_number", "-analyzed_at").first()


class ReportFile(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name="file_record")
    pdf_file = models.FileField(upload_to="uploaded_reports/", validators=[validate_pdf])
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_filename


class ReportPage(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveIntegerField()
    raw_text = models.TextField(blank=True)
    ocr_text = models.TextField(blank=True)
    final_text = models.TextField(blank=True)
    extraction_method = models.CharField(max_length=40, default="pymupdf")
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    needs_ocr = models.BooleanField(default=False)
    image_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("report", "page_number")
        ordering = ["report", "page_number"]

    def __str__(self):
        return f"{self.report} p.{self.page_number}"


class ReportChunk(models.Model):
    CHUNK_TYPES = [
        ("paragraph", "Paragraph"),
        ("table", "Table"),
        ("section", "Section"),
        ("ocr", "OCR"),
    ]
    EMBEDDING_STATUS = [
        ("pending", "Pending"),
        ("embedded", "Embedded"),
        ("failed", "Failed"),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="chunks")
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()
    chunk_text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    section_title = models.CharField(max_length=255, blank=True)
    chunk_type = models.CharField(max_length=40, choices=CHUNK_TYPES, default="paragraph")
    embedding_status = models.CharField(max_length=40, choices=EMBEDDING_STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["report", "page_start", "id"]

    def __str__(self):
        return f"{self.report} {self.page_start}-{self.page_end}"


class ReportTable(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="tables")
    page_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True)
    raw_data = models.JSONField(default=list, blank=True)
    extracted_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class OCRJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="ocr_jobs")
    page = models.ForeignKey(ReportPage, on_delete=models.CASCADE, related_name="ocr_jobs", null=True, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="pending")
    engine = models.CharField(max_length=40, default="pytesseract")
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalysisJob(models.Model):
    PURPOSE_UPLOAD = "upload"
    PURPOSE_REANALYSIS = "reanalysis"
    PURPOSE_CHOICES = [
        (PURPOSE_UPLOAD, "Initial Upload"),
        (PURPOSE_REANALYSIS, "Reanalysis"),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="analysis_jobs")
    purpose = models.CharField(max_length=40, choices=PURPOSE_CHOICES, default=PURPOSE_UPLOAD)
    status = models.CharField(max_length=40, choices=REPORT_STATUS_CHOICES, default="uploaded", db_index=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    progress = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report", "-created_at"]),
        ]

    def mark(self, status, progress=None, error_message=""):
        self.status = status
        self.report.status = status
        self.report.latest_analysis_job = self
        if progress is not None:
            self.progress = progress
        if error_message:
            self.error_message = error_message
        self.save(update_fields=["status", "progress", "error_message", "updated_at"])
        self.report.save(update_fields=["status", "latest_analysis_job", "updated_at"])
