import json
import os
import re
from datetime import datetime, timezone

from modules.runtime_paths import data_dir


HISTORY_PATH = data_dir() / "study_history.json"


def _default_history() -> dict:
    return {
        "quiz_sessions": [],
        "topic_stats": {},
        "flashcard_stats": {},
    }


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def load_study_history() -> dict:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                default = _default_history()
                for key, value in default.items():
                    data.setdefault(key, value)
                return data
    except Exception as exc:
        print(f"⚠️ Could not load study history: {exc}")
    return _default_history()


def save_study_history(history: dict) -> None:
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=2)
    except Exception as exc:
        print(f"⚠️ Could not save study history: {exc}")


def record_quiz_session(*, sources: list[str], difficulty: str, score: int, total: int,
                        attempts: list[dict]) -> dict:
    history = load_study_history()
    wrong_questions = []
    missed_topics = []

    for attempt in attempts:
        topic = (attempt.get("topic") or "General").strip() or "General"
        stats = history["topic_stats"].setdefault(topic, {"attempts": 0, "correct": 0, "wrong": 0})
        stats["attempts"] += 1
        if attempt.get("correct"):
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            missed_topics.append(topic)
            wrong_questions.append({
                "question": attempt.get("question", ""),
                "selected": attempt.get("selected", ""),
                "correct_answer": attempt.get("correct_answer", ""),
                "topic": topic,
                "explanation": attempt.get("explanation", ""),
            })

    session = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "difficulty": difficulty,
        "score": score,
        "total": total,
        "wrong_questions": wrong_questions[:12],
        "wrong_topics": sorted(set(missed_topics)),
    }
    history["quiz_sessions"].append(session)
    history["quiz_sessions"] = history["quiz_sessions"][-30:]
    save_study_history(history)
    return session


def get_quiz_analytics(limit_topics: int = 5, limit_sessions: int = 5) -> dict:
    history = load_study_history()
    topics = []
    for topic, stats in history.get("topic_stats", {}).items():
        attempts = max(1, int(stats.get("attempts", 0)))
        wrong = int(stats.get("wrong", 0))
        correct = int(stats.get("correct", 0))
        topics.append({
            "topic": topic,
            "attempts": attempts,
            "wrong": wrong,
            "correct": correct,
            "wrong_rate": round((wrong / attempts) * 100),
        })
    topics.sort(key=lambda item: (item["wrong"], item["wrong_rate"], item["attempts"]), reverse=True)

    recent_sessions = list(reversed(history.get("quiz_sessions", [])[-limit_sessions:]))
    return {
        "topics": topics[:limit_topics],
        "recent_sessions": recent_sessions,
    }


def record_flashcard_result(question: str, source_label: str, remembered: bool) -> dict:
    history = load_study_history()
    key = _normalize_key(question)
    entry = history["flashcard_stats"].setdefault(key, {
        "question": question.strip(),
        "sources": [],
        "correct": 0,
        "wrong": 0,
    })
    if source_label and source_label not in entry["sources"]:
        entry["sources"].append(source_label)
        entry["sources"] = entry["sources"][-5:]
    if remembered:
        entry["correct"] += 1
    else:
        entry["wrong"] += 1
    save_study_history(history)
    return entry


def get_flashcard_stats(question: str) -> dict:
    history = load_study_history()
    entry = history.get("flashcard_stats", {}).get(_normalize_key(question), {})
    return {
        "correct": int(entry.get("correct", 0)),
        "wrong": int(entry.get("wrong", 0)),
    }


def get_hard_flashcards(cards: list[dict], minimum_wrong: int = 1) -> list[dict]:
    ranked = []
    for card in cards or []:
        stats = get_flashcard_stats(card.get("question", ""))
        hard_score = (stats["wrong"] * 2) - stats["correct"]
        if stats["wrong"] >= minimum_wrong or hard_score > 0:
            ranked.append((hard_score, stats["wrong"], card))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [card for _, _, card in ranked]
