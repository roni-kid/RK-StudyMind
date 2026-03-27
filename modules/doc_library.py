import os
import json

# =============================================
# 📁 Document Library Module
# Manages multiple uploaded PDFs in memory
# =============================================

# In-memory library: {filename: {text, chunks, pages, words}}
library = {}
active_doc = {"filename": ""}


def add_document(filename: str, text: str, chunks: list, pages: int):
    """Add or update a document in the library."""
    library[filename] = {
        "text": text,
        "chunks": chunks,
        "pages": pages,
        "words": len(text.split()),
    }
    # Auto-set as active if it's the first doc
    if not active_doc["filename"]:
        active_doc["filename"] = filename


def set_active(filename: str):
    """Switch active document."""
    if filename in library:
        active_doc["filename"] = filename
        return True
    return False


def remove_document(filename: str):
    """Remove a document from the library."""
    if filename in library:
        del library[filename]
        # If we removed the active doc, switch to another
        if active_doc["filename"] == filename:
            if library:
                active_doc["filename"] = list(library.keys())[0]
            else:
                active_doc["filename"] = ""


def get_active_text() -> str:
    fn = active_doc["filename"]
    return library[fn]["text"] if fn in library else ""


def get_active_chunks() -> list:
    fn = active_doc["filename"]
    return library[fn]["chunks"] if fn in library else []


def get_active_filename() -> str:
    return active_doc["filename"]


def get_all_filenames() -> list:
    return list(library.keys())


def get_doc_info(filename: str) -> dict:
    return library.get(filename, {})


def render_library_html() -> str:
    """Renders the document library as HTML cards."""
    if not library:
        return """
        <div style="display:flex;justify-content:center;align-items:center;min-height:120px;
                    border:2px dashed #334155;border-radius:16px;color:#64748b;
                    font-family:'Segoe UI',sans-serif;font-size:15px;">
          No documents yet — upload PDFs in the 📄 PDF Reader tab
        </div>"""

    cards_html = ""
    for fname, info in library.items():
        is_active = fname == active_doc["filename"]
        border = "border:2px solid #4F46E5;" if is_active else "border:2px solid #1e293b;"
        badge = "<span style='background:#4F46E5;color:#fff;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700;margin-left:8px;'>ACTIVE</span>" if is_active else ""
        cards_html += f"""
        <div style="background:#1e293b;{border}border-radius:14px;padding:16px 20px;margin-bottom:10px;
                    font-family:'Segoe UI',sans-serif;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="color:#f1f5f9;font-weight:600;font-size:15px;">📄 {fname} {badge}</div>
            <div style="color:#64748b;font-size:12px;margin-top:4px;">
              {info['pages']} pages &nbsp;·&nbsp; {info['words']:,} words &nbsp;·&nbsp; {len(info['chunks'])} chunks
            </div>
          </div>
        </div>"""

    return f"""
    <div style="font-family:'Segoe UI',sans-serif;">
      <div style="color:#94a3b8;font-size:12px;margin-bottom:10px;">
        {len(library)} document(s) in library &nbsp;·&nbsp;
        Active: <strong style="color:#818cf8;">{active_doc['filename'] or 'None'}</strong>
      </div>
      {cards_html}
    </div>"""
