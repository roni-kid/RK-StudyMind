import fitz  # PyMuPDF

# =============================================
# 📄 PDF Reader Module
# Extracts clean text from uploaded PDFs
# =============================================

def read_pdf(file_path: str) -> str:
    """
    Takes a PDF file path and returns all its text as a single string.
    """
    try:
        doc = fitz.open(file_path)
        full_text = ""

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            full_text += f"\n--- Page {page_num} ---\n{text}"

        doc.close()

        if not full_text.strip():
            return "⚠️ This PDF appears to be empty or scanned (image-based). Text extraction not possible."

        return full_text.strip()

    except Exception as e:
        return f"❌ Error reading PDF: {str(e)}"


def get_page_count(file_path: str) -> int:
    """Returns the number of pages in a PDF."""
    try:
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except:
        return 0


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    Splits large text into smaller overlapping chunks.
    This helps the AI focus on relevant sections instead of the whole document.
    
    chunk_size = number of words per chunk
    overlap    = words shared between consecutive chunks (for context continuity)
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # slide forward with overlap

    return chunks
