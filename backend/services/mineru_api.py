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
import json
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
MINERU_POLL_INTERVAL = int(os.getenv("MINERU_POLL_INTERVAL", "5"))
MINERU_POLL_TIMEOUT = int(os.getenv("MINERU_POLL_TIMEOUT", "300"))


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
    Poll GET /extract-results/batch/{batch_id} until all entries are done.

    The "state" field lives on each entry inside data.extract_result[],
    NOT on the data object itself. We check that every entry has
    state == "done" (or "failed") before returning.

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
        logger.info("Poll response: %s", result)

        if result.get("code") != 0:
            msg = result.get("msg", "Unknown error")
            raise MinerUAPIError(f"Poll failed: {msg}")

        data = result["data"]
        extract_result = data.get("extract_result", [])

        # Check state on each entry in extract_result[]
        states = [entry.get("state", "unknown") for entry in extract_result]
        logger.info("Entry states: %s", states)

        # All entries must be in a terminal state (done or failed)
        if extract_result and all(s in ("done", "failed") for s in states):
            # Check for failures
            failed = [
                entry for entry in extract_result
                if entry.get("state") == "failed"
            ]
            if failed:
                err_msgs = [
                    f"{e.get('file_name', '?')}: {e.get('err_msg', 'unknown error')}"
                    for e in failed
                ]
                logger.error("Some files failed: %s", err_msgs)
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


def _flatten_content_list(content_list: list) -> str:
    """
    Flatten content_list_v2.json into plain text suitable for Zhipu GLM.

    The content_list is a nested structure: list of pages, each page is a
    list of blocks. Each block has a "type" and "content" dict.

    We extract text from all block types except images, joining with newlines.
    This preserves ALL invoice content including page_footer blocks that
    the markdown extractor drops (e.g., 收款单位).
    """
    lines: list[str] = []

    for page in content_list:
        for block in page:
            block_type = block.get("type", "")
            content = block.get("content", {})

            if block_type == "title":
                for item in content.get("title_content", []):
                    if item.get("type") == "text":
                        lines.append(item.get("content", ""))

            elif block_type == "paragraph":
                for item in content.get("paragraph_content", []):
                    if item.get("type") == "text":
                        lines.append(item.get("content", ""))

            elif block_type == "table":
                # Pass HTML table directly — GLM can parse it
                html = content.get("html", "")
                if html:
                    lines.append(html)

            elif block_type == "page_footer":
                for item in content.get("page_footer_content", []):
                    if item.get("type") == "text":
                        lines.append(item.get("content", ""))

            elif block_type == "page_header":
                for item in content.get("page_header_content", []):
                    if item.get("type") == "text":
                        lines.append(item.get("content", ""))

            # Skip "image" blocks — no useful text

    return "\n".join(lines)


async def _extract_content_text_from_zip(
    client: httpx.AsyncClient,
    zip_url: str,
) -> str:
    """
    Download a result zip and extract flattened text from content_list_v2.json.

    This is preferred over _extract_markdown_from_zip() because the
    content_list includes ALL content blocks (including page_footer with
    收款单位) that the markdown extractor drops.

    Fallback order:
      1. content_list_v2.json
      2. *_content_list.json
      3. Fall back to markdown extraction
    """
    logger.info("Downloading result zip from %s", zip_url)
    resp = await client.get(zip_url)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        all_files = zf.namelist()
        logger.debug("Zip contents: %s", all_files)

        # Try content_list_v2.json first
        content_list_file = None
        for name in all_files:
            if name.endswith("content_list_v2.json"):
                content_list_file = name
                break

        # Fallback to *_content_list.json
        if not content_list_file:
            for name in all_files:
                if name.endswith("_content_list.json"):
                    content_list_file = name
                    break

        if content_list_file:
            raw = zf.read(content_list_file).decode("utf-8", errors="replace")
            try:
                content_list = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse %s: %s, falling back to markdown",
                    content_list_file, e,
                )
                return await _extract_markdown_from_zip(client, zip_url)

            text = _flatten_content_list(content_list)
            logger.info(
                "Extracted content text from '%s' (%d chars)",
                content_list_file,
                len(text),
            )
            return text

        # No content_list found — fall back to markdown
        logger.warning(
            "No content_list JSON in zip, falling back to markdown. Files: %s",
            all_files,
        )
        # Re-use the already downloaded zip bytes
        md_files = [n for n in all_files if n.endswith(".md")]
        if md_files:
            md_content = zf.read(md_files[0]).decode("utf-8", errors="replace")
            logger.info("Fallback: extracted markdown from '%s'", md_files[0])
            return md_content

        raise MinerUAPIError("Result zip contains no content_list or markdown files")


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
    Kept for backward compatibility and debug comparison.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        return await _extract_markdown_from_zip(client, zip_url)


async def extract_content_text_from_zip(zip_url: str) -> str:
    """
    Public wrapper around _extract_content_text_from_zip.

    Downloads a result zip and extracts flattened text from content_list_v2.json.
    This is the preferred extraction method — includes page_footer blocks
    (e.g., 收款单位) that the markdown extractor drops.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        return await _extract_content_text_from_zip(client, zip_url)


async def parse_pdf(pdf_bytes: bytes, filename: str = "invoice.pdf") -> str:
    """
    Send a single PDF to the MinerU Online API and return extracted text.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        filename:  Original filename (used in the upload request).

    Returns:
        Extracted text string from MinerU (flattened from content_list_v2.json).

    Raises:
        MinerUAPIError: If the API returns an error or times out.
    """
    results = await parse_pdfs_batch([(pdf_bytes, filename)])
    return results[0]


async def parse_pdfs_batch(
    files: list[tuple[bytes, str]],
) -> list[str]:
    """
    Upload multiple PDFs in a single batch and return extracted text
    for each file.

    Uses content_list_v2.json from the result zip (preferred over markdown
    because it includes page_footer blocks with 收款单位 etc.).

    Args:
        files: List of (pdf_bytes, filename) tuples.

    Returns:
        List of text strings, one per input file (same order).

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

        # Step 4: Extract text from results (content_list_v2.json preferred)
        extract_result = data.get("extract_result", [])
        logger.info(
            "Got %d extract_result entries for %d files",
            len(extract_result),
            len(files),
        )

        texts: list[str] = []
        for i, entry in enumerate(extract_result):
            # Check if entry has a zip URL that needs downloading
            text = _extract_markdown_from_result(entry)

            if text.startswith("http"):
                # It's a URL — download the zip and extract content_list text
                text = await _extract_content_text_from_zip(client, text)

            if not text:
                logger.warning(
                    "Empty text for file %d (%s), raw entry: %s",
                    i,
                    filenames[i] if i < len(filenames) else "?",
                    entry,
                )

            texts.append(text)

        return texts
