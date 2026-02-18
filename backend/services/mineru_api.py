"""
MinerU Online API client (Phase 1).

Handles the full flow:
  1. POST /file-urls/batch   → get pre-signed upload URLs
  2. PUT  {pre-signed-url}   → upload PDF bytes
  3. Poll GET /extract-results/batch/{batch_id} → wait for state=="done"
  4. Download result zip      → extract markdown content

Base URL : https://mineru.net/api/v4/
Auth     : Bearer token in Authorization header
"""

import os

MINERU_API_BASE = "https://mineru.net/api/v4"
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")


async def parse_pdf(pdf_bytes: bytes, filename: str = "invoice.pdf") -> str:
    """
    Send a PDF to the MinerU Online API and return the extracted
    markdown/text content.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        filename:  Original filename (used in the upload request).

    Returns:
        Extracted text/markdown string from MinerU.
    """
    # TODO (Phase 1, Step 2): Implement MinerU API integration
    #
    # Steps:
    #   1. Request pre-signed upload URL via POST /file-urls/batch
    #   2. Upload PDF bytes to the pre-signed URL via PUT
    #   3. Poll GET /extract-results/batch/{batch_id} until state == "done"
    #   4. Download result zip and extract markdown content
    #
    raise NotImplementedError("MinerU API integration not yet implemented")
