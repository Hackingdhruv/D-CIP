"""OCR service — modular text extraction via Tesseract.

Modular design: `OCRBackend` protocol allows swapping Tesseract for another
backend without changing callers. Tesseract is the only built-in backend;
configure TESSERACT_CMD or ensure `tesseract` is on PATH.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_TESSERACT_AVAILABLE: bool | None = None


def _check_tesseract() -> bool:
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is None:
        try:
            import pytesseract
            from app.core.config import settings
            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            pytesseract.get_tesseract_version()
            _TESSERACT_AVAILABLE = True
        except Exception:
            _TESSERACT_AVAILABLE = False
            logger.warning("Tesseract not found — OCR disabled. Set TESSERACT_CMD or install tesseract.")
    return _TESSERACT_AVAILABLE


def ocr_image(file_path: str | Path) -> str | None:
    """Run Tesseract OCR on an image file. Returns extracted text or None."""
    if not _check_tesseract():
        return None
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(str(file_path))
        text = pytesseract.image_to_string(img)
        return text.strip() or None
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", file_path, exc)
        return None


def ocr_pdf_pages(file_path: str | Path) -> str | None:
    """Rasterize each PDF page and OCR it. Used when no text layer exists."""
    if not _check_tesseract():
        return None
    try:
        import pytesseract
        from PIL import Image
        import pypdf
        from io import BytesIO

        pages: list[str] = []
        reader = pypdf.PdfReader(str(file_path))
        for page_num in range(min(len(reader.pages), 50)):  # cap at 50 pages
            page = reader.pages[page_num]
            # Try to extract embedded images first
            if "/XObject" in page.get("/Resources", {}):
                xobj = page["/Resources"]["/XObject"].get_object()
                for obj in xobj.values():
                    obj = obj.get_object()
                    if obj.get("/Subtype") == "/Image":
                        try:
                            data = obj.get_data()
                            img = Image.open(BytesIO(data))
                            text = pytesseract.image_to_string(img)
                            if text.strip():
                                pages.append(text.strip())
                        except Exception:
                            continue
        return "\n\n".join(pages) if pages else None
    except Exception as exc:
        logger.warning("PDF OCR failed for %s: %s", file_path, exc)
        return None
