import json
import re
from typing import Any, Callable

from modules.ai_engine import is_lmstudio_error, wrap_untrusted_context  # noqa: F401


RECOVERY_NOTE = "AI output repaired for stability"

# Cap on how many candidate "{"/"[" positions the raw_decode rescue scan will
# try. Each attempt is O(n), so an unbounded scan over a long malformed
# response is O(n^2). 400 starting points is far more than any real payload
# needs and bounds the worst case.
_MAX_DECODE_SCAN_POSITIONS = 400


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


# Typographic/smart quote characters some local models substitute for straight
# quotes in JSON output — left-double, right-double, left-single, right-single.
# json.loads() only ever accepts straight " for string delimiters. Only quotes
# sitting directly adjacent to JSON structural syntax (right after `: ` or right
# before `,`/`}`/`]`) are rewritten — that is where a model is using them AS a
# delimiter substitute. Curly quotes used decoratively *inside* string content
# (e.g. quoting a phrase within spoken dialogue) are left untouched, since
# rewriting those would prematurely close the string instead of fixing anything.
def _normalize_smart_quotes(text: str) -> str:
    text = re.sub(r'(:\s*)[\u201c\u2018]', r'\1"', text)
    text = re.sub(r'[\u201d\u2019](\s*[,}\]])', r'"\1', text)
    return text


def extract_json_value(raw: str) -> Any:
    """
    Pull the first valid JSON object/array out of model output.
    Handles fenced JSON and prose-wrapped JSON without trusting surrounding text.
    Local LLMs (observed: gemma-3-4b) intermittently emit curly/typographic quote
    characters instead of straight quotes when generating longer, more natural-
    sounding dialogue text — these are never valid JSON string delimiters, so they
    are normalized to straight quotes before every parse attempt.
    """
    raw = str(raw or "").strip()
    if not raw:
        return None

    raw = _normalize_smart_quotes(raw)

    fenced = re.search(r'```(?:json)?\s*(.*?)```', raw, flags=re.I | re.S)
    candidates = [fenced.group(1).strip()] if fenced else []
    candidates.append(raw)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            pass
        # Scan for the first `{`/`[` and try raw_decode from there. A genuinely
        # malformed response can still yield a *partial* successful parse if
        # raw_decode manages to decode an inner nested object before the real
        # syntax error further along — e.g. matching just {"metadata": {...}}
        # instead of the full {"metadata": ..., "turns": [...]}. Keep scanning
        # and prefer whichever successful match consumes the most characters,
        # since the largest valid parse is the one most likely to be the
        # intended top-level structure rather than an accidental inner match.
        best_value = None
        best_span = -1
        scanned = 0
        for idx, char in enumerate(candidate):
            if char not in "[{":
                continue
            scanned += 1
            if scanned > _MAX_DECODE_SCAN_POSITIONS:
                break
            try:
                value, end = decoder.raw_decode(candidate[idx:])
            except Exception:
                continue
            if end > best_span:
                best_value = value
                best_span = end
        if best_value is not None:
            return best_value
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


def untrusted_document_block(context: str) -> str:
    """
    Shared wrapper for document text that generation modules paste into their
    own prompts. quiz/flashcards/mindmap/coding_agent previously called
    ask_lmstudio(context="") and inlined the document body with only a one-line
    "treat as untrusted" hint, which is a weaker and inconsistently-positioned
    mitigation than the delimited block ask_lmstudio() uses for its own
    `context` argument. This routes them all through the same construct.
    """
    return wrap_untrusted_context(context)
