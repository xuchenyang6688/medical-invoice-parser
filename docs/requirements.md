# Medical Invoice PDF Parser — Project Requirements

> **Version:** 1.0
> **Last Updated:** 2025-02-17
> **Purpose:** Personal learning demo — PDF document parsing with VLM (MinerU) + LLM structuring (Zhipu GLM)

---

## 1. Project Overview

Build a web application that parses Chinese medical electronic invoices (中国医疗电子票据) from PDF format into structured JSON data, using MinerU for document parsing and Zhipu GLM for data structuring.

### 1.1 Learning Goals

- Understand how VLM-based document parsing works (MinerU internals, pipeline vs VLM backends)
- Build a full-stack application: React frontend + Python FastAPI backend
- Practice prompt engineering for structured data extraction with an LLM (Zhipu GLM)
- Compare two integration approaches: cloud API vs self-deployed MinerU

### 1.2 Constraints

- **Zero monetary cost.** All tools/services must be free or within free tiers.
- **No local GPU.** MinerU self-deploy will run on Kaggle Notebooks (free GPU runtime).
- **Zhipu GLM API** is available for free within one month (API key already obtained).
- **MinerU Online API** is free during beta (requires application and approval at mineru.net).

---

## 2. User Flow

1. User opens the web interface.
2. User uploads one or more single-page medical invoice PDFs.
3. User clicks the **"Convert"** button.
4. UI displays a progress indicator (e.g., "Working on converting...").
5. On completion, UI displays the resulting JSON for each uploaded PDF.
6. User can **copy** the JSON content to clipboard or **download** it as a `.json` file.

---

## 3. Target JSON Schema

Each PDF produces one JSON object with the following fields:

```json
{
  "总金额": 124.56,
  "收款单位": "XX医院",
  "就诊日期": "2024-01-15",
  "医保基金支付金额": 80.00,
  "个人支付": 44.56,
  "个人账户支付": 30.00,
  "个人现金支付": 14.56
}
```

### Field Definitions

The Pydantic model uses **English field names** internally with **Chinese aliases** (`Field(alias=...)` + `ConfigDict(populate_by_name=True)`) so that Zhipu GLM's Chinese-key JSON output can be deserialized directly.

| English Field | Chinese Alias | Type | Description |
|---|---|---|---|
| total_amount | 总金额 | number (2 decimal places) | Total amount on the invoice |
| payee | 收款单位 | string | Hospital / receiving institution name |
| visit_date | 就诊日期 | string (date, e.g. "2024-01-15") | Date of medical visit |
| insurance_payment | 医保基金支付金额 | number (2 decimal places) | Amount paid by medical insurance fund |
| personal_payment | 个人支付 | number (2 decimal places) | Personal payment total |
| personal_account_payment | 个人账户支付 | number (2 decimal places) | Payment from personal medical insurance account |
| personal_cash_payment | 个人现金支付 | number (2 decimal places) | Out-of-pocket cash payment |

> **Note:** The API response serializes with `by_alias=True`, so the JSON keys seen by the frontend remain Chinese.

---

## 4. Architecture

### 4.1 High-Level Architecture

```
[React Frontend] --HTTP (multipart upload)--> [FastAPI Backend]
                                                     |
                                                     v
                                         [MinerU: PDF → text/markdown]
                                                     |
                                                     v
                                         [Zhipu GLM API: text → structured JSON]
                                                     |
                                                     v
                                         Return JSON to frontend
```

### 4.2 Component Breakdown

- **Frontend (React + Vite):** File upload UI, progress display, JSON viewer with copy/download.
- **Backend (Python FastAPI):** Receives PDF uploads, orchestrates MinerU + Zhipu pipeline, returns JSON.
- **MinerU:** Parses PDF into machine-readable text/markdown. Two integration modes (see Phases below).
- **Zhipu GLM API:** Takes extracted text + a crafted prompt, returns structured JSON matching the target schema.

### 4.3 Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend framework | React (Vite) | Lightweight, fast dev server, good learning resource |
| Backend framework | FastAPI (Python) | Async-friendly, auto-generated API docs, Python ML ecosystem |
| PDF parsing | MinerU | Open-source, strong Chinese document support, VLM-powered |
| Data structuring | Zhipu GLM API | Free for one month, good Chinese language support |
| Deployment (Phase 1) | Local machine | Only API calls, no GPU needed |
| Deployment (Phase 2) | Kaggle Notebooks | Free GPU for self-deployed MinerU |

