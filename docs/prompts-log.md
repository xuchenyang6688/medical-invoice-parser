# Claude Code Prompts Log

This document tracks key Claude Code prompts and learnings during the development of the Medical Invoice Parser project.

## Purpose

- Record effective prompts that produced useful implementations
- Note challenges encountered and how they were resolved
- Document architectural decisions and their rationale
- Provide context for future development sessions

---

## Session 1 - Project Scaffolding

### Initial Setup Prompt
**Prompt:** "Read instructions/docs/requirements.md. Help me with Phase 1, Step 1: scaffold the project structure."

**Outcome:**
- Created comprehensive project structure following requirements.md specifications
- Set up React + Vite frontend skeleton
- Set up FastAPI backend skeleton
- Created documentation and configuration files
- Used Conda for Python environment management instead of venv

**Learnings:**
- Using Vite for React provides a fast development experience
- Separating concerns with components and services makes the codebase maintainable
- Pydantic models in FastAPI provide automatic validation and documentation
- Conda provides better environment management for data science projects with complex dependencies

---

## Session 2 - MinerU API Integration (Phase 1, Step 2)

### Initial Prompt
**Prompt:** "Let's continue with Phase 1, Step 2: MinerU API integration and per the doc/requirement.txt 6.1 section, and also refer to the MinerU API document https://mineru.net/apiManage/docs"

**Outcome:**
- Implemented full MinerU Online API client in `backend/services/mineru_api.py`
- Wired MinerU into `POST /convert` endpoint
- Added debug endpoints for testing without long polling waits

### API Flow Discovered

The correct flow for local file uploads (clarified from official docs):
1. `POST /api/v4/file-urls/batch` — get pre-signed URLs + `batch_id`
2. `PUT {pre-signed-url}` — upload raw PDF bytes (no Content-Type header)
3. System auto-submits parsing tasks — **no separate extract call needed**
4. Poll `GET /api/v4/extract-results/batch/{batch_id}` until `state == "done"`
5. Download result zip → extract `.md` file

**Key correction:** `POST /extract/task/batch` is only for URL-based extraction (files already hosted online), NOT for local file uploads.

### Key Learnings

- **Polling takes 10+ minutes** for a single-page invoice — default timeout/interval needed to be much larger than initially assumed (changed to 60s interval, 1200s timeout)
- **Response field is `extract_result`** (singular, no 's') — easy to get wrong
- **Results come as zip files** containing markdown — need to download and extract
- **Debug endpoints are invaluable** when API calls are slow: created `GET /debug/extract-result/{batch_id}` and `POST /debug/extract-zip` to test extraction logic without re-uploading and waiting
- **API doc access challenge:** The MinerU docs page is a React SPA — raw HTML extraction didn't work. User pasted the relevant API documentation directly, which was more efficient
- **`httpx.AsyncClient`** works well for async HTTP in FastAPI — already available as a transitive dependency of `zhipuai`

### Architecture Decision: Batch-First
- `parse_pdfs_batch()` is the core function (handles multiple files in one batch)
- `parse_pdf()` is a convenience wrapper for single files
- This avoids redundant API calls when processing multiple invoices

---

## Session 3 - Zhipu GLM Integration + Content List Extraction (Phase 1, Step 3)

### Initial Prompt
**Prompt:** "Let's continue with Phase 1, Step 3: Zhipu GLM integration"

**Outcome:**
- Implemented full Zhipu GLM structurer in `backend/services/zhipu_structurer.py`
- Wired Zhipu into `POST /convert`, replacing the `InvoiceData()` placeholder
- Switched MinerU extraction from `full.md` to `content_list_v2.json` for more complete data
- Added `POST /debug/zhipu` debug endpoint for isolated testing

### Key Discovery: Markdown Drops Page Footers

Testing revealed that the markdown (`full.md`) from MinerU's zip **drops `page_footer` blocks**. The hospital name (`收款单位（章）：宣武医院`) lives in a page footer, so Zhipu GLM incorrectly guessed `"北京市医疗门报数据（电子）"` (the document title) as the payee.

**Solution:** Switched to extracting `content_list_v2.json` from the zip instead, which preserves ALL content blocks:
- `title` → document title text
- `paragraph` → field labels and values (票据代码, 交款人, 开票日期, etc.)
- `table` → HTML table with amounts and insurance details
- `page_footer` → **收款单位（章）：宣武医院** ← this was missing from markdown!

### content_list_v2.json Structure
```
[                              ← array of pages
  [                            ← page = array of blocks
    { "type": "title",       content.title_content[*].content }
    { "type": "paragraph",   content.paragraph_content[*].content }
    { "type": "table",       content.html }
    { "type": "page_footer", content.page_footer_content[*].content }
  ]
]
```

### Zhipu GLM Implementation Details

