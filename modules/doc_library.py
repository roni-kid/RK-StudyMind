import json
import os
import html as _html


LIBRARY_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "library.json",
)

RK_SURFACE_1 = "var(--rk-surface-1, #1e293b)"
RK_BORDER_STRONG = "var(--rk-border-strong, #334155)"
RK_TEXT = "var(--rk-text, #f1f5f9)"
RK_TEXT_MUTED = "var(--rk-text-muted, #94a3b8)"
RK_TEXT_FAINT = "var(--rk-text-faint, #64748b)"
RK_PRIMARY = "var(--rk-primary, #4F46E5)"
RK_PRIMARY_SOFT = "var(--rk-primary-soft, #818cf8)"


def save_library_snapshot(library: dict, active_doc_id: str = "") -> None:
    """
    Persist the library to disk. Raw document text is intentionally excluded —
    chunks already contain all the content needed to re-index and answer questions.
    Omitting text keeps snapshot files small even for 150K-word documents.
    """
    try:
        os.makedirs(os.path.dirname(LIBRARY_SNAPSHOT_PATH), exist_ok=True)
        docs = []
        for doc_id, info in (library or {}).items():
            docs.append({
                "id":         doc_id,
                "filename":   info.get("filename", ""),
                # "text" deliberately omitted — not needed after indexing
                "chunks":     info.get("chunks", []),
                "pages":      info.get("pages", 0),
                "unit_label": info.get("unit_label", "pages"),
                "words":      info.get("words", 0),
                "code_text":  info.get("code_text", ""),
            })
        payload = {
            "active_doc_id": active_doc_id or "",
            "docs": docs,
        }
        with open(LIBRARY_SNAPSHOT_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    except Exception as exc:
        print(f"⚠️ Could not save library snapshot: {exc}")


def load_library_snapshot() -> tuple[dict, str]:
    try:
        if not os.path.exists(LIBRARY_SNAPSHOT_PATH):
            return {}, ""
        with open(LIBRARY_SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        library = {}
        for item in payload.get("docs", []):
            doc_id = item.get("id")
            if not doc_id:
                continue
            library[doc_id] = {
                "id":         doc_id,
                "filename":   item.get("filename", doc_id),
                "text":       "",   # not persisted — chunks are sufficient
                "chunks":     item.get("chunks", []),
                "pages":      item.get("pages", 0),
                "unit_label": item.get("unit_label", "pages"),
                "words":      item.get("words", 0),
                "code_text":  item.get("code_text", ""),
            }
        active_doc_id = payload.get("active_doc_id", "")
        if active_doc_id not in library and library:
            active_doc_id = next(iter(library))
        return library, active_doc_id
    except Exception as exc:
        print(f"⚠️ Could not load library snapshot: {exc}")
        return {}, ""


def render_library_html(lib: dict = None, active_doc_id: str = None) -> str:
    lib = {} if lib is None else lib
    active_key = active_doc_id or ""

    if not lib:
        return f"""
        <div style="display:flex;justify-content:center;align-items:center;min-height:120px;
                    border:2px dashed {RK_BORDER_STRONG};border-radius:16px;color:{RK_TEXT_FAINT};
                    font-family:'Segoe UI',sans-serif;font-size:15px;">
          No documents yet — upload PDF, DOCX, TXT, MD, PPTX, EPUB, or code files in the 📚 Library tab
        </div>"""

    EXT_STYLES = {
        "PDF":  ("#185FA5", "#E6F1FB"),
        "DOCX": ("#0F6E56", "#E1F5EE"),
        "TXT":  ("#9A6700", "#FFF3CD"),
        "MD":   ("#7C3AED", "#EFE3FF"),
        "PPTX": ("#C2410C", "#FEE7D6"),
        "EPUB": ("#166534", "#DCFCE7"),
        "PY":   ("#2563EB", "#DBEAFE"),
        "JS":   ("#854D0E", "#FEF3C7"),
        "TS":   ("#1D4ED8", "#DBEAFE"),
        "C":    ("#475569", "#E2E8F0"),
        "CPP":  ("#475569", "#E2E8F0"),
        "JAVA": ("#B45309", "#FFEDD5"),
        "HTML": ("#C2410C", "#FFEDD5"),
        "CSS":  ("#0E7490", "#CFFAFE"),
    }

    cards_html = ""
    for doc_id, info in lib.items():
        fname = info.get("filename", doc_id)
        is_active = doc_id == active_key
        safe_fname = _html.escape(fname)
        ext    = fname.rsplit(".", 1)[-1].upper() if "." in fname else "FILE"
        tc, bc = EXT_STYLES.get(ext, ("#5F5E5A", "#F1EFE8"))
        border = f"border:2px solid {RK_PRIMARY};" if is_active else f"border:1px solid {RK_BORDER_STRONG};"
        active_badge = (
            f"<span style='background:{RK_PRIMARY};color:#fff;border-radius:20px;"
            "padding:2px 10px;font-size:11px;font-weight:700;margin-left:8px;'>ACTIVE</span>"
            if is_active else ""
        )
        unit_label = info.get("unit_label", "pages")
        cards_html += f"""
        <div style="background:{RK_SURFACE_1};{border}border-radius:14px;padding:16px 20px;
                    margin-bottom:10px;font-family:'Segoe UI',sans-serif;">
          <div style="display:flex;align-items:flex-start;gap:10px;">
            <span style="background:{bc};color:{tc};font-size:10px;font-weight:700;
                         padding:3px 8px;border-radius:5px;flex-shrink:0;margin-top:2px;">{ext}</span>
            <div style="flex:1;min-width:0;">
              <div style="color:{RK_TEXT};font-weight:600;font-size:14px;
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {safe_fname}{active_badge}
              </div>
              <div style="color:{RK_TEXT_FAINT};font-size:12px;margin-top:3px;">
                {info.get('pages', 0)} {_html.escape(str(unit_label))} &nbsp;·&nbsp; {info.get('words', 0):,} words &nbsp;·&nbsp; {len(info.get('chunks', []))} chunks
              </div>
            </div>
          </div>
        </div>"""

    active_name = "None"
    if active_key and active_key in lib:
        active_name = lib[active_key].get("filename", active_key)
    safe_active = _html.escape(active_name)
    return f"""
    <div style="font-family:'Segoe UI',sans-serif;">
      <div style="color:{RK_TEXT_MUTED};font-size:12px;margin-bottom:10px;">
        {len(lib)} document(s) in library &nbsp;·&nbsp;
        Active: <strong style="color:{RK_PRIMARY_SOFT};">{safe_active}</strong>
      </div>
      {cards_html}
    </div>"""
