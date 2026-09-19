import json
import re
import time
from modules.ai_engine import LMStudioError, ask_lmstudio, is_lmstudio_error
from modules.runtime_paths import log
from modules.study_context import build_balanced_context
from modules.structured_generation import (
    clean_text,
    dedupe_by,
    existing_items_block,
    extract_json_value,
    make_result,
    normalize_key,
    note_for_status,
    untrusted_document_block,
)


def _ask(prompt: str, **kwargs) -> str:
    """Raise on LM Studio transport errors instead of treating them as content."""
    raw = ask_lmstudio(prompt=prompt, **kwargs)
    if is_lmstudio_error(raw):
        raise LMStudioError(str(raw).strip())
    return raw

# =============================================
# 🃏 Flashcard Generation Module
# Fix #2: deduplication across batches
# =============================================

BATCH_SIZE = 10
MAX_FLASHCARDS = 30

# See quiz.py — the attempt budget alone allowed a multi-hour frozen UI.
GENERATION_BUDGET_SECONDS = 180
MAX_CONSECUTIVE_EMPTY = 6

DIFFICULTY_RULES = {
    "Easy": "Create direct, simple recall cards with short answers.",
    "Medium": "Create balanced study cards that mix recall with light understanding.",
    "Hard": "Create more specific cards that require connecting ideas or distinguishing similar concepts.",
    "Difficult": "Create challenging cards that test nuanced understanding, precision, and deeper recall.",
}

