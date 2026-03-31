import re
from modules.ai_engine import ask_lmstudio

# =============================================
# 📝 Smart Quiz Module — Resilient Parser
# Handles numbered, table, and loose formats
# =============================================

VALID_ANSWERS = ["A", "B", "C", "D"]

BATCH_SIZE = 3   # Questions per LLM call — small batches = higher reliability


def generate_quiz(text: str, num_questions: int = 5) -> list:
    """
    Generates quiz questions in small batches so the LLM never has to
    produce more than BATCH_SIZE questions per call.  Collects and
    deduplicates across batches until num_questions is reached.
    """
    words = text.split()
    context = " ".join(words[:4000])

    all_questions = []
    seen = set()
    max_attempts = (num_questions // BATCH_SIZE + 2) * 3  # safety cap
    attempts = 0
    consecutive_empty = 0  # tracks back-to-back batches that returned nothing

    while len(all_questions) < num_questions and attempts < max_attempts:
        remaining = num_questions - len(all_questions)
        to_gen    = min(BATCH_SIZE, remaining)
        start_num = len(all_questions) + 1

        batch = _generate_batch(
            context=context,
            num_q=to_gen,
            start_num=start_num,
            existing=[q['question'] for q in all_questions]
        )

        added = 0
        for q in batch:
            key = q['question'].lower().strip()
            if key not in seen:
                seen.add(key)
                all_questions.append(q)
                added += 1
            if len(all_questions) >= num_questions:
                break

        print(f"[quiz.py] Batch attempt {attempts+1}: got {len(batch)}, added {added}, total {len(all_questions)}/{num_questions}")
        attempts += 1

        # Track consecutive empty batches and stop if two in a row
        if added == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print("[quiz.py] Two consecutive empty batches — stopping early")
                break
        else:
            consecutive_empty = 0  # reset on any successful batch

    return all_questions[:num_questions]


def _generate_batch(context: str, num_q: int, start_num: int = 1,
                    existing: list = None) -> list:
    """Ask the LLM for a single small batch of questions."""
    avoid_block = ""
    if existing:
        avoid_list = "\n".join(f"- {q}" for q in existing[-10:])
        avoid_block = f"\nDo NOT repeat these already-generated questions:\n{avoid_list}\n"

    prompt = f"""Create exactly {num_q} multiple choice question(s) from the document below.
{avoid_block}
Use ONLY this exact format:

{start_num}. Q: [question text]
A: [option A]
B: [option B]
C: [option C]
D: [option D]
ANSWER: [A or B or C or D]
WHY: [one sentence explanation]

Rules:
- Base questions strictly on the document
- One correct answer per question
- ANSWER must be a single letter: A, B, C, or D
- Start immediately with "{start_num}. Q:"
- No extra text before or after

Document:
{context}

Quiz:"""

    raw = ask_lmstudio(prompt=prompt, context="")
    print(f"[quiz.py] Batch raw (first 500 chars):\n{raw[:500]}\n")
    questions = parse_quiz(raw, num_q)

    # Fallback if primary parse got nothing
    if not questions:
        print("[quiz.py] Primary parse failed — trying fallback")
        fallback = f"""Write {num_q} quiz question(s) about this text. Use this layout:

{start_num}. Q: [question]
A: [option]
B: [option]
C: [option]
D: [option]
ANSWER: [letter]

Text: {context[:1500]}

Start with "{start_num}. Q:":"""
        raw2 = ask_lmstudio(prompt=fallback, context="")
        questions = parse_quiz(raw2, num_q)

    return questions


def parse_quiz(raw: str, num_questions: int) -> list:
    """
    Resilient parser — tries three strategies in order:
    1. Standard numbered format  (1. Q: / A: / ANSWER: B)
    2. Markdown table format     (| 1 | question | A) ... | **B** |)
    3. Loose fallback            (any Q: / A: / ANSWER: pattern)
    """
    # ── Strategy 1: Standard numbered blocks ─────────────────────────────
    questions = _parse_numbered(raw, num_questions)
    if questions:
        print(f"[quiz.py] Strategy 1 (numbered) → {len(questions)} questions")
        return questions

    # ── Strategy 2: Markdown table ────────────────────────────────────────
    questions = _parse_table(raw, num_questions)
    if questions:
        print(f"[quiz.py] Strategy 2 (table) → {len(questions)} questions")
        return questions

    # ── Strategy 3: Loose format ──────────────────────────────────────────
    questions = _parse_loose(raw, num_questions)
    if questions:
        print(f"[quiz.py] Strategy 3 (loose) → {len(questions)} questions")
        return questions

    print("[quiz.py] All strategies failed — returning empty list")
    return []


# ── Parser helpers ────────────────────────────────────────────────────────

def _clean_answer(raw_ans: str) -> str:
    """Extracts a single A/B/C/D letter from messy answer strings."""
    if not raw_ans:
        return ""
    # Strip markdown bold/italic: **B** → B
    cleaned = re.sub(r'[\*_`]+', '', raw_ans).strip()
    # Take first letter that matches A-D
    m = re.search(r'\b([A-Da-d])\b', cleaned)
    if m:
        return m.group(1).upper()
    # Last resort: first character if it's a letter
    first = cleaned[:1].upper()
    return first if first in VALID_ANSWERS else ""


def _build_question(q_text, options, answer, explanation):
    """Validates and pads a question dict, returns None if invalid."""
    q_text = q_text.strip()
    answer = _clean_answer(answer)
    if not q_text or len(q_text) < 4 or answer not in VALID_ANSWERS:
        return None
    if len(options) < 2:
        return None
    # Pad missing options
    for letter in VALID_ANSWERS:
        if letter not in options:
            options[letter] = "—"
    return {
        "question": q_text,
        "options": options,
        "answer": answer,
        "explanation": explanation or f"Correct answer: {answer}"
    }


def _parse_numbered(raw: str, num_questions: int) -> list:
    """Handles standard numbered blocks split on '1. Q:' patterns."""
    questions = []
    # Split on numbered markers like "1." "2." "1)" optionally followed by "Q:"
    blocks = re.split(r'\n\s*\d+[.):\-]\s*(?:Q[:.]\s*)?', raw)

    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue
        try:
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            if not lines:
                continue

            # First line = question text
            q_text = re.sub(r'^Q\s*[:.\s]+', '', lines[0], flags=re.IGNORECASE).strip()
            # Strip bold markers from question
            q_text = re.sub(r'[\*_`]+', '', q_text).strip()
            if len(q_text) < 4:
                continue

            options = {}
            answer = ""
            explanation = ""

            for line in lines[1:]:
                line_clean = re.sub(r'[\*_`]+', '', line).strip()

                # Option lines: A: / A. / A) / a:
                m = re.match(r'^([A-Da-d])\s*[:.\)]\s*(.+)', line_clean)
                if m:
                    letter = m.group(1).upper()
                    if letter in VALID_ANSWERS:
                        options[letter] = m.group(2).strip()
                    continue

                # ANSWER / Correct Answer line
                ans_m = re.match(
                    r'^(?:answer|correct(?:\s+answer)?)\s*[:.\)]\s*(.+)',
                    line_clean, re.IGNORECASE
                )
                if ans_m:
                    answer = _clean_answer(ans_m.group(1))
                    continue

                # WHY / Explanation
                why_m = re.match(r'^(?:why|explanation|exp)\s*[:.\)]\s*(.+)',
                                 line_clean, re.IGNORECASE)
                if why_m:
                    explanation = why_m.group(1).strip()

            q = _build_question(q_text, options, answer, explanation)
            if q:
                questions.append(q)

        except Exception as e:
            print(f"[quiz.py] _parse_numbered block error: {e}")
            continue

        if len(questions) >= num_questions:
            break

    return questions


def _parse_table(raw: str, num_questions: int) -> list:
    """
    Handles markdown table output like:
    | 1 | Question text | A) opt | B) opt | C) opt | D) opt | **B** |
    Also handles header/separator rows gracefully.
    """
    questions = []
    lines = raw.splitlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue

        # Split on | and strip each cell
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]  # remove empty from leading/trailing |

        # Skip header and separator rows
        if not cells:
            continue
        if re.match(r'^[-:]+$', cells[0].replace(" ", "")):
            continue
        if re.match(r'^[#Nn]$|^num|^question|^q\s*$', cells[0], re.IGNORECASE):
            continue

        if len(cells) < 5:
            continue

        data_cells = cells[:]
        if re.match(r'^\d+$', data_cells[0]):
            data_cells = data_cells[1:]

        if len(data_cells) < 5:
            continue

        q_text = re.sub(r'[\*_`]+', '', data_cells[0]).strip()
        if len(q_text) < 5:
            continue

        option_cells = data_cells[1:5]
        options = {}
        for i, (letter, cell) in enumerate(zip(VALID_ANSWERS, option_cells)):
            cleaned = re.sub(r'^[A-Da-d]\s*[:.\)]\s*', '', cell).strip()
            cleaned = re.sub(r'[\*_`]+', '', cleaned).strip()
            if cleaned:
                options[letter] = cleaned

        answer_cell = data_cells[5] if len(data_cells) > 5 else ""
        if not answer_cell and len(data_cells) > 5:
            answer_cell = data_cells[-1]
        answer = _clean_answer(answer_cell)

        q = _build_question(q_text, options, answer, "")
        if q:
            questions.append(q)

        if len(questions) >= num_questions:
            break

    return questions


