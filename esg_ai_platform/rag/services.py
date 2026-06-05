import hashlib
import math
import time

from django.conf import settings

from reports.models import ReportChunk

from .models import CitationSource, Embedding, RetrievalLog, VectorChunk, VectorDocument


def _deterministic_embedding(text, dimensions=3072):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for index in range(dimensions):
        byte = digest[index % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    norm = math.sqrt(sum(value * value for value in values)) or 1
    return [value / norm for value in values]


def _embedding_for_text(text):
    dimensions = 3072
    if settings.OPENAI_API_KEY:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(model=settings.OPENAI_EMBEDDING_MODEL, input=text)
        vector = response.data[0].embedding
        if len(vector) != dimensions:
            vector = vector[:dimensions] if len(vector) > dimensions else vector + [0.0] * (dimensions - len(vector))
        return vector
    return _deterministic_embedding(text, dimensions)


def create_report_vector_records(report):
    document, _ = VectorDocument.objects.get_or_create(
        source_type="report",
        source_id=str(report.id),
        defaults={"title": str(report), "report": report},
    )
    created = 0
    for chunk in report.chunks.all():
        vector_chunk, was_created = VectorChunk.objects.get_or_create(
            document=document,
            report_chunk=chunk,
            defaults={
                "chunk_text": chunk.chunk_text,
                "page_number": chunk.page_start,
                "section_title": chunk.section_title,
                "metadata": {"chunk_type": chunk.chunk_type},
            },
        )
        if was_created:
            created += 1
        Embedding.objects.update_or_create(
            vector_chunk=vector_chunk,
            defaults={
                "model": settings.OPENAI_EMBEDDING_MODEL if settings.OPENAI_API_KEY else "deterministic-local",
                "dimensions": 3072,
                "vector": _embedding_for_text(chunk.chunk_text),
                "token_count": chunk.token_count,
            },
        )
        chunk.embedding_status = "embedded"
        chunk.save(update_fields=["embedding_status"])
    return created


def retrieve_context(report_id, disclosure_code, query, limit=6):
    started = time.monotonic()
    chunks = list(
        ReportChunk.objects.filter(report_id=report_id, chunk_text__icontains=query.split()[0] if query.split() else "")
        .order_by("page_start")[:limit]
    )
    if not chunks:
        chunks = list(ReportChunk.objects.filter(report_id=report_id).order_by("page_start")[:limit])

    log = RetrievalLog.objects.create(
        report_id=report_id,
        disclosure_code=disclosure_code,
        query=query,
        matched_chunk_ids=[chunk.id for chunk in chunks],
        latency_ms=int((time.monotonic() - started) * 1000),
        model=settings.OPENAI_EMBEDDING_MODEL,
    )
    citations = []
    for chunk in chunks:
        citations.append(
            CitationSource.objects.create(
                retrieval_log=log,
                report_id=report_id,
                disclosure_code=disclosure_code,
                page_number=chunk.page_start,
                quoted_text=chunk.chunk_text[:600],
                source_type=chunk.chunk_type,
                confidence_score=0.65,
            )
        )
    return {"matched_chunks": chunks, "citations": citations, "log": log}
