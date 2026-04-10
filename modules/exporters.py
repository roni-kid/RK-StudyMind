import csv
import os
import re
from datetime import datetime


EXPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "exports",
)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "studymind").strip().lower()).strip("-")
    return cleaned or "studymind"


def export_flashcards_csv(cards: list[dict], source_label: str, difficulty: str) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(EXPORT_DIR, f"flashcards_{_slugify(source_label)}_{stamp}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Front", "Back", "Source", "Difficulty", "Tags"])
        tags = f"studymind,{difficulty.lower()}"
        for card in cards or []:
            writer.writerow([
                card.get("question", ""),
                card.get("answer", ""),
                source_label,
                difficulty,
                tags,
            ])
    return path


def export_quiz_report(*, attempts: list[dict], score: int, total: int, sources: list[str],
                       difficulty: str, weak_topics: list[dict]) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = sources[0] if len(sources) == 1 else f"{len(sources)}-docs"
    path = os.path.join(EXPORT_DIR, f"quiz_report_{_slugify(label)}_{stamp}.md")

    lines = [
        "# StudyMind Quiz Report",
        "",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Difficulty: {difficulty}",
        f"- Score: {score}/{total}",
        f"- Sources: {', '.join(sources) if sources else 'N/A'}",
        "",
        "## Weak Topics",
        "",
    ]

    if weak_topics:
        for topic in weak_topics:
            lines.append(
                f"- {topic['topic']}: {topic['wrong']} wrong out of {topic['attempts']} attempt(s)"
            )
    else:
        lines.append("- No weak-topic data available yet.")

    lines.extend(["", "## Question Review", ""])
    for index, attempt in enumerate(attempts or [], start=1):
        result = "Correct" if attempt.get("correct") else "Wrong"
        lines.append(f"### {index}. {attempt.get('question', 'Question')}")
        lines.append(f"- Result: {result}")
        lines.append(f"- Topic: {attempt.get('topic', 'General')}")
        lines.append(f"- Your answer: {attempt.get('selected', 'N/A')}")
        lines.append(f"- Correct answer: {attempt.get('correct_answer', 'N/A')}")
        explanation = attempt.get("explanation", "").strip()
        if explanation:
            lines.append(f"- Why: {explanation}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")
    return path
