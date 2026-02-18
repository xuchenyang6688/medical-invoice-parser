"""
/convert endpoint — accepts PDF uploads, orchestrates MinerU + Zhipu pipeline,
returns structured JSON.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from models.invoice import ConvertResponse, ConvertResult, InvoiceData

router = APIRouter()


@router.post("/convert", response_model=ConvertResponse)
async def convert_invoices(files: list[UploadFile] = File(...)):
    """
    Accept one or more PDF files, parse each through MinerU, structure
    the extracted text with Zhipu GLM, and return the results.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results: list[ConvertResult] = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a PDF",
            )

        # TODO (Phase 1, Step 2-3): Replace placeholder with real pipeline
        # 1. pdf_bytes = await file.read()
        # 2. markdown_text = await mineru_api.parse_pdf(pdf_bytes)
        # 3. invoice_data = await zhipu_structurer.structure_text(markdown_text)

        invoice_data = InvoiceData()  # placeholder — all fields None

        results.append(
            ConvertResult(filename=file.filename, data=invoice_data)
        )

    return ConvertResponse(results=results).model_dump(by_alias=True)
