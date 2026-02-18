"""
Pydantic models for the medical invoice JSON schema.

Uses English field names for code maintainability, with Chinese aliases
so that Zhipu GLM's JSON output (which uses Chinese keys) can be
deserialized directly via model_validate().

Example GLM output (deserializable via alias):
{
    "总金额": 124.56,
    "收款单位": "XX医院",
    "就诊日期": "2024-01-15",
    "医保基金支付金额": 80.00,
    "个人支付": 44.56,
    "个人账户支付": 30.00,
    "个人现金支付": 14.56
}

Example serialized with by_alias=True (for API response):
Same Chinese-key JSON as above.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InvoiceData(BaseModel):
    """Structured data extracted from a medical invoice."""

    model_config = ConfigDict(populate_by_name=True)

    total_amount: Optional[float] = Field(
        None,
        alias="总金额",
        description="Total amount on the invoice",
    )
    payee: Optional[str] = Field(
        None,
        alias="收款单位",
        description="Hospital / receiving institution name",
    )
    visit_date: Optional[str] = Field(
        None,
        alias="就诊日期",
        description="Date of medical visit (YYYY-MM-DD)",
    )
    insurance_payment: Optional[float] = Field(
        None,
        alias="医保基金支付金额",
        description="Amount paid by medical insurance fund",
    )
    personal_payment: Optional[float] = Field(
        None,
        alias="个人支付",
        description="Personal payment total",
    )
    personal_account_payment: Optional[float] = Field(
        None,
        alias="个人账户支付",
        description="Payment from personal medical insurance account",
    )
    personal_cash_payment: Optional[float] = Field(
        None,
        alias="个人现金支付",
        description="Out-of-pocket cash payment",
    )


class ConvertResult(BaseModel):
    """Result for a single PDF file conversion."""

    filename: str = Field(..., description="Original PDF filename")
    data: InvoiceData = Field(..., description="Extracted invoice data")


class ConvertResponse(BaseModel):
    """Response from the /convert endpoint."""

    results: list[ConvertResult] = Field(..., description="List of conversion results")
