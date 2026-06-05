from django.db import models
from pgvector.django import VectorField

from reports.models import Report, ReportChunk


class VectorDocument(models.Model):
    SOURCE_TYPES = [
        ("gri", "GRI"),
        ("benchmark", "Benchmark"),
        ("report", "User Report"),
        ("regulation", "Regulation"),
    ]
    source_type = models.CharField(max_length=40, choices=SOURCE_TYPES, db_index=True)
    title = models.CharField(max_length=255)
    source_id = models.CharField(max_length=120, blank=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True, related_name="vector_documents")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_type}: {self.title}"


class VectorChunk(models.Model):
    document = models.ForeignKey(VectorDocument, on_delete=models.CASCADE, related_name="chunks")
    report_chunk = models.OneToOneField(ReportChunk, on_delete=models.SET_NULL, null=True, blank=True)
    chunk_text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Embedding(models.Model):
    vector_chunk = models.OneToOneField(VectorChunk, on_delete=models.CASCADE, related_name="embedding")
    model = models.CharField(max_length=80)
    dimensions = models.PositiveIntegerField(default=3072)
    vector = VectorField(dimensions=3072)
    token_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class RetrievalLog(models.Model):
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True)
    disclosure_code = models.CharField(max_length=40, blank=True)
    query = models.TextField()
    matched_chunk_ids = models.JSONField(default=list, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    model = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CitationSource(models.Model):
    retrieval_log = models.ForeignKey(RetrievalLog, on_delete=models.CASCADE, related_name="citations", null=True, blank=True)
    vector_chunk = models.ForeignKey(VectorChunk, on_delete=models.SET_NULL, null=True, blank=True)
    report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True)
    disclosure_code = models.CharField(max_length=40, blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    quoted_text = models.TextField(blank=True)
    source_type = models.CharField(max_length=40, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
