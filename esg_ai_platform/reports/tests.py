from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from accounts.models import Role, SystemAdminUserProfile, UserOrganizationRole, UserProfile
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

    def test_system_admin_can_open_upload_page_without_default_organization(self):
        admin = get_user_model().objects.create_user(username="sys-upload", password="pass")
        admin.is_staff = True
        admin.save(update_fields=["is_staff"])
        UserProfile.objects.create(user=admin, account_type=UserProfile.ACCOUNT_SYSTEM_ADMIN, legal_name="Admin")
        SystemAdminUserProfile.objects.create(user=admin)
        self.client.force_login(admin)

        response = self.client.get("/reports/upload/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "系統管理者測試企業")
