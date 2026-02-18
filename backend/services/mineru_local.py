"""
MinerU local/self-deployed integration (Phase 2).

This module will replace the online API client with a direct Python call
to a locally running MinerU instance (e.g. on Kaggle with GPU).
"""


async def parse_pdf_local(pdf_bytes: bytes, filename: str = "invoice.pdf") -> str:
    """
    Parse a PDF using a self-deployed MinerU instance.

    This is a Phase 2 feature — not yet implemented.
    """
    raise NotImplementedError(
        "Phase 2: MinerU local integration not yet implemented. "
        "Use mineru_api.parse_pdf() for the online API approach."
    )
