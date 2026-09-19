import json
import os
import re
import threading
from datetime import datetime, timezone

from modules.runtime_paths import atomic_write_json, data_dir, log, read_json_with_recovery


HISTORY_PATH = data_dir() / "study_history.json"

# Every flashcard verdict is a full read-modify-write of this file. With two
# browser sessions open, interleaved reads lost each other's updates; the lock
# serialises the whole cycle within the process.
_history_lock = threading.RLock()

# quiz_sessions was already trimmed to 30, but topic_stats and flashcard_stats
# grew without bound and the whole file is rewritten on every single click.
MAX_TOPIC_STATS = 500
MAX_FLASHCARD_STATS = 800


def _default_history() -> dict:
    return {
        "quiz_sessions": [],
        "topic_stats": {},
        "flashcard_stats": {},
    }


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def load_study_history() -> dict:
    data, error = read_json_with_recovery(HISTORY_PATH, default=None)
    if error:
        log(f"⚠️ Study history: {error}")
    if isinstance(data, dict):
        default = _default_history()
        for key, value in default.items():
            data.setdefault(key, value)
        return data
    return _default_history()


def _trim_history(history: dict) -> dict:
    """Bound the two dicts that previously grew forever."""
    topics = history.get("topic_stats", {})
    if len(topics) > MAX_TOPIC_STATS:
        ranked = sorted(
            topics.items(),
            key=lambda kv: int((kv[1] or {}).get("attempts", 0)),
            reverse=True,
        )
        history["topic_stats"] = dict(ranked[:MAX_TOPIC_STATS])

    cards = history.get("flashcard_stats", {})
    if len(cards) > MAX_FLASHCARD_STATS:
        ranked = sorted(
            cards.items(),
            key=lambda kv: int((kv[1] or {}).get("correct", 0)) + int((kv[1] or {}).get("wrong", 0)),
            reverse=True,
        )
        history["flashcard_stats"] = dict(ranked[:MAX_FLASHCARD_STATS])
    return history


def save_study_history(history: dict) -> None:
    try:
        atomic_write_json(HISTORY_PATH, _trim_history(history))
    except Exception as exc:
        log(f"⚠️ Could not save study history: {exc}")


def record_quiz_session(*, sources: list[str], difficulty: str, score: int, total: int,
                        attempts: list[dict]) -> dict:
  with _history_lock:
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
  with _history_lock:
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
