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
- Current phase: Phase 1 - End-to-End with MinerU Online API (Step 2 complete)
- Environment: Conda for Python, npm for Node.js
