# AI ESG 永續報告書智慧診斷系統

這是一個可擴充的 Django AI SaaS 專案骨架，用來上傳企業永續報告書 PDF，針對 GRI 305-1～305-5 進行揭露完整度診斷，保留頁碼引用、缺漏項目、同業標竿與改善建議，並產生可下載報告。

## 技術

- Python 3.11+
- Django 5.x + Django templates
- Bootstrap 5 + Chart.js
- PostgreSQL + pgvector
- Redis + Celery
- OpenAI Python SDK
- PyMuPDF / pytesseract OCR
- Jinja2 / WeasyPrint
- whitenoise / gunicorn / nginx compatible

## 安裝

```bash
cd esg_ai_platform
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## PostgreSQL + pgvector

```bash
createdb esg_ai_platform
psql esg_ai_platform -f scripts/create_pgvector_extension.sql
```

設定 `.env`：

```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/esg_ai_platform
```

## Redis

```bash
redis-server
```

## Django

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python scripts/seed_gri_305.py
python scripts/seed_benchmarks.py
python manage.py runserver
```

## Celery worker

```bash
celery -A config worker -l info
```

## OpenAI

在 `.env` 設定：

```env
OPENAI_API_KEY=sk-...
OPENAI_ANALYSIS_MODEL=gpt-4.1
OPENAI_FALLBACK_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

第一版分析服務提供 local fallback，沒有 API key 仍可跑完整流程；設定 OpenAI API key 後，`rag/services.py` 會使用 OpenAI embedding。正式 AI JSON schema prompt 可在 `analysis/agents/` 擴充。

## 使用流程

1. 建立 Organization、Role、UserProfile、UserOrganizationRole。
2. 使用者登入後上傳 PDF。
3. 系統建立 `Report` 與 `AnalysisJob`。
4. Celery pipeline 依序執行解析、OCR、向量紀錄、GRI 分析、PDF 產出。
5. Dashboard 顯示總分、分項分數、缺漏、引用來源、建議與歷史紀錄。

## Ubuntu 部署注意事項

- 安裝 PostgreSQL、pgvector、Redis、Tesseract、WeasyPrint 系統依賴。
- 使用 gunicorn 啟動 Django WSGI。
- 使用 nginx 反向代理並服務 `/static/` 與 `/media/`。
- 將 `DEBUG=False`，設定強隨機 `SECRET_KEY`、正式網域 `ALLOWED_HOSTS`。
- Celery worker 建議用 systemd 或 supervisor 管理。
- PDF 上傳檔案、AI token 成本、分析次數已預留資料欄位，可延伸 subscription 與 billing。