---

## 5. Implementation Phases

### Phase 1 — End-to-End with MinerU Online API

**Goal:** Get a fully working demo as fast as possible. Learn full-stack integration.

**Architecture:** Everything runs locally. MinerU is called via its cloud API (mineru.net). No GPU needed.

```
[React Frontend (local)]
       |
       v
[FastAPI Backend (local)]
       |
       ├──> MinerU Online API (mineru.net) → returns markdown/text
       |
       └──> Zhipu GLM API → returns structured JSON
       |
       v
[Return JSON to frontend]
```

**Steps:**

1. **Project scaffolding:** Initialize repo, create folder structure, set up React (Vite) and FastAPI skeleton.
2. **MinerU API integration:** Register at mineru.net, apply for API token, implement the upload → parse → poll → get result flow.
3. **Zhipu GLM integration:** Craft the prompt to extract target fields from MinerU's markdown output. Parse Zhipu's response into the target JSON schema.
4. **FastAPI endpoints:** `POST /convert` accepts PDF uploads, orchestrates MinerU + Zhipu, returns JSON array.
5. **React frontend:** File upload component, convert button, loading state, JSON display with copy-to-clipboard and download-as-file.
6. **End-to-end testing:** Test with 3-5 sample invoices, verify JSON accuracy.

### Phase 2 — Self-Deployed MinerU on Kaggle

**Goal:** Learn MinerU internals. Compare self-deployed vs API approach.

**Architecture:** MinerU runs on Kaggle with GPU. Backend calls MinerU locally within the notebook or via a tunnel.

**Steps:**

1. **Kaggle setup:** Create a Kaggle notebook with GPU runtime. Install MinerU (`uv pip install -U "mineru[all]"`). Download required models.
2. **MinerU exploration:** Run MinerU CLI on sample invoices. Experiment with different backends (pipeline, VLM, hybrid). Compare output quality.
3. **Replace API with local MinerU:** Swap the MinerU API call in the backend with a direct Python API call to the locally running MinerU instance.
4. **Deploy full stack on Kaggle (optional):** Run FastAPI + MinerU in the same Kaggle notebook, expose via ngrok tunnel, and connect the React frontend to it.
5. **Comparison:** Document differences between API and self-deployed approaches (speed, output quality, ease of use).

---

## 6. MinerU Integration Details

### 6.1 MinerU Online API (Phase 1)

- **Base URL:** `https://mineru.net/api/v4/`
- **Auth:** Bearer token in Authorization header
- **Token validity:** 14 days (must renew manually at mineru.net)
- **Rate limits (beta):** 2,000 high-priority pages/day, no hard daily limit
- **File size limit:** Max 200 MB per file, max 600 pages per file

**API Flow:**

1. `POST /file-urls/batch` — Request pre-signed upload URLs for local PDF files.
2. `PUT {pre-signed-url}` — Upload the PDF file to the pre-signed URL.
3. Poll `GET /extract-results/batch/{batch_id}` — Check task status until `state: "done"`.
4. Download result zip → extract markdown content.

**Single file alternative:**

1. `POST /extract/task` — Submit a PDF URL for extraction.
2. Poll `GET /extract/task/{task_id}` — Check until done, get result URL.

### 6.2 Self-Deployed MinerU (Phase 2)

- **Installation:** `uv pip install -U "mineru[all]"`
- **Model download:** `mineru-models-download` (several GB, run once)
- **CLI usage:** `mineru -p <input.pdf> -o <output_dir>`
- **Python API:** `mineru-api --host 0.0.0.0 --port 8000` (built-in FastAPI server)
- **Backends:** `pipeline` (rule-based + OCR), `vlm-auto-engine` (VLM-powered), `hybrid-auto-engine` (combined)
- **Recommended backend for Chinese invoices:** `hybrid-auto-engine` or `vlm-auto-engine`
- **GPU requirement:** CUDA GPU recommended; CPU mode available but slow

---

