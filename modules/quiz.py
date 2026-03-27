import json
import re
from modules.ai_engine import ask_lmstudio

# =============================================
# 📝 Smart Quiz Module
# Generates multiple choice questions (A/B/C/D)
# =============================================

def generate_quiz(text: str, num_questions: int = 5) -> list:
    """
    Generates multiple choice questions from document text.
    Returns list of dicts:
    [{"question": ..., "options": {"A":..,"B":..,"C":..,"D":..}, "answer": "A", "explanation": ...}]
    """
    words = text.split()
    context = " ".join(words[:3000])

    prompt = f"""Read the document below and create {num_questions} multiple choice questions.

Use EXACTLY this format for every question:

1. Q: [question text]
   A: [option A]
   B: [option B]
   C: [option C]
   D: [option D]
   ANSWER: [correct letter A/B/C/D]
   WHY: [one sentence explanation]

Rules:
- Questions must be based strictly on the document
- Only ONE correct answer per question
- Wrong options must be plausible but clearly incorrect
- Keep options short (one sentence max)
- Start immediately with "1. Q:"

Document:
{context}

Quiz:"""

    raw = ask_lmstudio(prompt=prompt, context="")
    return parse_quiz(raw, num_questions)


def parse_quiz(raw: str, num_questions: int) -> list:
    """Parses the model output into structured quiz questions."""
    questions = []
    # Split by question number
    blocks = re.split(r'\n\s*\d+\.\s*Q:', raw)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            # Extract question text
            lines = block.strip().splitlines()
            q_text = lines[0].strip().lstrip("Q:").strip()

            options = {}
            answer = ""
            explanation = ""

            for line in lines[1:]:
                line = line.strip()
                m = re.match(r'^([A-D])[:\.]?\s+(.+)', line)
                if m:
                    options[m.group(1)] = m.group(2).strip()
                elif line.upper().startswith("ANSWER:"):
                    answer = re.sub(r'(?i)answer\s*:', '', line).strip().upper()[:1]
                elif line.upper().startswith("WHY:"):
                    explanation = re.sub(r'(?i)why\s*:', '', line).strip()

            if q_text and len(options) == 4 and answer in "ABCD":
                questions.append({
                    "question": q_text,
                    "options": options,
                    "answer": answer,
                    "explanation": explanation
                })
        except Exception:
            continue

        if len(questions) >= num_questions:
            break

    return questions if questions else []
