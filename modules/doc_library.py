import os
import json

# =============================================
# 📁 Document Library Module
# Fix #6: persist library to JSON so docs
# survive app restarts, and clean up stale
# ChromaDB entries on startup
# =============================================

LIBRARY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "library.json")

library = {}
active_doc = {"filename": ""}


def _save_library():
    """Persist library metadata (not full text) to disk."""
    try:
        os.makedirs(os.path.dirname(LIBRARY_PATH), exist_ok=True)
        data = {
            "active": active_doc["filename"],
            "docs": {
                fn: {
                    "pages": info["pages"],
                    "words": info["words"],
                    "chunks_count": len(info["chunks"]),
                }
                for fn, info in library.items()
            }
        }
        with open(LIBRARY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save library metadata: {e}")


def add_document(filename: str, text: str, chunks: list, pages: int):
    """Add or update a document in the library."""
    library[filename] = {
        "text": text,
        "chunks": chunks,
        "pages": pages,
        "words": len(text.split()),
    }
    if not active_doc["filename"]:
        active_doc["filename"] = filename
    _save_library()


def set_active(filename: str):
    """Switch active document."""
    if filename in library:
        active_doc["filename"] = filename
        _save_library()
        return True
    return False


def remove_document(filename: str):
    """Remove a document from the library."""
    if filename in library:
        del library[filename]
        if active_doc["filename"] == filename:
            if library:
                active_doc["filename"] = list(library.keys())[0]
            else:
                active_doc["filename"] = ""
        _save_library()


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


def get_library_metadata() -> dict:
    """
    Fix #6: returns saved metadata (pages/words) for UI display
    without needing the full text in memory.
    """
    try:
        if os.path.exists(LIBRARY_PATH):
            with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def render_library_html() -> str:
    if not library:
        return """
        <div style="display:flex;justify-content:center;align-items:center;min-height:120px;
                    border:2px dashed #334155;border-radius:16px;color:#64748b;
                    font-family:'Segoe UI',sans-serif;font-size:15px;">
          No documents yet — upload PDFs or DOCX in the 📚 Library tab
        </div>"""

    EXT_STYLES = {
        "PDF":  ("#185FA5", "#E6F1FB"),
        "DOCX": ("#0F6E56", "#E1F5EE"),
    }

    cards_html = ""
    for fname, info in library.items():
        is_active = fname == active_doc["filename"]
        ext    = fname.rsplit(".", 1)[-1].upper() if "." in fname else "FILE"
        tc, bc = EXT_STYLES.get(ext, ("#5F5E5A", "#F1EFE8"))
        border = "border:2px solid #4F46E5;" if is_active else "border:1px solid #334155;"
        active_badge = (
            "<span style='background:#4F46E5;color:#e0dfff;border-radius:20px;"
            "padding:2px 10px;font-size:11px;font-weight:700;margin-left:8px;'>ACTIVE</span>"
            if is_active else ""
        )
        cards_html += f"""
        <div style="background:#1e293b;{border}border-radius:14px;padding:16px 20px;
                    margin-bottom:10px;font-family:'Segoe UI',sans-serif;">
          <div style="display:flex;align-items:flex-start;gap:10px;">
            <span style="background:{bc};color:{tc};font-size:10px;font-weight:700;
                         padding:3px 8px;border-radius:5px;flex-shrink:0;margin-top:2px;">{ext}</span>
            <div style="flex:1;min-width:0;">
              <div style="color:#f1f5f9;font-weight:600;font-size:14px;
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {fname}{active_badge}
              </div>
              <div style="color:#64748b;font-size:12px;margin-top:3px;">
                {info['pages']} pages &nbsp;·&nbsp; {info['words']:,} words &nbsp;·&nbsp; {len(info['chunks'])} chunks
              </div>
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
