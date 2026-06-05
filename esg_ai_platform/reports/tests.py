from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from accounts.models import Role, UserOrganizationRole
from organizations.models import Organization
from reports.forms import ReportUploadForm
from reports.models import AnalysisJob, Report


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ReportUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="uploader", password="pass")
        self.organization = Organization.objects.create(name="Tenant A")
        role = Role.objects.create(code=Role.ANALYST, name="Analyst")
        UserOrganizationRole.objects.create(user=self.user, organization=self.organization, role=role)

    def test_pdf_upload_form_creates_report_and_file_record(self):
        uploaded = SimpleUploadedFile("report.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")
        form = ReportUploadForm(
            data={
                "company_name": "Tenant A",
                "report_year": 2025,
                "title": "2025 Sustainability Report",
                "industry_category": "Electronics",
                "notes": "test",
            },
            files=MultiValueDict({"pdf_file": [uploaded]}),
        )

        self.assertTrue(form.is_valid(), form.errors)
        report = form.save_with_file(self.organization, self.user)
        AnalysisJob.objects.create(report=report)

        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(report.file_record.original_filename, "report.pdf")
        self.assertEqual(report.organization, self.organization)

    def test_non_pdf_upload_is_rejected(self):
        uploaded = SimpleUploadedFile("report.txt", BytesIO(b"not pdf").read(), content_type="text/plain")
        form = ReportUploadForm(
            data={
                "company_name": "Tenant A",
                "report_year": 2025,
                "title": "Text File",
                "industry_category": "Electronics",
            },
            files=MultiValueDict({"pdf_file": [uploaded]}),
        )

        self.assertFalse(form.is_valid())
