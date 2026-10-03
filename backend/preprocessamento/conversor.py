import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def converter_pdf_para_markdown(pdf_path: Path) -> str:
    """Converte um PDF para markdown usando pymupdf4llm."""
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf_path))
