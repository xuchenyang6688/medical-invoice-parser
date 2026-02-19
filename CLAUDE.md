# CLAUDE.md — Project Context for Claude Code

## Project Summary

Medical Invoice PDF Parser — a web app that parses Chinese medical electronic invoices (中国医疗电子票据) from PDF into structured JSON. Personal learning demo project.

**Pipeline:** PDF → MinerU (cloud API) → content_list_v2.json → Zhipu GLM (LLM structuring) → JSON

## Tech Stack

- **Frontend:** React 18 + Vite (port 5173)
- **Backend:** FastAPI + Python 3.10 (port 8000)
- **PDF Parsing:** MinerU Online API (mineru.net)
- **Data Structuring:** Zhipu GLM API (glm-4-flash)
- **Environment:** Conda (`medical-invoice-parser`), NOT venv

## How to Run

```bash
# Backend
conda activate medical-invoice-parser
cd backend
python -m uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
npm run dev
```

## Key Files

```
backend/
  main.py                    # FastAPI entry point, CORS config
  routers/convert.py         # POST /convert + debug endpoints
  services/mineru_api.py     # MinerU API client (upload → poll → extract)
  services/zhipu_structurer.py  # Zhipu GLM prompt + JSON parsing
  models/invoice.py          # Pydantic InvoiceData (English fields + Chinese aliases)
  .env                       # API keys (NEVER commit)

frontend/
  src/App.jsx                # Main component, orchestrates UI flow
  src/services/api.js        # POST /convert API client
  src/components/            # FileUpload, ConvertButton, ProgressBar, JsonViewer
```

## Conventions

- **Commits:** Conventional commit messages (`feat:`, `fix:`, etc.)
- **Pydantic models:** English field names + Chinese aliases via `Field(alias=...)` + `ConfigDict(populate_by_name=True)`
- **API responses:** Serialized with `by_alias=True` (Chinese keys for frontend)
- **Python environment:** Always use conda, never venv
- **Git:** Exclude `backend/test/` (local test data)

## Architecture Notes

- **MinerU extraction uses `content_list_v2.json`**, NOT markdown — markdown drops `page_footer` blocks which contain `收款单位` (hospital name)
- **`_flatten_content_list()`** converts the nested JSON structure into plain text for GLM
- **Zhipu SDK is sync** — wrapped with `asyncio.to_thread()` for async FastAPI compatibility
- **Batch-first:** `parse_pdfs_batch()` is the core function; `parse_pdf()` is a wrapper
- **Debug endpoints** (`/debug/mineru`, `/debug/zhipu`, `/debug/extract-result/{batch_id}`, `/debug/extract-zip`) allow testing each pipeline stage in isolation

## Known Quirks

- MinerU polling takes **10+ minutes** per invoice (MINERU_POLL_INTERVAL=60s, MINERU_POLL_TIMEOUT=1200s)
- MinerU API: the `state` field is on each entry inside `data.extract_result[]`, NOT on the `data` object itself — a past bug read it from the wrong level causing polling to always timeout
- `zhipuai` SDK requires `sniffio` which isn't auto-installed — install manually if missing
- MinerU API response field is `extract_result` (singular, no 's')
- GLM system messages can cause inconsistent results — currently commented out, user prompt alone works better

## Current Status

- **Phase 1 (MinerU Online API):** Steps 1-5 complete, Step 6 (end-to-end testing) remaining
- **Phase 2 (Self-deployed MinerU on Kaggle):** Not started
