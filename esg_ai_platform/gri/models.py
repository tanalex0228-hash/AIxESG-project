from django.db import models


class GRIStandard(models.Model):
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=40, default="2021")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("code", "version")

    def __str__(self):
        return f"{self.code} {self.name}"


class GRIDisclosure(models.Model):
    standard = models.ForeignKey(GRIStandard, on_delete=models.CASCADE, related_name="disclosures")
    disclosure_code = models.CharField(max_length=40, db_index=True)
    disclosure_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    required_keywords = models.JSONField(default=list, blank=True)
    required_data_points = models.JSONField(default=list, blank=True)
    scoring_logic = models.TextField(blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    version = models.CharField(max_length=40, default="2021")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("disclosure_code", "version")
        ordering = ["disclosure_code"]

    def __str__(self):
        return f"{self.disclosure_code} {self.disclosure_name}"


class GRICheckItem(models.Model):
    disclosure = models.ForeignKey(GRIDisclosure, on_delete=models.CASCADE, related_name="check_items")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)
    data_points = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["disclosure__disclosure_code", "sort_order"]

    def __str__(self):
        return f"{self.disclosure.disclosure_code}: {self.name}"


class RuleVersion(models.Model):
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} {self.version}"


class ScoringRule(models.Model):
    disclosure = models.ForeignKey(GRIDisclosure, on_delete=models.CASCADE, related_name="scoring_rules")
    rule_version = models.ForeignKey(RuleVersion, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=160)
    logic = models.TextField()
    score_when_missing = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    score_when_partial = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    score_when_complete = models.DecimalField(max_digits=4, decimal_places=2, default=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.disclosure.disclosure_code} {self.name}"


class ScoringWeight(models.Model):
    disclosure = models.OneToOneField(GRIDisclosure, on_delete=models.CASCADE, related_name="scoring_weight")
    weight_percent = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.disclosure.disclosure_code}: {self.weight_percent}%"


class RegulationDocument(models.Model):
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=40, default="markdown")
    file = models.FileField(upload_to="regulations/", blank=True)
    body = models.TextField(blank=True)
    version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RegulationChunk(models.Model):
    document = models.ForeignKey(RegulationDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_text = models.TextField()
    section_title = models.CharField(max_length=255, blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    embedding_status = models.CharField(max_length=40, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)


class GRIDisclosureRule(models.Model):
    disclosure_code = models.CharField(max_length=40, db_index=True)
    rule_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    official_requirement = models.TextField(blank=True)
    source_document = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=40, default="GRI 305:2016")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gri_disclosure_rules"
        unique_together = ("disclosure_code", "version")
        ordering = ["disclosure_code"]

    def __str__(self):
        return f"{self.disclosure_code} {self.rule_name}"


class GRIScoringWeight(models.Model):
    disclosure_code = models.CharField(max_length=40, db_index=True)
    field_key = models.CharField(max_length=120)
    field_label = models.CharField(max_length=255)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gri_scoring_weights"
        unique_together = ("disclosure_code", "field_key")
        ordering = ["disclosure_code", "sort_order"]

    def __str__(self):
        return f"{self.disclosure_code} {self.field_label}: {self.max_score}"


class GRIRequiredField(models.Model):
    SEVERITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    disclosure_code = models.CharField(max_length=40, db_index=True)
    field_key = models.CharField(max_length=120)
    field_label = models.CharField(max_length=255)
    source_clause = models.CharField(max_length=120, blank=True)
    requirement_type = models.CharField(max_length=80, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    patterns = models.JSONField(default=list, blank=True)
    recommendation_template = models.TextField(blank=True)
    severity = models.CharField(max_length=40, choices=SEVERITY_CHOICES, default="medium")
    is_critical = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gri_required_fields"
        unique_together = ("disclosure_code", "field_key")
        ordering = ["disclosure_code", "sort_order"]

    def __str__(self):
        return f"{self.disclosure_code} {self.field_label}"