def generate_flashcards_result(text: str = "", filename: str = "", num_cards: int = 10,
                               chunks: list[str] | None = None,
                               difficulty: str = "Medium") -> dict:
    """
    Generates validated flashcards with JSON as the primary model contract.
    If duplicates or invalid cards are removed, it asks for only the missing count.
    """
    # Use adaptive context limit so small models never overflow
    try:
        from modules.adaptive_chunking import adaptive_strategy
        ctx_words = min(adaptive_strategy.detect_model()["context_max_words"], 5000)
    except Exception:
        ctx_words = 3500
    context = build_balanced_context(chunks or [text], max_words=ctx_words, target_chunks=12)
    difficulty = difficulty if difficulty in DIFFICULTY_RULES else "Medium"

    requested = max(1, min(int(num_cards), MAX_FLASHCARDS))
    all_cards = []
    dropped_total = 0
    used_retry = False
    used_legacy = False
    max_attempts = (requested // BATCH_SIZE + 2) * 3
    attempts = 0
    consecutive_empty = 0  # tracks back-to-back batches that added nothing new
    started = time.monotonic()
    transport_error = ""
    timed_out = False

    while len(all_cards) < requested and attempts < max_attempts:
        if time.monotonic() - started > GENERATION_BUDGET_SECONDS:
            timed_out = True
            log(f"[flashcards.py] Generation budget of {GENERATION_BUDGET_SECONDS}s reached — stopping")
            break
        remaining = requested - len(all_cards)
        to_generate = min(BATCH_SIZE, remaining)
        try:
            raw_cards = _generate_json_batch(
                context=context,
                num_cards=to_generate,
                existing_cards=all_cards,
                difficulty=difficulty,
                retry=attempts > 0,
            )
            if attempts > 0:
                used_retry = True
            if not raw_cards:
                raw_cards = _generate_batch(
                    context=context,
                    num_cards=to_generate,
                    start_index=len(all_cards) + 1,
                    existing_questions=[c["question"] for c in all_cards],
                    difficulty=difficulty,
                )
                used_legacy = True
        except LMStudioError as exc:
            transport_error = str(exc)
            log(f"[flashcards.py] Aborting generation — LM Studio transport error: {exc}")
            break

        old_count = len(all_cards)
        merged, dropped = _merge_cards(all_cards, raw_cards, requested)
        dropped_total += dropped
        all_cards = merged
        added = len(all_cards) - old_count
        attempts += 1

        # Stop early once most of the attempt budget is spent on batches that
        # added nothing new (model stuck returning duplicates). Mirrors the
        # quiz.py safeguard so a slow local model doesn't burn every remaining
        # attempt on repeated LM Studio calls that can't produce fresh cards.
        if added == 0:
            consecutive_empty += 1
            if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                log(f"[flashcards.py] {consecutive_empty} consecutive empty batches — stopping early")
                break
        else:
            consecutive_empty = 0

    if not all_cards:
        return make_result(
            False,
            {"cards": []},
            "failed",
            (f"LM Studio problem: {transport_error}" if transport_error else
             "Could not generate any flashcards — try a different document or a larger/more capable model."),
            {"requested": requested, "returned": 0, "dropped": dropped_total},
        )

    status = "clean"
    if len(all_cards) < requested:
        status = "partial"
    elif used_legacy:
        status = "legacy_fallback"
    elif used_retry or dropped_total:
        status = "repaired"

    note = note_for_status(status)
    if transport_error:
        note = f"Stopped early — LM Studio problem: {transport_error}"
    elif timed_out and status == "partial":
        note = (f"Stopped after {GENERATION_BUDGET_SECONDS}s — got {len(all_cards)}/{requested} cards. "
                "A faster model, or fewer cards, will complete the set.")
    elif status == "partial":
        note = f"Only {len(all_cards)}/{requested} flashcards could be generated — the document may not have enough distinct content, or try a larger model."

    return make_result(
        True,
        {"cards": all_cards[:requested]},
        status,
        note,
        {"requested": requested, "returned": min(len(all_cards), requested), "dropped": dropped_total},
    )

def _merge_cards(existing: list[dict], new_cards: list[dict], requested: int) -> tuple[list[dict], int]:
    valid = existing + _validate_cards(new_cards)
    deduped, dropped = dedupe_by(valid, lambda card: normalize_key(card.get("question", "")))
    return deduped[:requested], dropped


def _validate_cards(cards: list[dict]) -> list[dict]:
    valid = []
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        question = clean_text(card.get("question") or card.get("Q") or card.get("q"), limit=220)
        answer = clean_text(card.get("answer") or card.get("A") or card.get("a"), limit=420)
        topic = clean_text(card.get("topic") or card.get("category") or "General", limit=60) or "General"
        if len(question) < 6 or len(answer) < 2:
            continue
        valid.append({"question": question, "answer": answer, "topic": topic})
    return valid


def _generate_json_batch(context: str, num_cards: int, existing_cards: list[dict] | None = None,
                         difficulty: str = "Medium", retry: bool = False) -> list:
    difficulty_rule = DIFFICULTY_RULES.get(difficulty, DIFFICULTY_RULES["Medium"])
    existing_block = existing_items_block(existing_cards or [], field="question", limit=25)
    retry_line = "This is a repair request. Return replacements only for the missing cards." if retry else ""
    document_block = untrusted_document_block(context)
    prompt = f"""Extract exactly {num_cards} NEW study flashcards from the document.
{retry_line}
{existing_block}

Return ONLY valid JSON in this shape:
{{
  "cards": [
    {{"question": "specific question", "answer": "brief accurate answer", "topic": "short topic"}}
  ]
}}

Rules:
- Return exactly {num_cards} cards
- Questions must be unique and based only on the document
- Answers must be short and clear
- Difficulty: {difficulty}. {difficulty_rule}
- No Markdown, no prose, no code fences

{document_block}"""

    raw = _ask(prompt, context="", temperature=0.2)
    value = extract_json_value(raw)
    if isinstance(value, dict):
        return _validate_cards(value.get("cards", []))
    if isinstance(value, list):
        return _validate_cards(value)
    return []


def _generate_batch(context: str, num_cards: int, start_index: int = 1,
                    existing_questions: list = None, difficulty: str = "Medium") -> list:
    """Generates a single batch, avoiding previously generated questions."""

    # Build avoidance block so model doesn't repeat earlier cards
    avoid_block = ""
    if existing_questions:
        avoid_list = "\n".join(f"- {q}" for q in existing_questions[-20:])  # show last 20
        avoid_block = f"\nDo NOT repeat any of these already-generated questions:\n{avoid_list}\n"
    difficulty_rule = DIFFICULTY_RULES.get(difficulty, DIFFICULTY_RULES["Medium"])

    document_block = untrusted_document_block(context)
    prompt = f"""Read the following document and create exactly {num_cards} NEW study flashcards.
{avoid_block}
Use EXACTLY this format:
{start_index}. Q: [question here]
   A: [answer here]

Rules:
- Questions must be specific and based only on the document
- Answers must be short and clear (1-2 sentences max)
- No extra text, headers, or explanations
- Each question must be unique and different from those listed above
- Difficulty: {difficulty}. {difficulty_rule}
- Start immediately with "{start_index}. Q:"

{document_block}

Flashcards:"""

    raw = _ask(prompt, context="", temperature=0.2)
    cards = parse_numbered_format(raw, num_cards)
    if not cards:
        cards = parse_json_format(raw, num_cards)
    if not cards:
        cards = parse_loose_format(raw, num_cards)
    return cards


def parse_numbered_format(raw: str, num_cards: int) -> list:
    cards = []
    pattern = re.findall(
        r'Q[:\.]?\s*(.+?)\s*\n\s*A[:\.]?\s*(.+?)(?=\n\s*\d+\.|\n\s*Q[:\.]?|\Z)',
        raw, re.DOTALL | re.IGNORECASE
    )
    for q, a in pattern:
        q = q.strip().strip('"').strip("*").strip()
        a = a.strip().strip('"').strip("*").strip()
        if q and a and len(q) > 5:
            cards.append({"question": q, "answer": a})
        if len(cards) >= num_cards:
            break
    return cards


def parse_json_format(raw: str, num_cards: int) -> list:
    try:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            cards_raw = json.loads(match.group(0))
            valid = []
            for c in cards_raw:
                if isinstance(c, dict):
                    q = c.get("question") or c.get("Q") or c.get("q", "")
                    a = c.get("answer") or c.get("A") or c.get("a", "")
                    if q and a:
                        valid.append({"question": str(q).strip(), "answer": str(a).strip()})
            return valid[:num_cards]
    except Exception as e:
        log(f"⚠️ Could not parse flashcard JSON response: {e}")
    return []


def parse_loose_format(raw: str, num_cards: int) -> list:
    cards = []
    lines = raw.strip().splitlines()
    current_q = None
    for line in lines:
        line = line.strip().lstrip("0123456789.-) ")
        if re.match(r'^(Q|Question)[:\.]', line, re.IGNORECASE):
            current_q = re.sub(r'^(Q|Question)[:\.]?\s*', '', line, flags=re.IGNORECASE).strip()
        elif re.match(r'^(A|Answer)[:\.]', line, re.IGNORECASE) and current_q:
            answer = re.sub(r'^(A|Answer)[:\.]?\s*', '', line, flags=re.IGNORECASE).strip()
            if answer:
                cards.append({"question": current_q, "answer": answer})
                current_q = None
        if len(cards) >= num_cards:
            break
    return cards
