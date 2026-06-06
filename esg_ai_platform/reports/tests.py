from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from accounts.models import Role, SystemAdminUserProfile, UserOrganizationRole, UserProfile
from analysis.models import AnalysisResult, DisclosureScore, GeneratedReport
from gri.models import GRIRequiredField
from organizations.models import Organization
from reports.forms import ReportUploadForm
from reports.models import AnalysisJob, Report, ReportChunk, ReportFile


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

    def test_system_admin_can_list_and_open_reports_without_default_organization(self):
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Analyzed Report",
            status="completed",
        )
        AnalysisJob.objects.create(report=report, status="completed", progress=100)
        admin = get_user_model().objects.create_user(username="sys-detail", password="pass")
        admin.is_staff = True
        admin.save(update_fields=["is_staff"])
        UserProfile.objects.create(user=admin, account_type=UserProfile.ACCOUNT_SYSTEM_ADMIN, legal_name="Admin")
        SystemAdminUserProfile.objects.create(user=admin)
        self.client.force_login(admin)

        list_response = self.client.get("/reports/")
        detail_response = self.client.get(f"/reports/{report.pk}/")

        self.assertContains(list_response, "Analyzed Report")
        self.assertEqual(detail_response.status_code, 200)

    def test_upload_redirects_to_status_page(self):
        self.client.force_login(self.user)
        uploaded = SimpleUploadedFile(
            "report.pdf",
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
            content_type="application/pdf",
        )

        with patch("reports.views.parse_pdf_task.delay", return_value=SimpleNamespace(id="task-1")):
            response = self.client.post(
                "/reports/upload/",
                data={
                    "company_name": "Tenant A",
                    "report_year": 2025,
                    "title": "Upload Flow",
                    "industry_category": "Electronics",
                    "pdf_file": uploaded,
                },
            )

        report = Report.objects.get(title="Upload Flow")
        self.assertRedirects(response, f"/reports/{report.pk}/status/", fetch_redirect_response=False)

    def test_compare_page_and_csv_export_render(self):
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Compare Report",
            status="completed",
        )
        AnalysisJob.objects.create(report=report, status="completed", progress=100)
        ReportChunk.objects.create(report=report, page_start=1, page_end=1, chunk_text="Scope 1 範疇一", token_count=4)
        self.client.force_login(self.user)

        page_response = self.client.get("/reports/compare/")
        csv_response = self.client.get(f"/reports/compare/?report_ids={report.id}&export=csv")

        self.assertEqual(page_response.status_code, 200)
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response["Content-Type"])

    def test_compare_page_shows_detected_field_value_for_hover_context(self):
        GRIRequiredField.objects.create(
            disclosure_code="305-1",
            field_key="S1_Total_Emissions",
            field_label="排放總量",
            is_required=True,
            is_active=True,
        )
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Value Compare Report",
            status="completed",
        )
        result = AnalysisResult.objects.create(report=report, total_score=70, confidence_score=80)
        DisclosureScore.objects.create(
            analysis_result=result,
            disclosure_code="305-1",
            status="complete",
            agent_output={
                "field_results": [
                    {
                        "field_label": "排放總量",
                        "status": "complete",
                        "detected_value": "1,234 tCO2e",
                        "page_number": 7,
                        "evidence_excerpt": "Scope 1 排放總量為 1,234 tCO2e。",
                    }
                ]
            },
        )
        peer = Report.objects.create(
            organization=self.organization,
            company_name="Peer B",
            report_year=2025,
            title="Peer Value Compare Report",
            status="completed",
        )
        peer_result = AnalysisResult.objects.create(report=peer, total_score=88, confidence_score=80)
        DisclosureScore.objects.create(
            analysis_result=peer_result,
            disclosure_code="305-1",
            status="complete",
            agent_output={
                "field_results": [
                    {
                        "field_label": "排放總量",
                        "status": "complete",
                        "detected_value": "2,500 tCO2e",
                        "page_number": 9,
                        "evidence_excerpt": "Scope 1 排放總量為 2,500 tCO2e。",
                    }
                ]
            },
        )
        self.client.force_login(self.user)

        response = self.client.get(f"/reports/compare/?report_ids={report.id}&report_ids={peer.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "comparison-tooltip-data")
        self.assertContains(response, "1,234 tCO2e")
        self.assertContains(response, "2,500 tCO2e")
        self.assertContains(response, "Peer B 2025")
        self.assertContains(response, "data-comparison-tooltip")

    def test_download_original_and_generated_reports(self):
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Downloadable Report",
            status="completed",
        )
        ReportFile.objects.create(
            report=report,
            pdf_file=SimpleUploadedFile("original.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"),
            original_filename="original.pdf",
            file_size=14,
        )
        result = AnalysisResult.objects.create(report=report, total_score=70, confidence_score=80)
        GeneratedReport.objects.create(
            analysis_result=result,
            file=SimpleUploadedFile("analysis.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"),
        )
        self.client.force_login(self.user)

        original = self.client.get(f"/reports/{report.pk}/download/original/")
        generated = self.client.get(f"/reports/{report.pk}/download/generated/")

        self.assertEqual(original.status_code, 200)
        self.assertEqual(generated.status_code, 200)

    def test_ranking_page_orders_by_score(self):
        low = Report.objects.create(
            organization=self.organization,
            company_name="Low Co",
            report_year=2024,
            title="Low",
            status="completed",
        )
        high = Report.objects.create(
            organization=self.organization,
            company_name="High Co",
            report_year=2024,
            title="High",
            status="completed",
        )
        AnalysisResult.objects.create(report=low, total_score=55, confidence_score=80)
        AnalysisResult.objects.create(report=high, total_score=88, confidence_score=80)
        self.client.force_login(self.user)

        response = self.client.get("/reports/ranking/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "High Co")
        self.assertContains(response, "Low Co")

    def test_reanalyze_creates_new_job_and_redirects_to_status(self):
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Needs Reanalysis",
            status="completed",
        )
        AnalysisResult.objects.create(report=report, total_score=55, confidence_score=70)
        self.client.force_login(self.user)

        with patch("reports.views.reanalyze_report_task.delay", return_value=SimpleNamespace(id="task-reanalyze")):
            response = self.client.post(f"/reports/{report.pk}/reanalyze/")

        report.refresh_from_db()
        job = report.latest_analysis_job
        self.assertRedirects(response, f"/reports/{report.pk}/status/", fetch_redirect_response=False)
        self.assertEqual(job.purpose, AnalysisJob.PURPOSE_REANALYSIS)
        self.assertEqual(job.celery_task_id, "task-reanalyze")

    def test_individual_user_cannot_reanalyze_public_report(self):
        report = Report.objects.create(
            organization=self.organization,
            company_name="Tenant A",
            report_year=2025,
            title="Public Report",
            status="completed",
        )
        individual = get_user_model().objects.create_user(username="public-reader", password="pass")
        UserProfile.objects.create(user=individual, account_type=UserProfile.ACCOUNT_INDIVIDUAL, legal_name="Reader")
        self.client.force_login(individual)

        response = self.client.post(f"/reports/{report.pk}/reanalyze/")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(AnalysisJob.objects.filter(report=report, purpose=AnalysisJob.PURPOSE_REANALYSIS).exists())