## 7. Zhipu GLM Integration Details

- **API provider:** Zhipu AI (智谱AI)
- **SDK:** `zhipuai` Python package
- **Model:** GLM-4 (or latest available model)
- **Cost:** Free within one-month trial period

### 7.1 Prompt Strategy (Draft)

```
你是一个专业的医疗电子票据信息提取助手。请从以下文本中提取医疗电子票据的关键信息，
并严格按照指定的JSON格式输出。

需要提取的字段：
- 总金额（数值，保留2位小数）
- 收款单位（医院名称，文本）
- 就诊日期（日期，格式：YYYY-MM-DD）
- 医保基金支付金额（数值，保留2位小数）
- 个人支付（数值，保留2位小数）
- 个人账户支付（数值，保留2位小数）
- 个人现金支付（数值，保留2位小数）

如果某个字段在文本中找不到，请将其值设为 null。

请只输出JSON，不要输出其他任何内容。

以下是票据文本内容：
---
{mineru_extracted_text}
---
```

This prompt will be refined during implementation based on actual MinerU output.

---

## 8. Project Structure

```
medical-invoice-parser/
├── README.md                     # Project overview, setup & run instructions
├── docs/
│   ├── requirements.md           # This file
│   └── prompts-log.md            # Key Claude Code prompts and learnings
├── frontend/                     # React app (Vite)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx               # Main app component
│       ├── components/
│       │   ├── FileUpload.jsx    # PDF upload component
│       │   ├── ConvertButton.jsx # Convert trigger
│       │   ├── ProgressBar.jsx   # Loading/progress indicator
│       │   └── JsonViewer.jsx    # JSON display with copy/download
│       └── services/
│           └── api.js            # API client for backend calls
├── backend/                      # FastAPI app
│   ├── requirements.txt
│   ├── main.py                   # FastAPI app entry point
│   ├── routers/
│   │   └── convert.py            # /convert endpoint
│   ├── services/
│   │   ├── mineru_api.py         # MinerU online API client (Phase 1)
│   │   ├── mineru_local.py       # MinerU local integration (Phase 2)
│   │   └── zhipu_structurer.py   # Zhipu GLM prompt + parsing
│   └── models/
│       └── invoice.py            # Pydantic models for the JSON schema
├── notebooks/                    # Kaggle notebooks (Phase 2)
│   └── mineru_setup.ipynb        # MinerU installation & testing on Kaggle
└── samples/                      # Sample invoice PDFs for testing (redacted)
    └── .gitkeep
```

---

## 9. Preparation Checklist

### Accounts & API Keys

- [ ] Register at [mineru.net](https://mineru.net) and apply for API token
- [ ] Verify Zhipu API key works (quick test call)
- [ ] Create Kaggle account (for Phase 2)

### Development Environment

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ and npm installed
- [ ] Git installed
- [ ] VS Code with Claude Code extension installed

### Sample Data

- [ ] Prepare 3-5 sample medical invoice PDFs (redact personal info if using real ones)

### Dependencies (installed during scaffolding)

**Backend:**
- fastapi, uvicorn, python-multipart (web framework)
- zhipuai (Zhipu GLM SDK)
- requests (for MinerU API calls)
- pydantic (data validation)

**Frontend:**
- React 18+ (via Vite)
- axios (HTTP client)

---

## 10. Claude Code Workflow

This project is built with the assistance of Claude Code. The recommended workflow:

1. **Start each Claude Code session** by pointing it to this file: `"Read docs/requirements.md and help me with [specific task]"`
2. **Work incrementally:** One step at a time, test after each step.
3. **Log key prompts** in `docs/prompts-log.md` — especially prompts that produced non-trivial implementations or taught you something.
4. **Use Claude Code for:** scaffolding, implementation, debugging, code review, refactoring.
5. **Come back to the planning chat** for: requirement changes, architectural decisions, new feature planning.

---

## Appendix: Key Reference Links

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [MinerU Documentation](https://opendatalab.github.io/MinerU/)
- [MinerU Online API Docs](https://mineru.net/apiManage/docs)
- [MinerU API Rate Limits](https://mineru.net/doc/docs/limit_en/)
- [Zhipu AI Platform](https://open.bigmodel.cn/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)