- **SDK:** `zhipuai.ZhipuAI` (sync SDK, wrapped with `asyncio.to_thread()` for async FastAPI)
- **Model:** `glm-4-flash` (free tier, sufficient for structured extraction)
- **Temperature:** 0.1 (low for deterministic extraction)
- **Prompt refinements:**
  - Added field name variation hints (e.g., `医保统筹基金支付` → `医保基金支付金额`)
  - Added date format normalization instruction (`20250605` → `2025-06-05`)
  - Added output example for GLM to follow
  - Instructed to output pure JSON without code fences
- **Response parsing:** Strip code fences → `json.loads()` → `InvoiceData.model_validate()` (uses Chinese aliases)

### Key Learnings

- **`content_list_v2.json` > `full.md`** for invoice data extraction — markdown drops footers and headers
- **`_flatten_content_list()` helper** iterates pages → blocks, extracts text by type, joins with newlines
- **`glm-4-flash`** is free and fast enough for structured extraction tasks
- **System message commented out** — the extraction prompt alone is sufficient; adding a system message caused inconsistent results
- **`sniffio` dependency** was missing from the `zhipuai` package — had to install separately
- **Debug endpoints remain invaluable** — `POST /debug/zhipu` allows testing GLM structuring with saved MinerU output, avoiding the 10-min MinerU wait

### Architecture Decision: Content List Preferred, Markdown Fallback

- `_extract_content_text_from_zip()` tries `content_list_v2.json` first, falls back to `*_content_list.json`, then markdown
- Old `_extract_markdown_from_zip()` kept for backward compatibility and debug comparison
- `parse_pdfs_batch()` switched to use content_list extraction

---

## Session 4 - React Frontend Wiring (Phase 1, Step 5)

### Initial Prompt
**Prompt:** "Let's continue" (after Phase 1, Step 3 was committed)

**Outcome:**
- Wired the React frontend to the real backend API — replaced `setTimeout` placeholder in `App.jsx` with actual `api.convertFiles(files)` call
- All frontend components were already fully implemented during scaffolding (Session 1)
- Created `CLAUDE.md` at project root for future Claude Code sessions

### What Changed

Only `frontend/src/App.jsx` needed modification:
- Added `import api from './services/api'`
- Replaced `setTimeout(() => { setIsConverting(false) }, 2000)` with `await api.convertFiles(files)`
- Used `finally` block to ensure `setIsConverting(false)` always runs
- Better error message extraction from error objects

### Key Learning

- **Scaffolding pays off:** All 4 frontend components (`FileUpload`, `ConvertButton`, `ProgressBar`, `JsonViewer`) and `api.js` were fully implemented during the scaffolding phase (Session 1). The only missing piece was a single import + function call in `App.jsx`. Good scaffolding dramatically reduces integration work.

---

## Session 5 - Polling Bug Fix

### Bug Report
**User identified:** `_poll_results()` in `mineru_api.py` was reading `state` from the wrong JSON level.

**Root cause:** The code had `state = data.get("state", "unknown")`, but MinerU's API response puts `state` on each entry inside `data.extract_result[]`, NOT on the `data` object itself. This caused `state` to always be `"unknown"`, so the polling loop never detected completion and always timed out.

**MinerU API response structure:**
```json
{
  "code": 0,
  "data": {
    "batch_id": "...",
    "extract_result": [
      {
        "data_id": "...",
        "file_name": "invoice.pdf",
        "state": "done",
        "full_zip_url": "..."
      }
    ]
  }
}
```

### Fix Applied
Changed `_poll_results()` to iterate `data.extract_result[]` and check that ALL entries have a terminal state (`"done"` or `"failed"`):
```python
extract_result = data.get("extract_result", [])
states = [entry.get("state", "unknown") for entry in extract_result]
if extract_result and all(s in ("done", "failed") for s in states):
    return data
```

Also added handling for failed entries — logs error messages for any files with `state == "failed"`.

### Key Learning
- **Always verify API response structure against real responses** — the `state` field location was assumed incorrectly during initial implementation
- **Poll defaults adjusted** to `MINERU_POLL_INTERVAL=5s`, `MINERU_POLL_TIMEOUT=300s` (from previous 60s/1200s) since the bug was the real reason for timeouts, not slow processing

---

## Future Sessions

*(This section will be updated as development progresses)*

---

## Tips for Future Development

1. **Before starting:** Always reference the requirements document to stay aligned with project goals
2. **After implementation:** Test each component independently before integrating
3. **When stuck:** Break down the problem into smaller, testable pieces
4. **API integration:** Test API calls with tools like Postman or curl first
5. **Error handling:** Add meaningful error messages for better debugging

---

## Notes

- Last updated: 2026-02-19
- Current phase: Phase 1 - End-to-End with MinerU Online API (Steps 1-5 complete, Step 6 end-to-end testing remaining)
- Environment: Conda for Python, npm for Node.js
