import json
import os
import html as _html

from modules.runtime_paths import (
    atomic_write_json,
    code_dir,
    data_dir,
    log,
    read_json_with_recovery,
)


LIBRARY_SNAPSHOT_PATH = data_dir() / "library.json"


# ── Code sidecar storage ─────────────────────────────────────
#
# Raw `text` was removed from the snapshot because a 150K-word document
# produced ~900KB of JSON. `code_text` then reintroduced exactly that bug for
# source files: full text held in RAM for the whole session AND written into
# library.json on every save. Chunking destroys indentation and duplicates the
# overlap, so it cannot be reconstructed from chunks — the text is instead
# written once to data/code/<doc_id>.txt and read back on demand.

def code_sidecar_path(doc_id: str):
    return code_dir() / f"{doc_id}.txt"


def save_code_text(doc_id: str, code_text: str) -> str:
    """Persist a code file's full source. Returns "" if nothing was written."""
    if not code_text:
        return ""
    try:
        path = code_sidecar_path(doc_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(code_text)
        return str(path)
    except Exception as exc:
        log(f"⚠️ Could not store code text for {doc_id}: {exc}")
        return ""


def load_code_text(info: dict) -> str:
    """Read a code file's source back from its sidecar. "" if unavailable."""
    if not isinstance(info, dict):
        return ""
    inline = info.get("code_text") or ""
    if inline:
        return inline
    doc_id = info.get("id") or ""
    if not doc_id:
        return ""
    try:
        path = code_sidecar_path(doc_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
    except Exception as exc:
        log(f"⚠️ Could not read code text for {doc_id}: {exc}")
    return ""


def delete_code_text(doc_id: str) -> None:
    try:
        path = code_sidecar_path(doc_id)
        if path.exists():
            path.unlink()
    except Exception as exc:
        log(f"⚠️ Could not delete code text for {doc_id}: {exc}")

RK_SURFACE_1 = "var(--rk-surface-1, #1e293b)"
RK_BORDER_STRONG = "var(--rk-border-strong, #334155)"
RK_TEXT = "var(--rk-text, #f1f5f9)"
RK_TEXT_MUTED = "var(--rk-text-muted, #94a3b8)"
RK_TEXT_FAINT = "var(--rk-text-faint, #64748b)"
RK_PRIMARY = "var(--rk-primary, #4F46E5)"
RK_PRIMARY_SOFT = "var(--rk-primary-soft, #818cf8)"


def save_library_snapshot(library: dict, active_doc_id: str = "") -> str:
    """
    Persist the library to disk. Raw document text is intentionally excluded —
    chunks already contain all the content needed to re-index and answer questions.
    Code source is stored in a sidecar file rather than inline (see above).

    Written atomically: open(path, "w") truncates the target first, so a crash
    or full disk mid-dump previously left a truncated library.json that the
    loader silently discarded, taking the whole library with it.

    Returns "" on success, or a human-readable error for the UI.
    """
    try:
        docs = []
        for doc_id, info in (library or {}).items():
            entry = {
                "id":         doc_id,
                "filename":   info.get("filename", ""),
                # "text" deliberately omitted — not needed after indexing
                "chunks":     info.get("chunks", []),
                "pages":      info.get("pages", 0),
                "unit_label": info.get("unit_label", "pages"),
                "words":      info.get("words", 0),
                "is_code":    bool(info.get("is_code") or info.get("code_text")),
            }
            # Migration path: an entry still carrying inline code_text from an
            # older snapshot gets flushed to its sidecar on the next save.
            inline_code = info.get("code_text") or ""
            if inline_code:
                save_code_text(doc_id, inline_code)
            docs.append(entry)

        payload = {
            "active_doc_id": active_doc_id or "",
            "docs": docs,
        }
        atomic_write_json(LIBRARY_SNAPSHOT_PATH, payload)
        return ""
    except Exception as exc:
        log(f"⚠️ Could not save library snapshot: {exc}")
        return f"Library could not be saved to disk: {exc}"


def load_library_snapshot() -> tuple[dict, str, str]:
    """
    Returns (library, active_doc_id, error_message).

    error_message is "" on a clean load. It is non-empty when library.json was
    unreadable — previously that case returned an empty library and only
    printed to a console nobody reads, so a corrupt snapshot looked identical
    to a fresh install.
    """
    payload, error = read_json_with_recovery(LIBRARY_SNAPSHOT_PATH, default=None)
    if payload is None:
        return {}, "", error

    try:
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
                # Read from the sidecar on demand, never held in session RAM.
                "code_text":  "",
                "is_code":    bool(item.get("is_code") or item.get("code_text")),
            }
            # Legacy snapshots stored the source inline; migrate it out.
            legacy_code = item.get("code_text") or ""
            if legacy_code:
                save_code_text(doc_id, legacy_code)

        active_doc_id = payload.get("active_doc_id", "")
        if active_doc_id not in library and library:
            active_doc_id = next(iter(library))
        return library, active_doc_id, error
    except Exception as exc:
        log(f"⚠️ Could not load library snapshot: {exc}")
        return {}, "", f"Library snapshot could not be read ({exc})."


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
