"""
MinerU Online API client (Phase 1).

Handles the full local-file-upload flow:
  1. POST /file-urls/batch   → get pre-signed upload URLs + batch_id
  2. PUT  {pre-signed-url}   → upload raw PDF bytes (no Content-Type header)
     (system auto-submits parsing tasks after upload)
  3. Poll GET /extract-results/batch/{batch_id} → wait for state=="done"
  4. Extract markdown content from results

Base URL : https://mineru.net/api/v4/
Auth     : Bearer token in Authorization header
"""

import asyncio
import io
import logging
import os
import zipfile
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MINERU_API_BASE = "https://mineru.net/api/v4"
MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN", "")
MINERU_MODEL_VERSION = os.getenv("MINERU_MODEL_VERSION", "vlm")
MINERU_POLL_INTERVAL = int(os.getenv("MINERU_POLL_INTERVAL", "60"))
MINERU_POLL_TIMEOUT = int(os.getenv("MINERU_POLL_TIMEOUT", "1200"))


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------
class MinerUAPIError(Exception):
    """Raised when the MinerU API returns an error or times out."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _headers() -> dict:
    """Return auth + content-type headers for JSON endpoints."""
    token = MINERU_API_TOKEN or os.getenv("MINERU_API_TOKEN", "")
    if not token:
        raise MinerUAPIError("MINERU_API_TOKEN is not set")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


async def _request_upload_urls(
    client: httpx.AsyncClient,
    filenames: list[str],
) -> tuple[str, list[str]]:
    """
    POST /file-urls/batch — request pre-signed upload URLs.

    Returns:
        (batch_id, list_of_presigned_urls)
    """
    files_payload = [
        {"name": name, "data_id": uuid4().hex}
        for name in filenames
    ]
    body = {
        "files": files_payload,
        "model_version": MINERU_MODEL_VERSION,
    }

    logger.info("Requesting upload URLs for %d file(s)...", len(filenames))
    resp = await client.post(
        f"{MINERU_API_BASE}/file-urls/batch",
        headers=_headers(),
        json=body,
    )
    resp.raise_for_status()
    result = resp.json()
    logger.debug("file-urls/batch response: %s", result)

    if result.get("code") != 0:
        msg = result.get("msg", "Unknown error")
        raise MinerUAPIError(f"file-urls/batch failed: {msg}")

    data = result["data"]
    batch_id = data["batch_id"]
    file_urls = data["file_urls"]
    logger.info("Got batch_id=%s, %d upload URL(s)", batch_id, len(file_urls))
    return batch_id, file_urls


async def _upload_file(
    client: httpx.AsyncClient,
    url: str,
    pdf_bytes: bytes,
) -> None:
    """
    PUT raw PDF bytes to the pre-signed upload URL.

    Per the docs: do NOT set Content-Type when uploading.
    """
    logger.info("Uploading %d bytes to pre-signed URL...", len(pdf_bytes))
    resp = await client.put(url, content=pdf_bytes)
    if resp.status_code != 200:
        raise MinerUAPIError(
            f"File upload failed: HTTP {resp.status_code} — {resp.text[:200]}"
        )
    logger.info("Upload succeeded (HTTP %d)", resp.status_code)


async def _poll_results(
    client: httpx.AsyncClient,
    batch_id: str,
    timeout: int = MINERU_POLL_TIMEOUT,
    interval: int = MINERU_POLL_INTERVAL,
) -> dict:
    """
    Poll GET /extract-results/batch/{batch_id} until state == "done".

    Returns:
        The full response data dict.
    """
    url = f"{MINERU_API_BASE}/extract-results/batch/{batch_id}"
    elapsed = 0
    attempt = 0

    while elapsed < timeout:
        attempt += 1
        logger.info(
            "Polling results (attempt %d, elapsed %ds)...", attempt, elapsed
        )

        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        result = resp.json()
        logger.debug("Poll response: %s", result)

        if result.get("code") != 0:
            msg = result.get("msg", "Unknown error")
            raise MinerUAPIError(f"Poll failed: {msg}")

        data = result["data"]
        state = data.get("state", "unknown")
        logger.info("Batch state: %s", state)

        if state == "done":
            return data

        await asyncio.sleep(interval)
        elapsed += interval

    raise MinerUAPIError(
        f"Polling timed out after {timeout}s for batch_id={batch_id}"
    )


async def _extract_markdown_from_zip(
    client: httpx.AsyncClient,
    zip_url: str,
) -> str:
    """Download a result zip and extract the markdown content."""
    logger.info("Downloading result zip from %s", zip_url)
    resp = await client.get(zip_url)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Look for .md files inside the zip
        md_files = [n for n in zf.namelist() if n.endswith(".md")]
        if not md_files:
            # Fall back to any text-like file
            all_files = zf.namelist()
            logger.warning("No .md files in zip, found: %s", all_files)
            if all_files:
                return zf.read(all_files[0]).decode("utf-8", errors="replace")
            raise MinerUAPIError("Result zip contains no readable files")

        # Read the first (usually only) markdown file
        md_content = zf.read(md_files[0]).decode("utf-8", errors="replace")
        logger.info(
            "Extracted markdown from '%s' (%d chars)",
            md_files[0],
            len(md_content),
        )
        return md_content


def _extract_markdown_from_result(result: dict) -> str:
    """
    Extract markdown text from a single extract_result entry.

    The result may contain:
    - full_zip_url: URL to download a zip with markdown
    - content_list / markdown: inline markdown content
    We handle both cases.
    """
    # Try inline markdown first
    if "markdown" in result:
        return result["markdown"]

    if "content_list" in result and result["content_list"]:
        # content_list is typically a list of content blocks
        parts = []
        for item in result["content_list"]:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", item.get("content", "")))
        return "\n".join(parts)

    # If no inline content, return the full_zip_url for later download
    return result.get("full_zip_url", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def fetch_results_once(batch_id: str) -> dict:
    """
    Single GET to /extract-results/batch/{batch_id} — no polling loop.

    Returns the raw 'data' dict from the API response.
    Useful for debug endpoints that want to inspect a previously completed batch.

    Raises:
        MinerUAPIError: If the API returns an error.
    """
    url = f"{MINERU_API_BASE}/extract-results/batch/{batch_id}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") != 0:
            msg = result.get("msg", "Unknown error")
            raise MinerUAPIError(f"fetch_results_once failed: {msg}")

        return result["data"]


async def extract_markdown_from_zip(zip_url: str) -> str:
    """
    Public wrapper around _extract_markdown_from_zip.

    Downloads a result zip and extracts the markdown content.
    Useful for debug endpoints that want to test zip extraction in isolation.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        return await _extract_markdown_from_zip(client, zip_url)


