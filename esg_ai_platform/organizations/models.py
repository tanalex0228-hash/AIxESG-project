from django.db import models


class Organization(models.Model):
    PLAN_CHOICES = [
        ("trial", "Trial"),
        ("starter", "Starter"),
        ("growth", "Growth"),
        ("enterprise", "Enterprise"),
    ]

    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=64, blank=True)
    industry_category = models.CharField(max_length=120, blank=True)
    subscription_plan = models.CharField(max_length=32, choices=PLAN_CHOICES, default="trial")
    usage_quota = models.PositiveIntegerField(default=3)
    monthly_analysis_count = models.PositiveIntegerField(default=0)
    billing_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
