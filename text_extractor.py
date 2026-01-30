"""
Phase A: Extract raw text from various input formats.

Supports:
  - Plain text / Markdown
  - PDF files (via PyPDF2)
"""

import io


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF file (Streamlit UploadedFile)."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        result = "\n\n".join(pages)
        print(f"[EXTRACT] PDF pages={len(reader.pages)}, chars={len(result)}")
        return result
    except ImportError:
        print("[EXTRACT][WARN] PyPDF2 not installed, trying pdfminer")
        raise
    except Exception as e:
        print(f"[EXTRACT][ERROR] PDF extraction failed: {e}")
        raise


def extract_text(source, source_type="text") -> str:
    """
    Unified text extraction.

    Args:
        source: Either a string (text/markdown) or a Streamlit UploadedFile (PDF).
        source_type: "text" or "pdf"

    Returns:
        Raw text string.
    """
    if source_type == "pdf":
        return extract_text_from_pdf(source)
    # Plain text or markdown – just return as-is
    text = source if isinstance(source, str) else source.read().decode("utf-8")
    print(f"[EXTRACT] text input, chars={len(text)}")
    return text
