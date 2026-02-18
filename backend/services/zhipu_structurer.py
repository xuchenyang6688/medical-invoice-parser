"""
Zhipu GLM integration — takes extracted text from MinerU and returns
structured InvoiceData via prompt engineering.
"""

import os

from models.invoice import InvoiceData

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")

# Draft extraction prompt (will be refined based on actual MinerU output)
EXTRACTION_PROMPT = """\
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
{text}
---
"""


async def structure_text(text: str) -> InvoiceData:
    """
    Send extracted invoice text to Zhipu GLM and parse the response
    into an InvoiceData model.

    Args:
        text: Markdown/text content extracted by MinerU.

    Returns:
        InvoiceData with fields populated from GLM's JSON response.
    """
    # TODO (Phase 1, Step 3): Implement Zhipu GLM integration
    #
    # Steps:
    #   1. Build prompt by inserting `text` into EXTRACTION_PROMPT
    #   2. Call Zhipu GLM API via zhipuai SDK
    #   3. Parse the JSON response string
    #   4. Validate and return InvoiceData.model_validate(parsed_json)
    #
    raise NotImplementedError("Zhipu GLM integration not yet implemented")
