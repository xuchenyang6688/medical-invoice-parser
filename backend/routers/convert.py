"""
/convert endpoint — accepts PDF uploads, orchestrates MinerU + Zhipu pipeline,
returns structured JSON.
"""

import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from models.invoice import ConvertResponse, ConvertResult, InvoiceData
from services.mineru_api import (
    parse_pdfs_batch,
    fetch_results_once,
    extract_markdown_from_zip,
    extract_content_text_from_zip,
    MinerUAPIError,
    _extract_markdown_from_result,
)
from services.zhipu_structurer import structure_text, ZhipuAPIError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/convert", response_model=ConvertResponse)
async def convert_invoices(files: list[UploadFile] = File(...)):
    """
    Accept one or more PDF files, parse each through MinerU, structure
    the extracted text with Zhipu GLM, and return the results.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Validate all files are PDFs and read bytes
    pdf_files: list[tuple[bytes, str]] = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a PDF",
            )
        pdf_bytes = await file.read()
        pdf_files.append((pdf_bytes, file.filename))

    # Step 1: Parse PDFs through MinerU (batch) — uses content_list_v2.json
    try:
        extracted_texts = await parse_pdfs_batch(pdf_files)
    except MinerUAPIError as e:
        logger.error("MinerU API error: %s", e.detail)
        raise HTTPException(status_code=502, detail=f"MinerU error: {e.detail}")

    # Step 2: Structure each extracted text with Zhipu GLM
    results: list[ConvertResult] = []
    for (_, filename), extracted_text in zip(pdf_files, extracted_texts):
        logger.info(
            "Got %d chars of extracted text for '%s'", len(extracted_text), filename
        )

        # Step 2b: Structure with Zhipu GLM
        try:
            invoice_data = await structure_text(extracted_text)
        except ZhipuAPIError as e:
            logger.error("Zhipu GLM error for '%s': %s", filename, e.detail)
            raise HTTPException(
                status_code=502, detail=f"Zhipu GLM error: {e.detail}"
            )

        results.append(
            ConvertResult(filename=filename, data=invoice_data)
        )

    return ConvertResponse(results=results).model_dump(by_alias=True)


@router.post("/debug/mineru")
async def debug_mineru(files: list[UploadFile] = File(...)):
    """
    Debug endpoint — returns raw MinerU markdown output for inspection.
    Useful for verifying extraction quality before wiring up Zhipu GLM.

    Remove this endpoint before production use.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    pdf_files: list[tuple[bytes, str]] = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a PDF",
            )
        pdf_bytes = await file.read()
        pdf_files.append((pdf_bytes, file.filename))

    try:
        markdown_texts = await parse_pdfs_batch(pdf_files)
    except MinerUAPIError as e:
        raise HTTPException(status_code=502, detail=f"MinerU error: {e.detail}")

    return {
        "results": [
            {"filename": fname, "markdown": md}
            for (_, fname), md in zip(pdf_files, markdown_texts)
        ]
    }


@router.get("/debug/extract-result/{batch_id}")
async def debug_extract_result(batch_id: str):
    """
    Debug endpoint — fetch results for a previously submitted batch_id
    (single GET, no polling), then extract text from any completed entries.

    Uses content_list_v2.json extraction (preferred over markdown).

    Example:
        GET /debug/extract-result/c03af1fa-e6f2-49e6-af5f-67deb9ba88c8
    """
    try:
        data = await fetch_results_once(batch_id)
    except MinerUAPIError as e:
        raise HTTPException(status_code=502, detail=f"MinerU error: {e.detail}")

    extract_result = data.get("extract_result", [])
    results = []

    for entry in extract_result:
        file_name = entry.get("file_name", "unknown")
        state = entry.get("state", "unknown")
        err_msg = entry.get("err_msg", "")
        content_text = ""

        if state == "done":
            try:
                text = _extract_markdown_from_result(entry)
                if text.startswith("http"):
                    text = await extract_content_text_from_zip(text)
                content_text = text
            except Exception as e:
                content_text = f"[extraction error: {e}]"

        results.append({
            "file_name": file_name,
            "state": state,
            "err_msg": err_msg,
            "content_text": content_text,
        })

    return {"batch_id": batch_id, "results": results}


@router.post("/debug/extract-zip")
async def debug_extract_zip(body: dict):
    """
    Debug endpoint — download a zip from the given URL and extract text
    using content_list_v2.json (preferred) or markdown (fallback).

    Accepts JSON body: {"zip_url": "https://cdn-mineru.openxlab.org.cn/..."}

    Use this to test zip extraction in complete isolation.
    """
    zip_url = body.get("zip_url", "")
    if not zip_url:
        raise HTTPException(status_code=400, detail="zip_url is required")

    try:
        content_text = await extract_content_text_from_zip(zip_url)
    except MinerUAPIError as e:
        raise HTTPException(status_code=502, detail=f"Zip extraction error: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return {"zip_url": zip_url, "content_text": content_text}


class ZhipuDebugRequest(BaseModel):
    """Request body for the /debug/zhipu endpoint."""
    markdown: str


@router.post("/debug/zhipu")
async def debug_zhipu(body: ZhipuDebugRequest):
    """
    Debug endpoint — send markdown text directly to Zhipu GLM for structuring,
    bypassing the MinerU pipeline entirely.

    Accepts JSON body: {"markdown": "<MinerU markdown content>"}

    Use this to test Zhipu structuring in isolation with saved MinerU output
    (e.g., from backend/test/mineru_markdown_result.md) without waiting
    10+ minutes for MinerU polling.

    Example with curl:
        curl -X POST http://localhost:8000/debug/zhipu \\
          -H "Content-Type: application/json" \\
          -d '{"markdown": "# 北京市医疗门报数据..."}'
    """
    try:
        invoice_data = await structure_text(body.markdown)
    except ZhipuAPIError as e:
        raise HTTPException(status_code=502, detail=f"Zhipu GLM error: {e.detail}")

    return {
        "invoice_data": invoice_data.model_dump(by_alias=True),
        "invoice_data_english": invoice_data.model_dump(),
    }
