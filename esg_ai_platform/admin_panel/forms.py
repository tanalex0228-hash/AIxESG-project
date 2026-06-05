from django import forms

from benchmarks.models import BenchmarkBestPractice, BenchmarkCompany
from gri.models import GRICheckItem, GRIDisclosure, ScoringRule, ScoringWeight


class GRIDisclosureForm(forms.ModelForm):
    class Meta:
        model = GRIDisclosure
        fields = [
            "standard",
            "disclosure_code",
            "disclosure_name",
            "description",
            "required_keywords",
            "required_data_points",
            "scoring_logic",
            "weight",
            "version",
            "is_active",
        ]


class GRICheckItemForm(forms.ModelForm):
    class Meta:
        model = GRICheckItem
        fields = ["disclosure", "name", "description", "keywords", "data_points", "is_required", "sort_order", "is_active"]


class ScoringWeightForm(forms.ModelForm):
    class Meta:
        model = ScoringWeight
        fields = ["disclosure", "weight_percent", "effective_from", "is_active"]


class ScoringRuleForm(forms.ModelForm):
    class Meta:
        model = ScoringRule
        fields = ["disclosure", "rule_version", "name", "logic", "score_when_missing", "score_when_partial", "score_when_complete", "is_active"]


class BenchmarkCompanyForm(forms.ModelForm):
    class Meta:
        model = BenchmarkCompany
        fields = ["name", "industry", "stock_code", "website", "notes", "is_active"]


class BenchmarkBestPracticeForm(forms.ModelForm):
    class Meta:
        model = BenchmarkBestPractice
        fields = ["company", "disclosure_code", "title", "description", "example_text", "priority", "is_active"]
