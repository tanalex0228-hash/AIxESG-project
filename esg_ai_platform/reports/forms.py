from django import forms
from django.utils.text import get_valid_filename

from .models import Report, ReportFile, validate_pdf
from .services.industry_classification import normalize_report_industry


class ReportUploadForm(forms.ModelForm):
    pdf_file = forms.FileField(validators=[validate_pdf], label="PDF 檔案")

    class Meta:
        model = Report
        fields = ["company_code", "company_name", "report_year", "title", "industry_category", "notes"]
        labels = {
            "company_code": "公司代號",
            "company_name": "公司名稱",
            "report_year": "報告年度",
            "title": "報告書標題",
            "industry_category": "產業分類",
            "notes": "備註",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data["pdf_file"]
        pdf_file.name = get_valid_filename(pdf_file.name)
        return pdf_file

    def save_with_file(self, organization, user):
        pdf_file = self.cleaned_data["pdf_file"]
        report = self.save(commit=False)
        report.organization = organization
        report.uploaded_by = user
        normalize_report_industry(report, save=False)
        report.save()
        ReportFile.objects.create(
            report=report,
            pdf_file=pdf_file,
            original_filename=pdf_file.name,
            file_size=pdf_file.size,
        )
        return report
