"""
/convert endpoint — accepts PDF uploads, orchestrates MinerU + Zhipu pipeline,
returns structured JSON.
"""

import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from models.invoice import ConvertResponse, ConvertResult, InvoiceData
from services.mineru_api import (
    parse_pdfs_batch,
    fetch_results_once,
    extract_markdown_from_zip,
    MinerUAPIError,
    _extract_markdown_from_result,
)

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

    # Step 1: Parse PDFs through MinerU (batch)
    try:
        markdown_texts = await parse_pdfs_batch(pdf_files)
    except MinerUAPIError as e:
        logger.error("MinerU API error: %s", e.detail)
        raise HTTPException(status_code=502, detail=f"MinerU error: {e.detail}")

    # Step 2: Structure each markdown text with Zhipu GLM
    results: list[ConvertResult] = []
    for (_, filename), markdown_text in zip(pdf_files, markdown_texts):
        logger.info(
            "Got %d chars of markdown for '%s'", len(markdown_text), filename
        )

        # TODO (Phase 1, Step 3): Replace placeholder with Zhipu GLM call
        # invoice_data = await zhipu_structurer.structure_text(markdown_text)
        invoice_data = InvoiceData()  # placeholder — all fields None

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
    (single GET, no polling), then extract markdown from any completed entries.

    Use this to test the zip-download + markdown-extraction logic without
    waiting 10+ minutes for polling.

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
        markdown = ""

        if state == "done":
            try:
                md_text = _extract_markdown_from_result(entry)
                if md_text.startswith("http"):
                    md_text = await extract_markdown_from_zip(md_text)
                markdown = md_text
            except Exception as e:
                markdown = f"[extraction error: {e}]"

        results.append({
            "file_name": file_name,
            "state": state,
            "err_msg": err_msg,
            "markdown": markdown,
        })

    return {"batch_id": batch_id, "results": results}


@router.post("/debug/extract-zip")
async def debug_extract_zip(body: dict):
    """
    Debug endpoint — download a zip from the given URL and extract markdown.

    Accepts JSON body: {"zip_url": "https://cdn-mineru.openxlab.org.cn/..."}

    Use this to test zip extraction in complete isolation.
    """
    zip_url = body.get("zip_url", "")
    if not zip_url:
        raise HTTPException(status_code=400, detail="zip_url is required")

    try:
        markdown = await extract_markdown_from_zip(zip_url)
    except MinerUAPIError as e:
        raise HTTPException(status_code=502, detail=f"Zip extraction error: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return {"zip_url": zip_url, "markdown": markdown}
