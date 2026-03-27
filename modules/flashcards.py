import json
import re
from modules.ai_engine import ask_lmstudio

# =============================================
# 🃏 Flashcard Generation Module
# Batched generation — supports up to 40 cards reliably
# =============================================

BATCH_SIZE = 10

def generate_flashcards(text: str, filename: str, num_cards: int = 10) -> list:
    """
    Generates flashcards in batches of 10 using a while loop.
    Retries each batch up to 2 times if it returns fewer cards than expected.
    """
    words = text.split()
    context = " ".join(words[:4000])  # increased context window

    all_cards = []
    max_attempts = (num_cards // BATCH_SIZE + 2) * 3  # safety cap on total attempts
    attempts = 0

    while len(all_cards) < num_cards and attempts < max_attempts:
        remaining = num_cards - len(all_cards)
        to_generate = min(BATCH_SIZE, remaining)
        cards = _generate_batch(context, to_generate, start_index=len(all_cards) + 1)
        if cards:
            all_cards.extend(cards)
        attempts += 1

    return all_cards[:num_cards] if all_cards else [
        {"question": "⚠️ Generation failed",
         "answer": "Could not generate flashcards. Try a different document or model."}
    ]


def _generate_batch(context: str, num_cards: int, start_index: int = 1) -> list:
    """Generates a single batch of up to 10 flashcards."""
    prompt = f"""Read the following document and create exactly {num_cards} study flashcards.

Use EXACTLY this format:
{start_index}. Q: [question here]
   A: [answer here]

{start_index + 1}. Q: [question here]
   A: [answer here]

Rules:
- Questions must be specific and based only on the document
- Answers must be short and clear (1-2 sentences max)
- No extra text, headers, or explanations
- Start immediately with "{start_index}. Q:"

Document:
{context}

Flashcards:"""

    raw = ask_lmstudio(prompt=prompt, context="")
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
    except Exception:
        pass
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
