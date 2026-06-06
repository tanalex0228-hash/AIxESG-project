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

### Module: Docker Deployment

- Completed: Added Dockerfile, production environment example, and a Docker-only deploy script that does not require Docker Compose.
- Tests: Pending server-side build and deployment on `financial-lab`.
- Fixes: Chose pure Docker deployment because the target server has Docker but does not have `docker compose`, and sudo requires a password.
- Notes: Deployment target is reachable by SSH at `alex@100.72.157.21`.

### Module: Public Fallback Deployment

- Completed: Added `CELERY_TASK_ALWAYS_EAGER` environment support for temporary public deployments where Docker/Redis permissions are not available yet.
- Tests: Pending remote runtime verification.
- Fixes: Docker deployment was blocked because `alex` cannot access `/var/run/docker.sock` without sudo.
- Notes: Temporary public deployment can run Gunicorn with SQLite and eager Celery tasks, then expose it with Tailscale Funnel.

### Module: Public CSRF Configuration

- Completed: Added environment-driven `CSRF_TRUSTED_ORIGINS` support for public IP/port deployments.
- Tests: Pending public login form POST verification.
- Fixes: Public deployment reached Django but failed form submission with CSRF 403 because `http://140.136.134.141:8010` was not trusted.

## 2026-06-06

### Module: GRI 305 Knowledge Base Integration

- Completed: Added formal GRI rule, scoring weight, and required-field models; added structured benchmark GRI 305 and gold-standard models; copied the provided Markdown knowledge base into `knowledge_base/`.
- Tests: `makemigrations`, `migrate`, knowledge-base import, 桓達企業 smoke pipeline, `ruff check .`, `mypy .`, `manage.py check`, `manage.py test --noinput`, PostgreSQL connection, Redis ping, Django runserver, and Celery worker startup passed.
- Fixes: Replaced GPT/agent-derived scoring entry point with a deterministic rule-engine wrapper while preserving the existing `run_gri_305_analysis(report)` interface; expanded Scope 3 category keyword matching for underscore-style benchmark fields.
- Notes: The official 桓達 PDF is not present in the workspace, so the smoke script generates a named 桓達企業 test PDF for pipeline validation.

### Module: Apple-Inspired SaaS Frontend Refresh

- Completed: Reworked shared navigation, dashboard, auth, report, upload, and admin templates into a cleaner Apple-inspired SaaS visual system with glass navigation, restrained panels, metric cards, pill controls, and consistent table/form styling.
- Tests: `manage.py check`, `ruff check .`, `mypy .`, `collectstatic --noinput`, `manage.py test --noinput`, and Django route smoke tests for login, registration, static CSS, dashboard, report list, upload redirect, and admin panel passed.
- Fixes: Applied visual styling through shared CSS and per-page structure so the refresh is not limited to a single page.
- Notes: The design direction adapts the provided Apple reference into an operational ESG SaaS interface instead of copying consumer-product page markup.

### Module: Product Intro, Upload UX, and LLM Feedback

- Completed: Added a public AIxESG product intro page, changed the brand link to that page, improved system-admin PDF upload testing flow, added upload-block messaging for non-enterprise users, and surfaced management feedback, benchmark gaps, risks, and 90-day recommendations on report detail pages.
- Tests: `manage.py check`, `ruff check .`, `mypy .`, `collectstatic --noinput`, `manage.py test --noinput`, 桓達企業 smoke pipeline, LLM feedback normalization check, and route smoke tests for `/intro/`, `/login/`, `/reports/upload/`, and `/` passed.
- Fixes: System administrators without a default organization can now choose or create a test company on the upload page instead of being silently redirected; LLM feedback rating is normalized to A/B/C/D for stable UI display.
- Notes: LLM management feedback uses OpenAI when `OPENAI_API_KEY` exists and deterministic rule-engine fallback otherwise.

### Module: Report History, Loading Status, and Company Comparison

- Completed: Fixed report list/detail access for system admins and public individual viewers, added an upload analysis status page with polling and completion actions, added report status JSON endpoint, added company/report GRI 305 missing-field comparison matrix, CSV export, and dashboard recent-missing summary.
- Tests: `manage.py check`, `ruff check .`, `mypy .`, `collectstatic --noinput`, `manage.py test --noinput`, 桓達企業 smoke pipeline, and route smoke tests for reports list/detail/status/status JSON/compare/CSV passed.
- Fixes: Report history no longer appears empty for system admins; report detail no longer 404s when a system admin opens analyzed reports from dashboard history; upload flow redirects to a progress page instead of leaving the browser on a long-running request.
- Notes: Comparison rows are generated from active GRI required fields and each selected report's stored missing-item records.

### Module: Scoring Quality, Downloads, Filters, and Ranking

- Completed: Scoped GRI field detection to disclosure-specific text windows, added richer field-specific recommendations, added protected downloads for original company PDFs and generated AIxESG reports, added company/year/status filters, added ESG report ranking page, and expanded the generated PDF report with management feedback and benchmark gaps.
- Tests: `manage.py check`, `ruff check .`, `mypy .`, `collectstatic --noinput`, `manage.py test --noinput`, score-variance shell check, 桓達企業 smoke pipeline, and route smoke tests for ranking/original PDF/generated PDF downloads passed.
- Fixes: Different reports no longer collapse into identical scores under the rule engine; generic “請補充...” recommendations were replaced with concrete disclosure value and action guidance per field.
- Notes: Uploaded company PDFs are already stored through `ReportFile.pdf_file`; downloads now go through permission-checked Django views rather than direct media URLs.

### Module: Reanalysis Versions and Comparison Evidence

- Completed: Added report reanalysis without re-uploading PDFs; converted analysis jobs/results to versioned history while keeping `Report.latest_analysis_job` and `Report.latest_analysis_result` as the current view; added a protected reanalysis action on report detail pages; added analysis version history; added comparison matrix hover/value context from rule-engine field evidence.
- Tests: `makemigrations --check --dry-run`, `manage.py migrate`, `manage.py check`, `ruff check .`, `mypy .`, `collectstatic --noinput`, and `manage.py test --noinput` passed with 22 tests.
- Fixes: Previous `AnalysisResult` records are no longer overwritten by the rule engine; reanalysis creates a new `AnalysisJob` and a new `AnalysisResult` version, and individual public viewers cannot reanalyze reports they only have read access to.
- Notes: Reanalysis reuses existing parsed pages, chunks, and embeddings when present, and automatically fills missing parse/OCR/embedding steps before running the latest GRI 305 rule engine.
