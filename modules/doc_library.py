import json
import os
import html as _html


LIBRARY_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "library.json",
)


def save_library_snapshot(library: dict, active_doc_id: str = "") -> None:
    try:
        os.makedirs(os.path.dirname(LIBRARY_SNAPSHOT_PATH), exist_ok=True)
        docs = []
        for doc_id, info in (library or {}).items():
            docs.append({
                "id": doc_id,
                "filename": info.get("filename", ""),
                "text": info.get("text", ""),
                "chunks": info.get("chunks", []),
                "pages": info.get("pages", 0),
                "unit_label": info.get("unit_label", "pages"),
                "words": info.get("words", 0),
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
                "id": doc_id,
                "filename": item.get("filename", doc_id),
                "text": item.get("text", ""),
                "chunks": item.get("chunks", []),
                "pages": item.get("pages", 0),
                "unit_label": item.get("unit_label", "pages"),
                "words": item.get("words", 0),
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
        return """
        <div style="display:flex;justify-content:center;align-items:center;min-height:120px;
                    border:2px dashed #334155;border-radius:16px;color:#64748b;
                    font-family:'Segoe UI',sans-serif;font-size:15px;">
          No documents yet — upload PDF, DOCX, TXT, MD, PPTX, or EPUB in the 📚 Library tab
        </div>"""

    EXT_STYLES = {
        "PDF":  ("#185FA5", "#E6F1FB"),
        "DOCX": ("#0F6E56", "#E1F5EE"),
        "TXT":  ("#9A6700", "#FFF3CD"),
        "MD":   ("#7C3AED", "#EFE3FF"),
        "PPTX": ("#C2410C", "#FEE7D6"),
        "EPUB": ("#166534", "#DCFCE7"),
    }

    cards_html = ""
    for doc_id, info in lib.items():
        fname = info.get("filename", doc_id)
        is_active = doc_id == active_key
        safe_fname = _html.escape(fname)
        ext    = fname.rsplit(".", 1)[-1].upper() if "." in fname else "FILE"
        tc, bc = EXT_STYLES.get(ext, ("#5F5E5A", "#F1EFE8"))
        border = "border:2px solid #4F46E5;" if is_active else "border:1px solid #334155;"
        active_badge = (
            "<span style='background:#4F46E5;color:#e0dfff;border-radius:20px;"
            "padding:2px 10px;font-size:11px;font-weight:700;margin-left:8px;'>ACTIVE</span>"
            if is_active else ""
        )
        unit_label = info.get("unit_label", "pages")
        cards_html += f"""
        <div style="background:#1e293b;{border}border-radius:14px;padding:16px 20px;
                    margin-bottom:10px;font-family:'Segoe UI',sans-serif;">
          <div style="display:flex;align-items:flex-start;gap:10px;">
            <span style="background:{bc};color:{tc};font-size:10px;font-weight:700;
                         padding:3px 8px;border-radius:5px;flex-shrink:0;margin-top:2px;">{ext}</span>
            <div style="flex:1;min-width:0;">
              <div style="color:#f1f5f9;font-weight:600;font-size:14px;
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {safe_fname}{active_badge}
              </div>
              <div style="color:#64748b;font-size:12px;margin-top:3px;">
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
      <div style="color:#94a3b8;font-size:12px;margin-bottom:10px;">
        {len(lib)} document(s) in library &nbsp;·&nbsp;
        Active: <strong style="color:#818cf8;">{safe_active}</strong>
      </div>
      {cards_html}
    </div>"""