def _parse_loose(raw: str, num_questions: int) -> list:
    """
    Most permissive fallback — scans line by line for Q/A/ANSWER patterns
    regardless of numbering or structure.
    """
    questions = []
    lines = raw.splitlines()
    current_q = None
    options = {}
    answer = ""
    explanation = ""

    def flush():
        nonlocal current_q, options, answer, explanation
        if current_q:
            q = _build_question(current_q, options, answer, explanation)
            if q:
                questions.append(q)
        current_q = None
        options = {}
        answer = ""
        explanation = ""

    for line in lines:
        line_clean = re.sub(r'[\*_`]+', '', line.strip()).strip()
        if not line_clean:
            continue

        # New question line
        q_m = re.match(r'^(?:\d+[.):\-]?\s*)?Q\s*[:.\)]\s*(.+)', line_clean, re.IGNORECASE)
        if q_m:
            flush()
            current_q = q_m.group(1).strip()
            continue

        # Option line
        opt_m = re.match(r'^([A-Da-d])\s*[:.\)]\s*(.+)', line_clean)
        if opt_m and current_q is not None:
            letter = opt_m.group(1).upper()
            if letter in VALID_ANSWERS:
                options[letter] = opt_m.group(2).strip()
            continue

        # ANSWER line
        ans_m = re.match(r'^(?:answer|correct(?:\s+answer)?)\s*[:.\)]\s*(.+)',
                         line_clean, re.IGNORECASE)
        if ans_m and current_q is not None:
            answer = _clean_answer(ans_m.group(1))
            continue

        # WHY line
        why_m = re.match(r'^(?:why|explanation|exp)\s*[:.\)]\s*(.+)',
                         line_clean, re.IGNORECASE)
        if why_m and current_q is not None:
            explanation = why_m.group(1).strip()

        if len(questions) >= num_questions:
            break

    flush()  # don't forget the last block
    return questions[:num_questions]
