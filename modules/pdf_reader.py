import fitz  # PyMuPDF
import os

# =============================================
# 📄 Document Reader Module
# Supports: PDF and DOCX files
# =============================================

def read_file(file_path: str) -> str:
    """
    Auto-detects file type and extracts text.
    Supports .pdf and .docx
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return read_pdf(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        return f"❌ Unsupported file type: {ext}. Please upload a PDF or DOCX file."


def read_pdf(file_path: str) -> str:
    """Extracts text from a PDF file, page by page."""
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            full_text += f"\n--- Page {page_num} ---\n{text}"
        doc.close()
        if not full_text.strip():
            return "⚠️ This PDF appears to be empty or scanned. Text extraction not possible."
        return full_text.strip()
    except Exception as e:
        return f"❌ Error reading PDF: {str(e)}"


def read_docx(file_path: str) -> str:
    """Extracts text from a DOCX file, paragraph by paragraph."""
    try:
        from docx import Document
        doc = Document(file_path)
        full_text = ""
        para_num = 0
        for para in doc.paragraphs:
            if para.text.strip():
                para_num += 1
                full_text += f"{para.text}\n"
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        full_text += f"{cell.text}\n"
        if not full_text.strip():
            return "⚠️ This DOCX appears to be empty. Text extraction not possible."
        return full_text.strip()
    except ImportError:
        return "❌ python-docx not installed. Run: pip install python-docx"
    except Exception as e:
        return f"❌ Error reading DOCX: {str(e)}"


def get_page_count(file_path: str) -> int:
    """
    Returns page count for PDFs, paragraph count for DOCX.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        try:
            doc = fitz.open(file_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 0
    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(file_path)
            # Count non-empty paragraphs as a proxy for "pages"
            count = sum(1 for p in doc.paragraphs if p.text.strip())
            return count
        except:
            return 0
    return 0


def get_page_label(file_path: str) -> str:
    """Returns 'pages' for PDF, 'paragraphs' for DOCX."""
    ext = os.path.splitext(file_path)[1].lower()
    return "paragraphs" if ext == ".docx" else "pages"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    Splits large text into smaller overlapping chunks.
    chunk_size = words per chunk
    overlap    = shared words between consecutive chunks
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
