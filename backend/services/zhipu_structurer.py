"""
Zhipu GLM integration — takes extracted text from MinerU and returns
structured InvoiceData via prompt engineering.

Uses the zhipuai SDK (sync) to call GLM-4-Flash (free tier).
The function is async-compatible via asyncio.to_thread().
"""

import asyncio
import json
import logging
import os
import re

from zhipuai import ZhipuAI
from models.invoice import InvoiceData

logger = logging.getLogger(__name__)

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")

# ---------------------------------------------------------------------------
# Extraction prompt — refined based on real MinerU markdown output
# ---------------------------------------------------------------------------
# Key observations from sample data:
#   - MinerU uses "医保统筹基金支付" but our schema expects "医保基金支付金额"
#   - MinerU uses "个人自付" but our schema expects "个人支付"
#   - Date may appear as "20250605" instead of "2025-06-05"
#   - Hospital name may not be explicitly labelled "收款单位"; it may
#     appear in the title (e.g., "北京市医疗门报数据") or need inference
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """\
你是一个专业的医疗电子票据信息提取助手。请从以下文本中提取医疗电子票据的关键信息，
并严格按照指定的JSON格式输出。

需要提取的字段（注意：票据中的字段名称可能与下面的名称略有不同，请根据语义匹配）：
- 总金额：票据上的金额合计（小写），数值，保留2位小数
- 收款单位：医院/医疗机构名称，文本。可能出现在票据标题或抬头中
- 就诊日期：格式必须为 YYYY-MM-DD（如原文为 20250605，请转为 2025-06-05）
- 医保基金支付金额：医保统筹基金支付的金额，数值，保留2位小数（票据中可能标注为"医保统筹基金支付"）
- 个人支付：个人支付总额，数值，保留2位小数（票据中可能标注为"个人自付"）
- 个人账户支付：从个人医保账户支付的金额，数值，保留2位小数
- 个人现金支付：个人现金支付金额，数值，保留2位小数

输出示例：
{{"总金额": 80.00, "收款单位": "XX医院", "就诊日期": "2025-06-05", "医保基金支付金额": 14.00, "个人支付": 66.00, "个人账户支付": 66.00, "个人现金支付": 0.00}}

如果某个字段在文本中确实找不到，请将其值设为 null。

请只输出纯JSON，不要输出```json标记或其他任何内容。

以下是票据文本内容：
---
{text}
---"""


class ZhipuAPIError(Exception):
    """Raised when the Zhipu GLM API call or response parsing fails."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _get_client() -> ZhipuAI:
    """Create a ZhipuAI client. Raises ZhipuAPIError if API key is missing."""
    if not ZHIPU_API_KEY:
        raise ZhipuAPIError(
            "ZHIPU_API_KEY is not set. Add it to backend/.env"
        )
    return ZhipuAI(api_key=ZHIPU_API_KEY)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _call_glm_sync(prompt: str) -> str:
    """
    Synchronous call to Zhipu GLM API.

    Returns the raw content string from the model's response.
    """
    client = _get_client()

    logger.info("Calling Zhipu GLM (%s), prompt length: %d chars", ZHIPU_MODEL, len(prompt))

    try:
        response = client.chat.completions.create(
            model=ZHIPU_MODEL,
            messages=[
                # {
                #     "role": "system",
                #     "content": "你是一个专业的医疗票据数据提取助手，只输出JSON格式的结果。",
                # },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,  # Low temperature for deterministic extraction
        )
    except Exception as e:
        raise ZhipuAPIError(f"Zhipu API call failed: {e}") from e

    content = response.choices[0].message.content
    logger.info("Zhipu GLM raw response: %s", content)
    return content


def _parse_response(raw: str) -> InvoiceData:
    """
    Parse the raw GLM response string into an InvoiceData model.

    Steps:
      1. Strip markdown code fences if present
      2. json.loads() the string
      3. InvoiceData.model_validate() using Chinese aliases
    """
    cleaned = _strip_code_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ZhipuAPIError(
            f"Failed to parse GLM response as JSON: {e}\nRaw response: {raw}"
        ) from e

    try:
        invoice = InvoiceData.model_validate(parsed)
    except Exception as e:
        raise ZhipuAPIError(
            f"Failed to validate parsed JSON against InvoiceData schema: {e}\n"
            f"Parsed JSON: {parsed}"
        ) from e

    logger.info("Parsed InvoiceData: %s", invoice.model_dump(by_alias=True))
    return invoice


async def structure_text(text: str) -> InvoiceData:
    """
    Send extracted invoice text to Zhipu GLM and parse the response
    into an InvoiceData model.

    The zhipuai SDK is synchronous, so the actual API call runs in
    a thread executor to avoid blocking the async event loop.

    Args:
        text: Markdown/text content extracted by MinerU.

    Returns:
        InvoiceData with fields populated from GLM's JSON response.

    Raises:
        ZhipuAPIError: If the API call, JSON parsing, or validation fails.
    """
    prompt = EXTRACTION_PROMPT.format(text=text)

    # Run sync SDK call in a thread to keep FastAPI async
    raw_response = await asyncio.to_thread(_call_glm_sync, prompt)

    return _parse_response(raw_response)
