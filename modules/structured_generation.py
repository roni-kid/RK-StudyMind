import json
import re
from typing import Any, Callable


RECOVERY_NOTE = "AI output repaired for stability"


def make_result(ok: bool, data: dict | None = None, status: str = "clean",
                note: str = "", counts: dict | None = None) -> dict:
    return {
        "ok": bool(ok),
        "data": data or {},
        "status": status,
        "note": note,
        "counts": counts or {},
    }


def note_for_status(status: str) -> str:
    if status in {"retried", "repaired", "legacy_fallback", "partial"}:
        return RECOVERY_NOTE
    return ""


def clean_text(value: Any, limit: int | None = None) -> str:
    text = str(value or "")
    text = re.sub(r'[\*_`]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip(" \t\r\n:-")
    if limit and len(text) > limit:
        text = text[:limit - 1].rstrip() + "..."
    return text


def normalize_key(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def extract_json_value(raw: str) -> Any:
    """
    Pull the first valid JSON object/array out of model output.
    Handles fenced JSON and prose-wrapped JSON without trusting surrounding text.
    """
    raw = str(raw or "").strip()
    if not raw:
        return None

    fenced = re.search(r'```(?:json)?\s*(.*?)```', raw, flags=re.I | re.S)
    candidates = [fenced.group(1).strip()] if fenced else []
    candidates.append(raw)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            pass
        for idx, char in enumerate(candidate):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[idx:])
                return value
            except Exception:
                continue
    return None


def dedupe_by(items: list[dict], key_fn: Callable[[dict], str]) -> tuple[list[dict], int]:
    seen = set()
    kept = []
    dropped = 0
    for item in items:
        key = key_fn(item)
        if not key:
            dropped += 1
            continue
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(item)
    return kept, dropped


def existing_items_block(items: list[dict], field: str = "question", limit: int = 20) -> str:
    values = [clean_text(item.get(field, "")) for item in items if clean_text(item.get(field, ""))]
    if not values:
        return ""
    clipped = values[-limit:]
    return "\nAlready accepted. Do not repeat or rephrase these:\n" + "\n".join(f"- {value}" for value in clipped)
