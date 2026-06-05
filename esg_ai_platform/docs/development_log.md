# Development Log

## 2026-06-05

### Module: Project Scaffold

- Completed: Created Django project structure with config, apps, templates, static files, media folders, scripts, and environment examples.
- Tests: `python3 -m compileall esg_ai_platform` passed on the available Python 3.9 interpreter.
- Fixes: Removed generated `.DS_Store`, `.venv`, and `__pycache__` artifacts after checks.
- Notes: Full Django runtime review is blocked until Python 3.11+ is available.

### Module: Domain Models

- Completed: Added organization, account role, report, GRI, benchmark, RAG, and analysis models.
- Tests: Syntax/import compilation passed.
- Fixes: Added safer reverse one-to-one access in dashboard and report detail views.
- Notes: Migrations still need generation and execution in a Python 3.11+ environment with PostgreSQL and pgvector.

### Module: PDF Pipeline

- Completed: Implemented PDF parsing with PyMuPDF, page text extraction, low-text page image extraction, chunking, OCR job records, and Tesseract OCR processing.
- Tests: Syntax compilation passed.
- Fixes: Replaced OCR extension placeholder with actual `pytesseract.image_to_string` flow.
- Notes: Runtime OCR validation requires the `tesseract` binary and language packs.

### Module: RAG and Embeddings

- Completed: Added vector document/chunk records and embedding creation using OpenAI when configured, with deterministic local fallback for development.
- Tests: Syntax compilation passed.
- Fixes: Replaced vector-record-only implementation with `Embedding` rows.
- Notes: pgvector similarity search still requires PostgreSQL + pgvector runtime validation.

### Module: Seed Data

- Completed: Added GRI 305 seed script and benchmark sample seed script.
- Tests: Syntax compilation passed.
- Fixes: Reworded benchmark data from placeholder language to explicit sample data.

### Module: Engineering Governance

- Completed: Added this development log and adopted a progress report requirement for subsequent stops.
- Tests: Repository status check showed the workspace was not a git repository.
- Fixes: Pending git initialization and feature commits.
- Notes: Commit discipline can begin once a repository is initialized.

### Module: Runtime Enablement

- Completed: Installed Python 3.11, Tesseract, Tesseract language packs, Redis, PostgreSQL 17, and pgvector via Homebrew.
- Tests: `ruff check`, `mypy`, `manage.py check`, `manage.py migrate`, seed scripts, Redis ping, pgvector extension query, Django runserver smoke test, and Celery worker startup passed.
- Fixes: Switched from PostgreSQL 16 to PostgreSQL 17 because Homebrew pgvector 0.8.2 ships extension files for PostgreSQL 17/18.
- Notes: Added `VectorExtension()` to `rag/migrations/0001_initial.py` so test databases also enable pgvector automatically.

### Module: End-to-End Smoke Pipeline

- Completed: Added and ran `scripts/smoke_pipeline.py`, which generates a sample PDF and executes parse, optional OCR, chunking, embedding, GRI analysis, and PDF report generation.
- Tests: Smoke output reported 1 page, 1 chunk, 5 disclosure scores, 3 citations, and `generated_reports/gri_305_analysis_1.pdf`.
- Fixes: Added deterministic local embeddings so the RAG pipeline can create `Embedding` rows without an OpenAI key.
- Notes: This validates the local fallback pipeline; production AI quality still requires model prompt implementation and an OpenAI API key.

### Module: Account Registration and Access Governance

- Completed: Added registration for individual, enterprise, and system administrator accounts; separated account-type identity data into dedicated profile tables; added encrypted backup phone/email storage; added operation logging middleware.
- Tests: `ruff check`, `mypy`, `manage.py check`, `manage.py test --noinput` passed with 9 tests.
- Fixes: Restricted system rule/admin-panel access to system administrators instead of organization admins; updated tests to reflect this security boundary.
- Notes: System administrator self-registration requires `SYSTEM_ADMIN_REGISTRATION_CODE`.

### Module: Visual Styling and Static Assets

- Completed: Verified all standard web templates extend `base.html`; enhanced shared CSS for forms, error states, metrics, tables, mobile layout, and registration fields.
- Tests: `collectstatic --noinput` passed; runserver smoke returned 200 for `/accounts/register/`, `/login/`, `/static/css/app.css`, and `/static/js/dashboard.js`.
- Fixes: Re-ran collectstatic after CSS changes so local staticfiles are current.
- Notes: The PDF template intentionally uses inline CSS for WeasyPrint rendering.