async def parse_pdf(pdf_bytes: bytes, filename: str = "invoice.pdf") -> str:
    """
    Send a single PDF to the MinerU Online API and return extracted markdown.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        filename:  Original filename (used in the upload request).

    Returns:
        Extracted text/markdown string from MinerU.

    Raises:
        MinerUAPIError: If the API returns an error or times out.
    """
    results = await parse_pdfs_batch([(pdf_bytes, filename)])
    return results[0]


async def parse_pdfs_batch(
    files: list[tuple[bytes, str]],
) -> list[str]:
    """
    Upload multiple PDFs in a single batch and return extracted markdown
    for each file.

    Args:
        files: List of (pdf_bytes, filename) tuples.

    Returns:
        List of markdown strings, one per input file (same order).

    Raises:
        MinerUAPIError: If the API returns an error or times out.
    """
    if not files:
        return []

    filenames = [f[1] for f in files]

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # Step 1: Request pre-signed upload URLs
        batch_id, upload_urls = await _request_upload_urls(client, filenames)

        if len(upload_urls) != len(files):
            raise MinerUAPIError(
                f"Expected {len(files)} upload URLs, got {len(upload_urls)}"
            )

        # Step 2: Upload each PDF to its pre-signed URL
        for (pdf_bytes, fname), url in zip(files, upload_urls):
            logger.info("Uploading '%s'...", fname)
            await _upload_file(client, url, pdf_bytes)

        # Step 3: Poll until all tasks are done
        data = await _poll_results(client, batch_id)

        # Step 4: Extract markdown from results
        extract_result = data.get("extract_result", [])
        logger.info(
            "Got %d extract_result entries for %d files",
            len(extract_result),
            len(files),
        )

        markdowns: list[str] = []
        for i, entry in enumerate(extract_result):
            # Check if entry has a zip URL that needs downloading
            md_text = _extract_markdown_from_result(entry)

            if md_text.startswith("http"):
                # It's a URL — download the zip and extract markdown
                md_text = await _extract_markdown_from_zip(client, md_text)

            if not md_text:
                logger.warning(
                    "Empty markdown for file %d (%s), raw entry: %s",
                    i,
                    filenames[i] if i < len(filenames) else "?",
                    entry,
                )

            markdowns.append(md_text)

        return markdowns
