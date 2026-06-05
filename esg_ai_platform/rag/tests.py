from django.test import TestCase

from organizations.models import Organization
from rag.models import Embedding, VectorChunk, VectorDocument
from rag.services import create_report_vector_records
from reports.models import Report, ReportChunk


class RagServiceTests(TestCase):
    def test_create_report_vector_records_creates_embedding_rows(self):
        organization = Organization.objects.create(name="Vector Tenant")
        report = Report.objects.create(
            organization=organization,
            company_name="Vector Tenant",
            report_year=2025,
            title="Report",
        )
        ReportChunk.objects.create(
            report=report,
            page_start=1,
            page_end=1,
            chunk_text="Scope 2 能源間接排放量揭露。",
            token_count=16,
        )

        created = create_report_vector_records(report)

        self.assertEqual(created, 1)
        self.assertEqual(VectorDocument.objects.count(), 1)
        self.assertEqual(VectorChunk.objects.count(), 1)
        self.assertEqual(Embedding.objects.count(), 1)
