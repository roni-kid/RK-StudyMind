import gradio as gr
import sys
import os
import random
import html as _html
import re as _re
from datetime import datetime
import uuid
import json

sys.path.append(os.path.dirname(__file__))
from modules.pdf_reader import read_file, get_page_count, get_page_label, chunk_text
from modules.ai_engine import check_lmstudio_connection, is_lmstudio_online
from modules.vector_store import (
    index_chunks, search_similar_chunks, preload_model_background,
    clear_index, get_embed_backend
)
from modules.engine_manager import ask, get_engine_status

# Kick off embedding model load in background immediately at startup
preload_model_background()

from modules.adaptive_chunking import adaptive_strategy, initialize_adaptive_strategy
_adaptive_model_info = initialize_adaptive_strategy()
from modules.flashcards import generate_flashcards_result
from modules.mindmap import generate_mindmap_tree_result, mindmap_to_html, save_mindmap_file
from modules.quiz import generate_quiz_result
from modules.doc_library import render_library_html, save_library_snapshot, load_library_snapshot
from modules.exporters import export_flashcards_csv, export_quiz_report
from modules.study_context import build_balanced_context
from modules.study_history import (
    record_flashcard_result,
    record_quiz_session,
    get_quiz_analytics,
    get_hard_flashcards,
)
from modules.math_renderer import render_math, render_math_html
try:
    from _splash_patch import SPLASH_JS as _SPLASH_JS, css as _SPLASH_CSS
except ImportError:
    _SPLASH_JS = ""   # _splash_patch.py is git-ignored; fresh clones fall back gracefully
    _SPLASH_CSS = ""
from modules.coding_agent import (
    explain_code, render_explain_html,
    qa_code, render_qa_history_html,
)
from modules.code_viewer import syntax_highlight_html, get_language_from_filename, render_code_empty_state
from modules.audio_overview import (
    AUDIO_DURATION_CHOICES, DEFAULT_DURATION,
    generate_audio_overview_result, get_duration_preset,
    render_transcript_html,
)

# ── Config + File Profiler ────────────────────────────────────────────────────
from modules.file_profiler import load_config, get_profiler

_config        = load_config()
_file_profiler = get_profiler()

MAX_FILES_PER_UPLOAD = _config["max_files_per_upload"]
MAX_DOCS_PER_SESSION = _config["max_docs_per_session"]
MAX_FILE_SIZE_BYTES  = _config["max_file_size_mb"] * 1024 * 1024
MAX_DOC_WORDS        = _config["max_doc_words"]
MAX_TOTAL_WORDS      = _config["max_total_words"]
MAX_DOC_CHUNKS       = _config["max_doc_chunks"]
MAX_DOC_UNITS        = 1500  # page/unit hard cap (not tunable via config)
# ─────────────────────────────────────────────────────────────────────────────

STUDY_TIPS = [
    "💡 Tip: Upload multiple PDFs at once by holding Ctrl while selecting files.",
    "💡 Tip: Use the Q&A tab to quiz yourself before generating a formal quiz.",
    "💡 Tip: Flashcards work best in short 10-minute sessions — take a break after each round.",
    "💡 Tip: Generate a Mindmap first to understand a topic, then dive into Q&A for details.",
    "💡 Tip: Mix documents in Flashcards and Quiz mode to test cross-topic knowledge.",
    "💡 Tip: If quiz quality is low, try a document with more detailed text content.",
]

DIFFICULTY_CHOICES = ["Easy", "Medium", "Hard", "Difficult"]
MAX_QUIZ_QUESTIONS = 30
MAX_FLASHCARDS = 30

APP_VERSION = "v1.3"

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.c', '.cpp', '.java', '.html', '.css'}


def generation_status_note(result: dict) -> str:
    note = str((result or {}).get("note") or "").strip()
    return f" · {note}" if note else ""


def new_session_state() -> dict:
    return {
        "session_id": uuid.uuid4().hex,
        "library": {},
        "active_doc_id": "",
        "chat_log": [],
        "current_flashcards": [],
        "flashcards_master": [],
        "flashcard_wrong_cards": [],
        "current_flashcard_sources": [],
        "current_flashcard_source_label": "",
        "current_flashcard_difficulty": "Medium",
        "current_quiz": [],
        "quiz_master": [],
        "quiz_attempts": [],
        "quiz_wrong_questions": [],
        "quiz_sources": [],
        "current_quiz_source_label": "",
        "current_quiz_difficulty": "Medium",
        "quiz_session_saved": False,
    }


def ensure_session_state(session_state: dict | None) -> dict:
    if not isinstance(session_state, dict) or "session_id" not in session_state:
        session_state = new_session_state()
        try:
            restored_library, restored_active_id = load_library_snapshot()
        except Exception as e:
            print(f"⚠️ Could not load library snapshot: {e}")
            restored_library, restored_active_id = {}, ""
        if restored_library:
            session_state["library"] = restored_library
            session_state["active_doc_id"] = restored_active_id
            # library.json only holds chunks/metadata — this session's ChromaDB
            # collection is ephemeral, so restored docs must be re-embedded now
            # or Q&A/Quiz/Flashcards will silently search an empty collection.
            for doc_id, info in restored_library.items():
                try:
                    index_chunks(
                        info.get("chunks", []),
                        doc_id=doc_id,
                        filename=info.get("filename", ""),
                        session_id=session_state["session_id"],
                    )
                except Exception as e:
                    print(f"⚠️ Could not re-index restored doc '{info.get('filename', doc_id)}': {e}")
        return session_state
    session_state.setdefault("library", {})
    session_state.setdefault("active_doc_id", "")
    session_state.setdefault("chat_log", [])
    session_state.setdefault("current_flashcards", [])
    session_state.setdefault("flashcards_master", [])
    session_state.setdefault("flashcard_wrong_cards", [])
    session_state.setdefault("current_flashcard_sources", [])
    session_state.setdefault("current_flashcard_source_label", "")
    session_state.setdefault("current_flashcard_difficulty", "Medium")
    session_state.setdefault("current_quiz", [])
    session_state.setdefault("quiz_master", [])
    session_state.setdefault("quiz_attempts", [])
    session_state.setdefault("quiz_wrong_questions", [])
    session_state.setdefault("quiz_sources", [])
    session_state.setdefault("current_quiz_source_label", "")
    session_state.setdefault("current_quiz_difficulty", "Medium")
    session_state.setdefault("quiz_session_saved", False)
    return session_state


def get_library(session_state: dict) -> dict:
    return session_state["library"]


def get_active_doc(session_state: dict) -> dict | None:
    library = get_library(session_state)
    return library.get(session_state.get("active_doc_id", ""))


def get_active_filename(session_state: dict) -> str:
    active = get_active_doc(session_state)
    return active.get("filename", "") if active else ""


def get_all_doc_ids(session_state: dict) -> list:
    return list(get_library(session_state).keys())


def get_doc_choices(session_state: dict) -> list:
    counts = {}
    for info in get_library(session_state).values():
        filename = info.get("filename", "")
        counts[filename] = counts.get(filename, 0) + 1
    choices = []
    for doc_id, info in get_library(session_state).items():
        filename = info.get("filename", doc_id)
        label = filename if counts.get(filename, 0) <= 1 else f"{filename} [{doc_id[:8]}]"
        choices.append((label, doc_id))
    return choices

# ── Helpers ──────────────────────────────────────────────────────
def get_doc_status(session_state):
    fn = get_active_filename(session_state)
    if not fn:
        return "❌ No document loaded — upload a file in the Library tab first"
    info = get_active_doc(session_state) or {}
    return (
        f"✅ Active: {fn} ({info.get('pages','?')} {info.get('unit_label', 'pages')}) "
        f"— {len(get_library(session_state))} doc(s) in library"
    )


def get_checkbox_update(session_state):
    choices = get_doc_choices(session_state)
    return gr.update(choices=choices, value=[doc_id for _, doc_id in choices])


def get_radio_update(session_state):
    choices = get_doc_choices(session_state)
    doc_ids = [doc_id for _, doc_id in choices]
    active = session_state.get("active_doc_id", "")
    sel = active if active in doc_ids else (doc_ids[0] if doc_ids else None)
    return gr.update(choices=choices, value=sel)


def sanitize_docs(selected_docs, session_state) -> list:
    if not selected_docs:
        return []
    if isinstance(selected_docs, str):
        selected_docs = [selected_docs]
    library = get_library(session_state)
    return [d for d in selected_docs if d in library]


def get_source_names(selected_docs: list, session_state) -> list[str]:
    library = get_library(session_state)
    names = []
    for doc_id in selected_docs or []:
        if doc_id in library:
            names.append(library[doc_id]["filename"])
    return names


def get_source_label(selected_docs: list, session_state) -> str:
    names = get_source_names(selected_docs, session_state)
    if not names:
        return ""
    return names[0] if len(names) == 1 else f"{len(names)} doc(s)"


def get_chunks_from_selection(selected_docs: list, session_state) -> list[str]:
    library = get_library(session_state)
    chunks = []
    for doc_id in selected_docs or []:
        info = library.get(doc_id)
        if not info:
            continue
        filename = info.get("filename", "Document")
        for idx, chunk in enumerate(info.get("chunks", []), start=1):
            chunks.append(f"[From: {filename} | chunk {idx}]\n{chunk}")
    return chunks


def persist_library(session_state) -> None:
    save_library_snapshot(
        get_library(session_state),
        session_state.get("active_doc_id", ""),
    )


def render_quiz_analytics_html(session_state=None, title: str = "Weak Topic Analytics") -> str:
    analytics = get_quiz_analytics()
    topics = analytics.get("topics", [])
    sessions = analytics.get("recent_sessions", [])
    cards = []
    if topics:
        for topic in topics:
            cards.append(
                f"<div style='background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px 14px;'>"
                f"<div style='font-size:13px;font-weight:700;color:#f1f5f9;'>{_html.escape(topic['topic'])}</div>"
                f"<div style='font-size:12px;color:#94a3b8;margin-top:4px;'>{topic['wrong']} wrong · {topic['attempts']} attempts · {topic['wrong_rate']}% miss rate</div>"
                f"</div>"
            )
    else:
        cards.append(
            "<div style='background:#0f172a;border:1px dashed #334155;border-radius:12px;padding:14px;color:#64748b;font-size:13px;'>"
            "No quiz analytics yet. Complete a quiz to start tracking weak topics."
            "</div>"
        )

    recent_html = ""
    if sessions:
        rows = []
        for session in sessions:
            rows.append(
                f"<div style='font-size:12px;color:#94a3b8;'>"
                f"{_html.escape(session.get('difficulty', 'Medium'))} · "
                f"{session.get('score', 0)}/{session.get('total', 0)} · "
                f"{_html.escape(', '.join(session.get('sources', [])[:2]) or 'Source')}"
                f"</div>"
            )
        recent_html = (
            "<div style='margin-top:12px;'>"
            "<div style='font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.3px;text-transform:uppercase;margin-bottom:8px;'>Recent Quiz Sessions</div>"
            + "".join(rows) +
            "</div>"
        )

    return (
        "<div style='background:#1e293b;border:1px solid #334155;border-radius:16px;padding:16px 18px;font-family:\"Segoe UI\",sans-serif;'>"
        f"<div style='font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:12px;'>{_html.escape(title)}</div>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;'>{''.join(cards)}</div>"
        f"{recent_html}"
        "</div>"
    )


def dedupe_cards(cards: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for card in cards or []:
        key = card.get("question", "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(card)
    return unique


def render_missed_topics_html(session_state) -> str:
    wrong_questions = session_state.get("quiz_wrong_questions", [])
    if not wrong_questions:
        return render_quiz_analytics_html(title="Missed Topics")

    counts = {}
    for item in wrong_questions:
        topic = (item.get("topic") or "General").strip() or "General"
        counts[topic] = counts.get(topic, 0) + 1

    cards = []
    for topic, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        cards.append(
            f"<div style='background:#0f172a;border:1px solid #334155;border-radius:12px;padding:12px 14px;'>"
            f"<div style='font-size:13px;font-weight:700;color:#f1f5f9;'>{_html.escape(topic)}</div>"
            f"<div style='font-size:12px;color:#94a3b8;margin-top:4px;'>{count} missed question(s) in the current session</div>"
            f"</div>"
        )

    return (
        "<div style='background:#1e293b;border:1px solid #334155;border-radius:16px;padding:16px 18px;font-family:\"Segoe UI\",sans-serif;'>"
        "<div style='font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:12px;'>Missed Topics</div>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;'>{''.join(cards)}</div>"
        "</div>"
    )


# ── Engine section render helpers ────────────────────────────────

def render_engine_status_html() -> str:
    status   = get_engine_status()
    s_color  = "#10b981" if status["online"] else "#ef4444"
    backend  = get_embed_backend()
    eb_color = "#10b981" if backend == "LM Studio" else ("#f59e0b" if "local" in backend else "#64748b")
    eb_icon  = "⚡" if backend == "LM Studio" else "🧩"

    # Adaptive model info
    try:
        model_info = adaptive_strategy.detect_model()
        m_status   = model_info["status"]
        ctx_tokens = model_info["context_tokens"]
        ctx_words  = model_info["context_max_words"]
        m_color    = "#10b981" if "✅" in m_status else "#f59e0b"
        ctx_line   = (f'<div style="font-size:11px;color:#64748b;margin-top:3px;">'
                      f'Context window: {ctx_tokens:,} tokens · {ctx_words:,} words safe</div>')
    except Exception:
        m_status, m_color, ctx_line = "⚠️ Model unknown", "#f59e0b", ""

    return (
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:12px;'
        f'padding:14px 18px;font-family:\'Segoe UI\',sans-serif;">'
        f'<div style="font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:6px;">'
        f'🔧 LM Studio '
        f'<span style="font-size:11px;font-weight:400;color:#64748b;">— localhost:1234</span></div>'
        f'<div style="font-size:12px;color:{s_color};margin-bottom:4px;">{_html.escape(str(status["status_msg"]))}</div>'
        f'<div style="font-size:11px;color:{m_color};margin-bottom:2px;">{_html.escape(m_status)}</div>'
        f'{ctx_line}'
        f'<div style="font-size:11px;color:#475569;margin-top:6px;">Connect your own model via LM Studio</div>'
        f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #334155;'
        f'font-size:11px;color:{eb_color};">{eb_icon} Embeddings: {_html.escape(backend)}</div>'
        f'</div>'
    )


# ── Home ─────────────────────────────────────────────────────────
def render_home_stats(session_state, ai_status: str = "") -> str:
    library = get_library(session_state)
    doc_count   = len(library)
    word_count  = sum(info.get("words", 0) for info in library.values())
    chunk_count = sum(len(info.get("chunks", [])) for info in library.values())
    tip = random.choice(STUDY_TIPS)

    if not ai_status:
        ai_color, ai_label = "#475569", "Not checked"
    elif "✅" in ai_status:
        ai_color, ai_label = "#10b981", "Connected"
    else:
        ai_color, ai_label = "#ef4444", "Offline"

    def stat_card(icon, value, label, color):
        return (f'<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;'
                f'padding:20px 24px;flex:1;min-width:140px;text-align:center;">'
                f'<div style="font-size:24px;margin-bottom:6px;">{icon}</div>'
                f'<div style="font-size:26px;font-weight:800;color:{color};">{value}</div>'
                f'<div style="font-size:12px;color:#64748b;margin-top:4px;">{label}</div>'
                f'</div>')

    def feature_card(icon, title, desc):
        return ('<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;'
                'padding:18px 12px;flex:1;min-width:130px;text-align:center;">'
                f'<div style="font-size:28px;margin-bottom:8px;">{icon}</div>'
                f'<div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:4px;">{title}</div>'
                f'<div style="font-size:11px;color:#64748b;line-height:1.4;">{desc}</div>'
                '</div>')

    return f"""
<style>
@keyframes gradientShimmer{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes glossMove{{0%{{left:-60%;opacity:0}}15%{{opacity:1}}85%{{opacity:1}}100%{{left:130%;opacity:0}}}}
@keyframes pulseBadge{{0%,100%{{box-shadow:0 0 0 0 rgba(79,70,229,.5)}}50%{{box-shadow:0 0 0 8px rgba(79,70,229,0)}}}}
</style>
<div style="font-family:'Segoe UI',sans-serif;max-width:960px;margin:0 auto;padding:8px 0;">
  <div style="position:relative;overflow:hidden;border-radius:22px;margin-bottom:24px;
    background:linear-gradient(135deg,#1e1b4b,#312e81,#1e1b4b,#0f172a,#1e293b,#4F46E5,#1e1b4b);
    background-size:400% 400%;animation:gradientShimmer 7s ease infinite;
    padding:48px 40px;text-align:center;border:1px solid #3730a3;">
    <div style="position:absolute;top:0;left:-60%;width:40%;height:100%;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);
      transform:skewX(-15deg);animation:glossMove 4s ease-in-out infinite;pointer-events:none;"></div>
    <div style="font-size:54px;margin-bottom:12px;position:relative;">🧠</div>
    <div style="font-size:38px;font-weight:800;color:#f1f5f9;letter-spacing:-.5px;position:relative;">RK StudyMind</div>
    <div style="font-size:15px;color:#a5b4fc;margin-top:8px;position:relative;">Your personal AI-powered study companion</div>
    <div style="display:inline-block;background:#4F46E5;color:#fff;border-radius:20px;
      padding:4px 18px;font-size:12px;font-weight:700;margin-top:16px;
      letter-spacing:1px;position:relative;animation:pulseBadge 2s ease infinite;">{APP_VERSION}</div>
  </div>
  <div style="font-size:11px;font-weight:700;color:#475569;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Library Stats</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px;">
    {stat_card("📚", doc_count, "Documents", "#818cf8")}
    {stat_card("📝", f"{word_count:,}", "Words Indexed", "#34d399")}
    {stat_card("🔍", chunk_count, "Vector Chunks", "#f59e0b")}
    {stat_card("🔧", "LM Studio", "AI Engine", ai_color)}
  </div>
  <div style="font-size:11px;font-weight:700;color:#475569;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Features</div>
  <div style="display:flex;gap:10px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:6px;margin-bottom:20px;">
    {feature_card("📚","Library","Upload & manage docs")}
    {feature_card("💬","Q&A","Chat with documents")}
    {feature_card("📝","Quiz","Multiple choice quiz")}
    {feature_card("🃏","Flashcards","Score-tracked cards")}
    {feature_card("🗺️","Mindmap","Structured study tree")}
  </div>
  <div style="background:#1e293b;border:1px solid #334155;border-left:4px solid #4F46E5;border-radius:12px;padding:14px 18px;">
    <div id="rk-tip-text" style="font-size:13px;color:#94a3b8;line-height:1.6;transition:opacity 0.35s ease;">{tip}</div>
  </div>
  <script>(function(){{
    var tips={json.dumps(STUDY_TIPS)};
    var el=document.getElementById('rk-tip-text');
    if(!el)return;
    if(window._rkTipTimer)clearInterval(window._rkTipTimer);
    var idx={STUDY_TIPS.index(tip)};
    window._rkTipTimer=setInterval(function(){{
      idx=(idx+1)%tips.length;
      el.style.opacity='0';
      setTimeout(function(){{
        if(document.getElementById('rk-tip-text')===el){{el.textContent=tips[idx];el.style.opacity='1';}}
      }},350);
    }},5000);
  }})();</script>
</div>"""


def refresh_home(session_state):
    session_state = ensure_session_state(session_state)
    # Invalidate cached model detection so a model swap in LM Studio is picked up immediately
    adaptive_strategy.invalidate_cache()
    ai_status = check_lmstudio_connection()
    return (
        render_home_stats(session_state, ai_status),
        render_engine_status_html(),
        session_state,
    )


# ── Library ───────────────────────────────────────────────────────
def render_upload_info_html(msg, ok=True):
    if not msg: return ""
    color = "#10b981" if ok else "#ef4444"
    return (f'<div style="background:#1e293b;border:1px solid {color}33;border-left:4px solid {color};'
            f'border-radius:12px;padding:13px 18px;font-family:\'Segoe UI\',sans-serif;'
            f'font-size:13px;color:#f1f5f9;white-space:pre-line;line-height:1.7;">{_html.escape(str(msg))}</div>')


def make_upload_outputs(session_state, message: str, ok: bool = True):
    return (
        render_upload_info_html(message, ok=ok),
        *get_library_outputs(session_state),
        render_home_stats(session_state),
        session_state,
    )

def get_code_file_dropdown_update(session_state):
    """Return a gr.update for the Coding file dropdown, listing only code files."""
    choices = [
        (info.get("filename", doc_id), doc_id)
        for doc_id, info in get_library(session_state).items()
        if os.path.splitext(info.get("filename", ""))[1].lower() in CODE_EXTENSIONS
    ]
    return gr.update(choices=choices, value=(choices[0][1] if choices else None))


def get_audio_doc_dropdown_update(session_state):
    """Return a gr.update for the Audio document dropdown."""
    choices = get_doc_choices(session_state)
    active = session_state.get("active_doc_id")
    value = active if active in get_library(session_state) else (choices[0][1] if choices else None)
    return gr.update(choices=choices, value=value)


def get_library_outputs(session_state):
    return (
        render_library_html(get_library(session_state), session_state.get("active_doc_id", "")),
        get_doc_status(session_state),
        get_radio_update(session_state),
        get_checkbox_update(session_state),
        get_checkbox_update(session_state),
        get_checkbox_update(session_state),
        get_audio_doc_dropdown_update(session_state),
        render_qa_status_html(session_state),
        get_code_file_dropdown_update(session_state),
    )


def render_qa_status_html(session_state):
    fn = get_active_filename(session_state)
    if not fn:
        return ('<div style="background:#1e293b;border-left:4px solid #ef4444;border-radius:0 10px 10px 0;'
                'padding:10px 16px;font-family:\'Segoe UI\',sans-serif;font-size:13px;color:#94a3b8;">'
                '❌ No active document — upload in Library</div>')
    return (f'<div style="background:#1e293b;border-left:4px solid #10b981;border-radius:0 10px 10px 0;'
            f'padding:10px 16px;font-family:\'Segoe UI\',sans-serif;font-size:13px;color:#34d399;">'
            f'✅ {_html.escape(fn)} &nbsp;·&nbsp; {len(get_library(session_state))} doc(s) loaded</div>')


def load_files(session_state, files):
    session_state = ensure_session_state(session_state)
    library = get_library(session_state)
    if files is None:
        yield make_upload_outputs(session_state, "⚠️ No files uploaded.", ok=False)
        return
    if not isinstance(files, list):
        files = [files]

    if len(files) > MAX_FILES_PER_UPLOAD:
        files = files[:MAX_FILES_PER_UPLOAD]
        results = [f"⚠️ Only the first {MAX_FILES_PER_UPLOAD} files were processed."]
    else:
        results = []
    total_files = len(files)
    current_total_words = sum(info.get("words", 0) for info in library.values())

    for index, file in enumerate(files, start=1):
        # Fast pre-check: session document cap
        if len(library) >= MAX_DOCS_PER_SESSION:
            results.append(f"⚠️ Session limit reached ({MAX_DOCS_PER_SESSION} documents).")
            break

        fp  = file.name
        fn  = os.path.basename(fp)
        ext = os.path.splitext(fn)[1].lower()

        yield make_upload_outputs(
            session_state,
            f"⏳ Processing {index}/{total_files}: {fn}\n\n" + "\n".join(results or ["Preparing file…"]),
        )

        if ext not in ['.pdf', '.docx', '.txt', '.md', '.pptx', '.epub',
                       '.py', '.js', '.ts', '.c', '.cpp', '.java', '.html', '.css']:
            results.append(f"❌ Skipped '{fn}': unsupported type")
            continue

        try:
            file_size = os.path.getsize(fp)
        except OSError:
            file_size = 0

        if file_size > MAX_FILE_SIZE_BYTES:
            results.append(f"❌ Skipped '{fn}': file too large ({file_size // (1024 * 1024)} MB)")
            continue

        pc = get_page_count(fp)
        if pc and pc > MAX_DOC_UNITS:
            results.append(f"❌ Skipped '{fn}': document too large ({pc} {get_page_label(fp)})")
            continue

        yield make_upload_outputs(
            session_state,
            f"⏳ Processing {index}/{total_files}: {fn}\n\n📖 Reading document text…\n" + "\n".join(results),
        )

        raw = read_file(fp)
        if isinstance(raw, str) and raw.startswith(("❌", "⚠️")):
            results.append(f"❌ Skipped '{fn}': {raw}")
            continue

        # ── File Profiler: plan the document (normal / stretch / split) ──
        plans   = _file_profiler.plan_document(raw, fn, _config)
        n_plans = len(plans)

        if n_plans > 1:
            yield make_upload_outputs(
                session_state,
                f"⏳ Processing {index}/{total_files}: {fn}\n\n"
                f"📐 Large document — splitting into {n_plans} parts…\n"
                + "\n".join(results),
            )

        # ── Process each plan entry ──────────────────────────────────────
        for plan in plans:
            plan_label = plan["label"]
            plan_text  = plan["text"]
            word_count = plan["word_count"]
            split_idx  = plan["split_index"]   # int | None
            split_tot  = plan["split_total"]   # int | None

            # Session document cap (re-check per part for split files)
            if len(library) >= MAX_DOCS_PER_SESSION:
                tag = f"part {split_idx}/{split_tot} of " if split_idx else ""
                results.append(f"⚠️ Session limit reached — skipping {tag}'{fn}'.")
                break

            # Session word cap
            remaining_words = MAX_TOTAL_WORDS - current_total_words
            if word_count > remaining_words:
                tag = f"part {split_idx}/{split_tot} of " if split_idx else ""
                results.append(f"⚠️ Session word limit reached — skipping {tag}'{fn}'.")
                break

            # ── Adaptive chunk size ───────────────────────────────────────
            chunk_strategy = adaptive_strategy.compute_chunk_size(word_count)
            cks = chunk_text(plan_text, chunk_size_tokens=chunk_strategy["chunk_size_tokens"])
            if not cks:
                results.append(f"❌ Skipped '{plan_label}': no extractable text")
                continue
            if len(cks) > MAX_DOC_CHUNKS:
                results.append(f"❌ Skipped '{plan_label}': too many chunks ({len(cks)})")
                continue

            # ── Build library entry ───────────────────────────────────────
            doc_id     = uuid.uuid4().hex
            plan_pages = pc if n_plans == 1 else word_count
            plan_unit  = get_page_label(fp) if n_plans == 1 else "words"
            entry = {
                "id":         doc_id,
                "filename":   plan_label,
                "text":       "",   # raw not stored; chunks are sufficient
                "chunks":     cks,
                "pages":      plan_pages,
                "unit_label": plan_unit,
                "words":      word_count,
                "code_text":  plan_text if ext in CODE_EXTENSIONS else "",  # full text for Coding
            }

            part_tag = f"part {split_idx}/{split_tot} — " if split_idx else ""
            yield make_upload_outputs(
                session_state,
                f"⏳ Processing {index}/{total_files}: {fn}\n\n"
                f"🧠 Indexing {part_tag}{len(cks)} chunks ({chunk_strategy['strategy']})…\n"
                + "\n".join(results),
            )

            try:
                index_chunks(
                    cks,
                    doc_id=doc_id,
                    filename=plan_label,
                    session_id=session_state["session_id"],
                )
            except Exception as e:
                results.append(f"❌ Skipped '{plan_label}': indexing failed ({e})")
                continue

            library[doc_id] = entry
            current_total_words += word_count
            if not session_state.get("active_doc_id"):
                session_state["active_doc_id"] = doc_id
            persist_library(session_state)

            icon      = {'.pdf': '📄', '.docx': '📝', '.txt': '📃', '.md': '📋', '.pptx': '📊', '.epub': '📖',
                         '.py': '🐍', '.js': '🟨', '.ts': '🔷', '.c': '⚙️', '.cpp': '⚙️',
                         '.java': '☕', '.html': '🌐', '.css': '🎨'}.get(ext, '📄')
            part_note = f" [split {split_idx}/{split_tot}]" if split_idx else ""
            results.append(
                f"{icon} '{plan_label}'{part_note} — {word_count:,} words, "
                f"{len(cks)} chunks [{chunk_strategy['strategy']}]"
            )
            yield make_upload_outputs(
                session_state,
                f"✅ {'Part' if split_idx else 'File'} done: {plan_label}\n\n"
                + "\n".join(results)
                + f"\n📚 Total: {len(library)}",
            )

    info = f"✅ {len(results)} result(s):\n" + "\n".join(results) + f"\n📚 Total: {len(library)}"
    yield make_upload_outputs(session_state, info)


def switch_active_doc(session_state, doc_id):
    session_state = ensure_session_state(session_state)
    if doc_id in get_library(session_state):
        session_state["active_doc_id"] = doc_id
        persist_library(session_state)
    return (*get_library_outputs(session_state), session_state)


def delete_doc(session_state, doc_id):
    session_state = ensure_session_state(session_state)
    library = get_library(session_state)
    if doc_id in library:
        clear_index(session_state["session_id"], doc_id)
        del library[doc_id]
        if session_state.get("active_doc_id") == doc_id:
            remaining = get_all_doc_ids(session_state)
            session_state["active_doc_id"] = remaining[0] if remaining else ""
        persist_library(session_state)
    return (*get_library_outputs(session_state), session_state)


def refresh_library(session_state):
    session_state = ensure_session_state(session_state)
    return (*get_library_outputs(session_state), session_state)

# ── Q&A ───────────────────────────────────────────────────────────
def format_ai_message(text: str) -> str:
    if not text:
        return ""
    text = render_math_html(text)
    def escape_non_tags(s):
        result = []
        for part in _re.split(r'(<[^>]+>)', s):
            if part.startswith('<'):
                result.append(part)
            else:
                result.append(_html.escape(part))
        return ''.join(result)
    text = escape_non_tags(text)
    FENCE = _re.compile(r'```(?:\w+)?\n?(.*?)```', _re.DOTALL)
    def rfence(m):
        code = m.group(1).strip()
        return (f'<pre style="background:#0d1117;border:1px solid #30363d;border-radius:10px;'
                f'padding:14px 18px;margin:10px 0;overflow-x:auto;font-family:monospace;'
                f'font-size:12.5px;color:#c9d1d9;line-height:1.6;"><code>{code}</code></pre>')
    text = FENCE.sub(rfence, text)
    def convert_header(m):
        level = len(m.group(1))
        content = m.group(2).strip()
        size    = {1: "18px", 2: "16px", 3: "14px"}.get(level, "14px")
        margin  = {1: "14px 0 8px 0", 2: "12px 0 6px 0", 3: "10px 0 4px 0"}.get(level, "8px 0 4px 0")
        border  = "border-bottom:1px solid #334155;padding-bottom:6px;" if level == 1 else ""
        return (f'<div style="font-size:{size};font-weight:700;color:#f1f5f9;'
                f'margin:{margin};{border}">{content}</div>')
    text = _re.sub(r'(?m)^(#{1,3})\s+(.+)', convert_header, text)
    text = _re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#f1f5f9;">\1</strong>', text)
    text = _re.sub(r'(?<![*_])\*([^*\n]+?)\*(?![*_])', r'<em>\1</em>', text)
    text = _re.sub(r'`([^`]+)`',
        r'<code style="background:#0d1117;border:1px solid #30363d;padding:2px 7px;'
        r'border-radius:5px;font-size:12.5px;color:#a5b4fc;font-family:monospace;">\1</code>', text)
    text = _re.sub(r'(?m)^(\d+\.\s)', r'<span style="color:#818cf8;font-weight:700;">\1</span>', text)
    text = _re.sub(r'(?m)^([•\-]\s)', r'<span style="color:#818cf8;">\1</span>', text)
    text = text.replace('\n', '<br>')
    return text


def render_chat_bubbles(session_state):
    chat_log = session_state.get("chat_log", [])
    if not chat_log:
        return ('<div style="display:flex;align-items:center;justify-content:center;min-height:300px;'
                'font-family:\'Segoe UI\',sans-serif;color:#475569;font-size:15px;gap:10px;flex-direction:column;">'
                '<div style="font-size:32px;">💬</div><div>Ask a question about your documents</div></div>')
    bubbles = ""
    for entry in chat_log:
        speaker, msg = entry[0], entry[1]
        ts = entry[2] if len(entry) > 2 else ""
        ts_html = (f'<div style="font-size:10.5px;color:#64748b;margin-top:5px;">{_html.escape(ts)}</div>') if ts else ""
        if speaker == "You":
            safe = _html.escape(msg).replace("\n","<br>")
            bubbles += (f'<div style="display:flex;flex-direction:column;align-items:flex-end;margin-bottom:18px;">'
                        f'<div style="max-width:70%;background:linear-gradient(135deg,#4338ca,#6366f1);color:#fff;'
                        f'border-radius:18px 18px 4px 18px;padding:13px 18px;font-size:14px;font-weight:500;'
                        f'line-height:1.65;box-shadow:0 4px 16px rgba(79,70,229,.35);">{safe}</div>{ts_html}</div>')
        else:
            if "_[Source:" in msg or "_[Searched" in msg:
                pts  = msg.rsplit("\n\n_", 1)
                body = format_ai_message(pts[0])
                src  = pts[1].strip("_") if len(pts) > 1 else ""
                sbadge = (f'<div style="display:inline-flex;align-items:center;gap:5px;margin-top:10px;'
                          f'background:#0f172a;border:1px solid #334155;border-radius:20px;padding:3px 10px;'
                          f'font-size:11px;color:#94a3b8;">📎 {_html.escape(src)}</div>') if src else ""
            else:
                body   = format_ai_message(msg)
                sbadge = ""
            bubbles += (f'<div style="display:flex;gap:10px;margin-bottom:18px;align-items:flex-start;">'
                        f'<div style="width:36px;height:36px;border-radius:12px;flex-shrink:0;'
                        f'background:linear-gradient(135deg,#312e81,#4F46E5);border:1px solid #4338ca;'
                        f'display:flex;align-items:center;justify-content:center;font-size:18px;'
                        f'box-shadow:0 2px 8px rgba(79,70,229,.3);">🧠</div>'
                        f'<div style="display:flex;flex-direction:column;max-width:75%;min-width:0;">'
                        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:4px 18px 18px 18px;'
                        f'padding:14px 18px;font-size:14px;color:#e2e8f0;line-height:1.75;'
                        f'overflow-wrap:break-word;word-break:break-word;'
                        f'box-shadow:0 2px 10px rgba(0,0,0,.25);">{body}{sbadge}</div>{ts_html}</div></div>')
    return (f'<div id="rk_chat_inner" style="font-family:\'Segoe UI\',sans-serif;padding:12px 6px;display:flex;flex-direction:column;max-height:480px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:#334155 #0f172a;">'
            f'{bubbles}</div>')

THINKING_BUBBLE = """<div style="display:flex;gap:10px;margin-bottom:18px;align-items:flex-start;">
  <div style="width:36px;height:36px;border-radius:12px;flex-shrink:0;background:linear-gradient(135deg,#312e81,#4F46E5);
    border:1px solid #4338ca;display:flex;align-items:center;justify-content:center;font-size:18px;">🧠</div>
  <div style="background:#1e293b;border:1px solid #4338ca40;border-radius:4px 18px 18px 18px;
    padding:16px 22px;display:flex;align-items:center;gap:4px;">
    <span class="rk-dot"></span><span class="rk-dot"></span><span class="rk-dot"></span>
  </div>
</div>"""

SCROLL_JS = """<script>(function(){var d=document.getElementById('rk_chat_inner');if(!d)return;
d.scrollTop=d.scrollHeight;})();</script>"""

def answer_question(session_state, question, chat_html, search_mode):
    session_state = ensure_session_state(session_state)
    chat_log = session_state["chat_log"]
    library = get_library(session_state)
    if not question.strip():
        yield chat_html, "", session_state
        return
    ts = datetime.now().strftime("%I:%M %p").lstrip("0")
    chat_log.append(("You", question, ts))
    active_doc = get_active_doc(session_state)
    if not active_doc:
        chat_log.append(("RK StudyMind", "⚠️ No document loaded. Please upload a file in the Library tab first.", datetime.now().strftime("%I:%M %p").lstrip("0")))
        yield render_chat_bubbles(session_state) + SCROLL_JS, "", session_state
        return
    if not is_lmstudio_online():
        chat_log.append(("RK StudyMind", "🔴 LM Studio is offline. Open LM Studio, load a model, and start the local server before asking questions.", datetime.now().strftime("%I:%M %p").lstrip("0")))
        yield render_chat_bubbles(session_state) + SCROLL_JS, "", session_state
        return
    yield render_chat_bubbles(session_state) + THINKING_BUBBLE + SCROLL_JS, "", session_state
    if search_mode == "🔍 Active Document Only":
        evidence = search_similar_chunks(
            question=question,
            doc_id=active_doc["id"],
            session_id=session_state["session_id"],
            top_k=3,
            include_metadata=True,
        )
        if evidence:
            context = "\n\n---\n\n".join(item["text"] for item in evidence)
            chunk_labels = ", ".join(str(item["chunk_index"] + 1) for item in evidence)
            source_note = f"Source: {active_doc['filename']} (chunks {chunk_labels})"
        else:
            _ctx_words = adaptive_strategy.detect_model()["context_max_words"]
            context = build_balanced_context(active_doc.get("chunks", []), max_words=_ctx_words, target_chunks=10)
            source_note = f"Source: {active_doc['filename']} (balanced fallback)"
    else:
        all_chunks = []
        source_parts = []
        for doc_id, info in library.items():
            evidence = search_similar_chunks(
                question=question,
                doc_id=doc_id,
                session_id=session_state["session_id"],
                top_k=2,
                include_metadata=True,
            )
            if evidence:
                chunk_labels = ", ".join(str(item["chunk_index"] + 1) for item in evidence)
                source_parts.append(f"{info['filename']} (chunks {chunk_labels})")
                for item in evidence:
                    all_chunks.append(f"[From: {info['filename']} | chunk {item['chunk_index'] + 1}]\n{item['text']}")
        if all_chunks:
            context = "\n\n---\n\n".join(all_chunks)
            source_note = "Sources: " + "; ".join(source_parts[:4])
        else:
            _ctx_words = adaptive_strategy.detect_model()["context_max_words"]
            context = build_balanced_context(
                [chunk for info in library.values() for chunk in info.get("chunks", [])],
                max_words=_ctx_words,
                target_chunks=12,
            )
            source_note = f"Searched {len(library)} documents (balanced fallback)"
    answer = ask(prompt=question, context=context)
    chat_log.append(("RK StudyMind", f"{answer}\n\n_[{source_note}]_", datetime.now().strftime("%I:%M %p").lstrip("0")))
    yield render_chat_bubbles(session_state) + SCROLL_JS, "", session_state


def clear_chat(session_state):
    session_state = ensure_session_state(session_state)
    session_state["chat_log"] = []
    return render_chat_bubbles(session_state), "", session_state

# ── Quiz ──────────────────────────────────────────────────────────
def render_quiz_question(q, index, total, selected=None, revealed=False, score=0):
    pct = int(((index+1)/total)*100)
    opts = ""
    q_text_rendered = _html.escape(render_math(q["question"]))
    for letter, text in q["options"].items():
        opt_rendered = _html.escape(render_math(text))
        if revealed:
            if letter == q["answer"]:   lbg,lclr,rbg,rborder,tclr,fw,icon = "#10b981","#fff","#0d2318","2px solid #10b981","#6ee7b7","700","✅"
            elif letter == selected:    lbg,lclr,rbg,rborder,tclr,fw,icon = "#ef4444","#fff","#2d1212","2px solid #ef4444","#fca5a5","600","❌"
            else:                       lbg,lclr,rbg,rborder,tclr,fw,icon = "#1e293b","#334155","#0f172a","1px solid #1e293b","#334155","400",letter
            click = ""
        else:
            if letter == selected:      lbg,lclr,rbg,rborder,tclr,fw = "#4F46E5","#fff","#1a1f4a","2px solid #4F46E5","#c7d2fe","700"
            else:                       lbg,lclr,rbg,rborder,tclr,fw = "#1e293b","#64748b","#0f172a","1px solid #334155","#e2e8f0","400"
            icon = letter
            hin  = f"if(this.dataset.picked!='1'){{this.style.background='#1a2540';this.style.borderColor='#475569';}}"
            hout = f"if(this.dataset.picked!='1'){{this.style.background='{rbg}';this.style.borderColor='#334155';}}"
            click = (f'onclick="var e=document.getElementById(\'rk_quiz_btn_{letter.lower()}\');'
                     f'if(e){{(e.querySelector(\'button\')||e).click();}}" '
                     f'onmouseover="{hin}" onmouseout="{hout}"')
        opts += (f'<div {click} style="display:flex;align-items:center;gap:12px;background:{rbg};border:{rborder};'
                 f'border-radius:12px;padding:13px 16px;margin-bottom:8px;'
                 f'cursor:{"default" if revealed else "pointer"};transition:all .15s;user-select:none;">'
                 f'<div style="width:30px;height:30px;border-radius:8px;background:{lbg};flex-shrink:0;'
                 f'display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:{lclr};">{icon}</div>'
                 f'<div style="color:{tclr};font-size:14px;font-weight:{fw};line-height:1.45;'
                 f'font-family:\'Cambria Math\',Georgia,\'Segoe UI\',sans-serif;">{opt_rendered}</div></div>')
    exp = ""
    if revealed:
        exp_text = q.get("explanation") or ("Correct answer: " + q["answer"])
        exp_rendered = _html.escape(render_math(exp_text))
        exp = (f'<div style="background:#0f172a;border-left:3px solid #4F46E5;border-radius:0 10px 10px 0;'
               f'padding:13px 16px;margin-top:4px;color:#94a3b8;font-size:13px;line-height:1.6;">'
               f'💡 <strong style="color:#c7d2fe;">Why:</strong> {exp_rendered}</div>')
    spill = (f'<span style="background:#10b98120;color:#34d399;border:1px solid #10b98140;'
             f'border-radius:20px;padding:3px 12px;font-size:11px;font-weight:700;">✅ {score}/{index+1}</span>') if revealed or score > 0 else ""
    if revealed:
        is_last = (index >= total-1)
        lbl,col = ("See Results 🏆","#10b981") if is_last else ("Next Question →","#4F46E5")
        ajs = "var e=document.getElementById('rk_quiz_next');if(e){(e.querySelector('button')||e).click();}"
        abtn = (f'<div onclick="{ajs}" style="margin-top:18px;background:{col};border-radius:12px;padding:14px;'
                f'color:#fff;font-size:14px;font-weight:700;text-align:center;cursor:pointer;user-select:none;"'
                f' onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">{lbl}</div>')
    elif selected:
        sjs = "var e=document.getElementById('rk_quiz_submit');if(e){(e.querySelector('button')||e).click();}"
        abtn = (f'<div onclick="{sjs}" style="margin-top:18px;background:#4F46E5;border-radius:12px;padding:14px;'
                f'color:#fff;font-size:14px;font-weight:700;text-align:center;cursor:pointer;user-select:none;"'
                f' onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">Submit Answer ✅</div>')
    else:
        abtn = ('<div style="margin-top:18px;background:#0f172a;border:1px dashed #334155;border-radius:12px;'
                'padding:13px;color:#475569;font-size:13px;text-align:center;">Select an answer to continue</div>')
    return (f'<div style="font-family:\'Segoe UI\',sans-serif;padding:4px 0;">'
            f'<div style="background:#1e293b;border:1px solid #334155;border-radius:20px;padding:28px 32px;max-width:760px;margin:0 auto;">'
            f'<div style="background:#0f172a;border-radius:10px;height:5px;margin-bottom:20px;overflow:hidden;">'
            f'<div style="background:linear-gradient(90deg,#4F46E5,#818cf8);height:100%;border-radius:10px;width:{pct}%;"></div></div>'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">'
            f'<span style="background:#4F46E530;color:#a5b4fc;border:1px solid #4F46E550;border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;">'
            f'Q {index+1} / {total}</span>{spill}</div>'
            f'<div style="font-size:17px;font-weight:700;color:#f1f5f9;margin-bottom:20px;line-height:1.55;'
            f'font-family:\'Cambria Math\',Georgia,\'Segoe UI\',sans-serif;">{q_text_rendered}</div>'
            f'{opts}{exp}{abtn}</div></div>')

def render_quiz_empty():
    return ('<div style="font-family:\'Segoe UI\',sans-serif;padding:4px 0;">'
            '<div style="background:#1e293b;border:2px dashed #334155;border-radius:20px;max-width:760px;margin:0 auto;'
            'min-height:220px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;">'
            '<div style="font-size:36px;">📝</div>'
            '<div style="color:#64748b;font-size:15px;font-weight:600;">Generate a quiz to start</div>'
            '<div style="color:#334155;font-size:12px;">Select documents and hit Generate above</div>'
            '</div></div>')

def render_quiz_results(score, total):
    pct = int((score/total)*100) if total > 0 else 0
    if pct>=80:   emoji,msg,color = "🏆","Excellent!","#10b981"
    elif pct>=60: emoji,msg,color = "👍","Good job!","#f59e0b"
    elif pct>=40: emoji,msg,color = "📚","Keep studying!","#f97316"
    else:         emoji,msg,color = "💪","Review and retry!","#ef4444"
    return (f'<div style="display:flex;justify-content:center;padding:10px;">'
            f'<div style="background:#1e293b;border:2px solid {color};border-radius:20px;width:100%;max-width:720px;'
            f'min-height:200px;padding:40px;box-shadow:0 8px 30px rgba(0,0,0,.25);display:flex;flex-direction:column;'
            f'align-items:center;justify-content:center;font-family:\'Segoe UI\',sans-serif;text-align:center;gap:12px;">'
            f'<div style="font-size:48px;">{emoji}</div>'
            f'<div style="font-size:24px;font-weight:800;color:#f1f5f9;">Quiz Complete!</div>'
            f'<div style="font-size:15px;color:{color};font-weight:600;">{msg}</div>'
            f'<div style="display:flex;gap:32px;margin-top:8px;">'
            f'<div><div style="font-size:34px;font-weight:800;color:#10b981;">{score}</div><div style="font-size:13px;color:#94a3b8;">Correct</div></div>'
            f'<div><div style="font-size:34px;font-weight:800;color:#ef4444;">{total-score}</div><div style="font-size:13px;color:#94a3b8;">Wrong</div></div>'
            f'<div><div style="font-size:34px;font-weight:800;color:{color};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score</div></div>'
            f'</div><div style="font-size:13px;color:#94a3b8;margin-top:10px;">Use Retry Wrong Answers, Study Missed Topics, or Export Study Report below.</div></div></div>')

def qbm(): return (gr.update(interactive=True,variant="primary"),)*4 + (gr.update(interactive=False,variant="secondary"),)*3
def qam(): return (gr.update(interactive=True,variant="secondary"),)*4+(gr.update(interactive=True,variant="primary"),gr.update(interactive=False,variant="secondary"),gr.update(interactive=False,variant="secondary"))
def qrm(): return (gr.update(interactive=False,variant="secondary"),)*5+(gr.update(interactive=True,variant="primary"),gr.update(interactive=False,variant="secondary"))
def qdm(): return (gr.update(interactive=False,variant="secondary"),)*6+(gr.update(interactive=True,variant="primary"),)

def start_quiz(session_state, num_q, selected_docs, difficulty):
    session_state = ensure_session_state(session_state)
    if not is_lmstudio_online():
        return ("🔴 LM Studio is offline. Open LM Studio, load a model, and start the local server.",
                render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html())
    selected_docs = sanitize_docs(selected_docs, session_state)
    if not selected_docs: return "⚠️ No documents selected.", render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html()
    chunks = get_chunks_from_selection(selected_docs, session_state)
    if not chunks: return "⚠️ No text.", render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html()
    difficulty = difficulty if difficulty in DIFFICULTY_CHOICES else "Medium"
    requested_questions = max(1, min(int(num_q), MAX_QUIZ_QUESTIONS))
    quiz_result = generate_quiz_result(chunks=chunks, num_questions=requested_questions, difficulty=difficulty)
    questions = quiz_result.get("data", {}).get("questions", [])
    if not questions: return "⚠️ Could not generate quiz.", render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html()
    session_state["current_quiz"] = questions
    session_state["quiz_master"] = [dict(q) for q in questions]
    session_state["quiz_attempts"] = [None] * len(questions)
    session_state["quiz_wrong_questions"] = []
    session_state["quiz_sources"] = get_source_names(selected_docs, session_state)
    session_state["current_quiz_source_label"] = get_source_label(selected_docs, session_state)
    session_state["current_quiz_difficulty"] = difficulty
    session_state["quiz_session_saved"] = False
    src = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else get_library(session_state)[selected_docs[0]]["filename"]
    return (f"✅ {len(questions)} {difficulty.lower()} question(s) from: {src}{generation_status_note(quiz_result)}",
            render_quiz_question(questions[0], 0, len(questions), score=0), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html())

def quiz_select_answer(session_state, qi, letter, rev, sc):
    session_state = ensure_session_state(session_state)
    current_quiz = session_state.get("current_quiz", [])
    if not current_quiz: return render_quiz_empty(), qi, letter, rev, sc, *qbm(), session_state, render_quiz_analytics_html()
    idx = int(qi)
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz), letter, rev, sc), idx, letter, rev, sc, *qam(), session_state, render_quiz_analytics_html())

def quiz_submit(session_state, qi, letter, rev, sc):
    session_state = ensure_session_state(session_state)
    current_quiz = session_state.get("current_quiz", [])
    if not current_quiz or letter is None: return render_quiz_empty(), qi, letter, True, sc, *qam(), session_state, render_quiz_analytics_html()
    idx = int(qi); q = current_quiz[idx]
    is_correct = letter == q["answer"]
    ns = sc + (1 if is_correct else 0)
    attempts = session_state.get("quiz_attempts", [])
    while len(attempts) <= idx:
        attempts.append(None)
    attempts[idx] = {
        "question": q["question"],
        "topic": q.get("topic", "General"),
        "selected": letter,
        "correct_answer": q["answer"],
        "correct": is_correct,
        "explanation": q.get("explanation", ""),
    }
    if not is_correct:
        existing = {item.get("question", "").strip().lower() for item in session_state.get("quiz_wrong_questions", [])}
        if q["question"].strip().lower() not in existing:
            session_state["quiz_wrong_questions"].append(dict(q))
    return (render_quiz_question(q, idx, len(current_quiz), letter, True, ns), idx, letter, True, ns, *qrm(), session_state, render_quiz_analytics_html())

def quiz_next(session_state, qi, letter, rev, sc):
    session_state = ensure_session_state(session_state)
    current_quiz = session_state.get("current_quiz", [])
    if not current_quiz: return render_quiz_empty(), 0, None, False, sc, *qbm(), session_state, render_quiz_analytics_html()
    idx = int(qi)+1
    if idx >= len(current_quiz):
        if not session_state.get("quiz_session_saved"):
            attempts = [item for item in session_state.get("quiz_attempts", []) if item]
            record_quiz_session(
                sources=session_state.get("quiz_sources", []),
                difficulty=session_state.get("current_quiz_difficulty", "Medium"),
                score=sc,
                total=len(current_quiz),
                attempts=attempts,
            )
            session_state["quiz_session_saved"] = True
        return render_quiz_results(sc, len(current_quiz)), idx-1, None, False, sc, *qdm(), session_state, render_quiz_analytics_html()
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz), score=sc), idx, None, False, sc, *qbm(), session_state, render_quiz_analytics_html())

def quiz_restart(session_state):
    session_state = ensure_session_state(session_state)
    current_quiz = session_state.get("current_quiz", [])
    if not current_quiz: return render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html()
    session_state["quiz_attempts"] = [None] * len(current_quiz)
    session_state["quiz_wrong_questions"] = []
    session_state["quiz_session_saved"] = False
    return (render_quiz_question(current_quiz[0], 0, len(current_quiz), score=0), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html())

def retry_wrong_quiz(session_state):
    session_state = ensure_session_state(session_state)
    wrong_questions = dedupe_cards(session_state.get("quiz_wrong_questions", []))
    if not wrong_questions:
        return ("ℹ️ No wrong answers to retry yet.",
                render_quiz_empty(), 0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html())
    session_state["current_quiz"] = [dict(item) for item in wrong_questions]
    session_state["quiz_attempts"] = [None] * len(wrong_questions)
    session_state["quiz_wrong_questions"] = []
    session_state["quiz_session_saved"] = False
    return (f"🔁 Retrying {len(wrong_questions)} wrong question(s).",
            render_quiz_question(session_state["current_quiz"][0], 0, len(session_state["current_quiz"]), score=0),
            0, None, False, 0, *qbm(), session_state, render_quiz_analytics_html())

def study_missed_topics(session_state):
    session_state = ensure_session_state(session_state)
    wrong_questions = session_state.get("quiz_wrong_questions", [])
    if not wrong_questions:
        return "ℹ️ No missed topics yet.", render_quiz_analytics_html(title="Missed Topics"), session_state
    return (
        f"📌 Studying missed topics from {len(wrong_questions)} wrong answer(s).",
        render_missed_topics_html(session_state),
        session_state,
    )

def export_current_quiz_report(session_state):
    session_state = ensure_session_state(session_state)
    attempts = [item for item in session_state.get("quiz_attempts", []) if item]
    if not attempts:
        return None, "ℹ️ Complete a quiz before exporting a study report."
    score = sum(1 for item in attempts if item.get("correct"))
    report_path = export_quiz_report(
        attempts=attempts,
        score=score,
        total=len(session_state.get("current_quiz") or session_state.get("quiz_master") or attempts),
        sources=session_state.get("quiz_sources", []),
        difficulty=session_state.get("current_quiz_difficulty", "Medium"),
        weak_topics=get_quiz_analytics().get("topics", []),
    )
    return report_path, f"📄 Quiz study report exported to: {os.path.basename(report_path)}"

# ── Flashcards ────────────────────────────────────────────────────
CARD_COLORS = ["#4F46E5","#0891B2","#059669","#D97706","#DC2626","#7C3AED"]

def qmode(): return (gr.update(interactive=True,variant="secondary"),gr.update(interactive=True,variant="primary"),gr.update(interactive=False,variant="secondary"),gr.update(interactive=False,variant="secondary"),gr.update(interactive=False,variant="secondary"))
def amode(): return (gr.update(interactive=False,variant="secondary"),gr.update(interactive=False,variant="secondary"),gr.update(interactive=True,variant="primary"),gr.update(interactive=True,variant="secondary"),gr.update(interactive=False,variant="secondary"))
def dmode(): return (gr.update(interactive=False,variant="secondary"),)*4+(gr.update(interactive=True,variant="primary"),)

def render_score_bar(correct, wrong, total):
    ans = correct+wrong
    if ans == 0: return ""
    pct = int((correct/ans)*100); bf = int((correct/total)*100)
    return (f'<div style="max-width:680px;margin:0 auto 10px auto;font-family:\'Segoe UI\',sans-serif;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
            f'<span style="color:#94a3b8;font-size:13px;">Score: {ans}/{total} answered</span>'
            f'<span style="font-size:14px;font-weight:700;color:#10b981;">✅ {correct} &nbsp;❌ {wrong} &nbsp;{pct}%</span></div>'
            f'<div style="background:#1e293b;border-radius:10px;height:8px;overflow:hidden;">'
            f'<div style="background:#10b981;width:{bf}%;height:100%;border-radius:10px;"></div></div></div>')

def render_results_html(correct, wrong, total):
    pct = int((correct/total)*100) if total > 0 else 0
    if pct>=80:   e,m,c="🏆","Excellent work!","#10b981"
    elif pct>=60: e,m,c="👍","Good job!","#f59e0b"
    elif pct>=40: e,m,c="📚","Keep practising!","#f97316"
    else:         e,m,c="💪","Don't give up!","#ef4444"
    return (f'<div style="display:flex;justify-content:center;padding:10px;">'
            f'<div style="background:#1e293b;border:2px solid {c};border-radius:20px;width:100%;max-width:680px;'
            f'min-height:280px;padding:40px 50px;box-shadow:0 8px 30px rgba(0,0,0,.25);display:flex;flex-direction:column;'
            f'align-items:center;justify-content:center;font-family:\'Segoe UI\',sans-serif;text-align:center;gap:16px;">'
            f'<div style="font-size:52px;">{e}</div>'
            f'<div style="font-size:26px;font-weight:800;color:#f1f5f9;">Session Complete!</div>'
            f'<div style="font-size:16px;color:{c};font-weight:600;">{m}</div>'
            f'<div style="display:flex;gap:32px;margin-top:8px;">'
            f'<div><div style="font-size:36px;font-weight:800;color:#10b981;">{correct}</div><div style="font-size:13px;color:#94a3b8;">Correct ✅</div></div>'
            f'<div><div style="font-size:36px;font-weight:800;color:#ef4444;">{wrong}</div><div style="font-size:13px;color:#94a3b8;">Wrong ❌</div></div>'
            f'<div><div style="font-size:36px;font-weight:800;color:{c};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score 📊</div></div></div>'
            f'<div style="font-size:13px;color:#475569;margin-top:8px;">Use Study Again, Study Missed Cards, Only Hard Cards, or Export CSV below.</div>'
            f'</div></div>')

def render_card_html(card, index, total, revealed, correct=0, wrong=0):
    color = CARD_COLORS[index % len(CARD_COLORS)]
    sb = render_score_bar(correct, wrong, total)
    if not revealed:
        sl,content,tc,bg,bs = "QUESTION",_html.escape(render_math(card["question"])),"#ffffff",color,"border:none;"
        hint = "<div style='margin-top:24px;text-align:center;font-size:12px;color:rgba(255,255,255,.4);'>Think of the answer, then click 🔄 Reveal Answer</div>"
    else:
        sl,content,tc,bg = "ANSWER",_html.escape(render_math(card["answer"])),"#1e293b","#f8fafc"
        bs = f"border:4px solid {color};"
        hint = "<div style='margin-top:24px;text-align:center;font-size:12px;color:rgba(0,0,0,.35);'>Did you remember it? Click ✅ or ❌ below</div>"
    ra = "0,0,0" if revealed else "255,255,255"
    tc2 = "#64748b" if revealed else "#fff"
    tc3 = "rgba(0,0,0,.3)" if revealed else "rgba(255,255,255,.55)"
    return (f'{sb}<div style="display:flex;justify-content:center;padding:10px;">'
            f'<div style="background:{bg};{bs}border-radius:20px;width:100%;max-width:680px;min-height:280px;'
            f'padding:40px 50px;box-shadow:0 8px 30px rgba(0,0,0,.25);display:flex;flex-direction:column;'
            f'position:relative;font-family:\'Segoe UI\',sans-serif;">'
            f'<div style="position:absolute;top:16px;right:24px;background:rgba({ra},.1);color:{tc2};'
            f'border-radius:20px;padding:4px 14px;font-size:13px;font-weight:600;">{index+1} / {total}</div>'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;'
            f'margin-bottom:16px;color:{tc3};">{sl}</div>'
            f'<div style="font-size:20px;font-weight:600;color:{tc};line-height:1.6;flex-grow:1;display:flex;align-items:center;'
            f'font-family:\'Cambria Math\',Georgia,\'Segoe UI\',sans-serif;">{content}</div>'
            f'{hint}</div></div>')

def render_empty_card():
    return ('<div style="display:flex;justify-content:center;padding:20px;">'
            '<div style="background:#1e293b;border:2px dashed #475569;border-radius:20px;'
            'width:100%;max-width:680px;min-height:280px;display:flex;align-items:center;'
            'justify-content:center;color:#94a3b8;font-size:18px;font-family:\'Segoe UI\',sans-serif;">'
            'Generate flashcards to start studying 🃏</div></div>')

def make_flashcards(session_state, num_cards, selected_docs, difficulty):
    session_state = ensure_session_state(session_state)
    if not is_lmstudio_online():
        return ("🔴 LM Studio is offline. Open LM Studio, load a model, and start the local server.",
                render_empty_card(), 0, False, 0, 0, *qmode(), session_state)
    selected_docs = sanitize_docs(selected_docs, session_state)
    if not selected_docs: return "⚠️ No documents selected.", render_empty_card(), 0, False, 0, 0, *qmode(), session_state
    chunks = get_chunks_from_selection(selected_docs, session_state)
    if not chunks: return "⚠️ No text.", render_empty_card(), 0, False, 0, 0, *qmode(), session_state
    difficulty = difficulty if difficulty in DIFFICULTY_CHOICES else "Medium"
    src = get_source_label(selected_docs, session_state)
    requested_cards = max(1, min(int(num_cards), MAX_FLASHCARDS))
    card_result = generate_flashcards_result(chunks=chunks, filename=src, num_cards=requested_cards, difficulty=difficulty)
    cards = card_result.get("data", {}).get("cards", [])
    if not cards:
        return ("⚠️ Could not generate flashcards.", render_empty_card(), 0, False, 0, 0, *qmode(), session_state)
    session_state["current_flashcards"] = [dict(card) for card in cards]
    session_state["flashcards_master"] = [dict(card) for card in cards]
    session_state["flashcard_wrong_cards"] = []
    session_state["current_flashcard_sources"] = get_source_names(selected_docs, session_state)
    session_state["current_flashcard_source_label"] = src
    session_state["current_flashcard_difficulty"] = difficulty
    return (f"✅ {len(cards)} {difficulty.lower()} flashcard(s) from: {src}{generation_status_note(card_result)}",
            render_card_html(cards[0], 0, len(cards), False), 0, False, 0, 0, *qmode(), session_state)

def reveal_answer(session_state, ci, sa, co, wo):
    session_state = ensure_session_state(session_state)
    current_flashcards = session_state.get("current_flashcards", [])
    if not current_flashcards: return render_empty_card(), ci, True, co, wo, *amode(), session_state
    idx = int(ci)
    return render_card_html(current_flashcards[idx], idx, len(current_flashcards), True, co, wo), idx, True, co, wo, *amode(), session_state

def score_correct(session_state, ci, co, wo):
    session_state = ensure_session_state(session_state)
    current_flashcards = session_state.get("current_flashcards", [])
    if not current_flashcards:
        return render_empty_card(), 0, False, co, wo, *qmode(), session_state
    current_card = current_flashcards[int(ci)]
    record_flashcard_result(current_card.get("question", ""), session_state.get("current_flashcard_source_label", ""), True)
    co += 1; total = len(current_flashcards)
    if int(ci) >= total-1: return render_results_html(co, wo, total), int(ci), False, co, wo, *dmode(), session_state
    idx = int(ci)+1
    return render_card_html(current_flashcards[idx], idx, total, False, co, wo), idx, False, co, wo, *qmode(), session_state

def score_wrong(session_state, ci, co, wo):
    session_state = ensure_session_state(session_state)
    current_flashcards = session_state.get("current_flashcards", [])
    if not current_flashcards:
        return render_empty_card(), 0, False, co, wo, *qmode(), session_state
    current_card = current_flashcards[int(ci)]
    record_flashcard_result(current_card.get("question", ""), session_state.get("current_flashcard_source_label", ""), False)
    existing = {item.get("question", "").strip().lower() for item in session_state.get("flashcard_wrong_cards", [])}
    if current_card.get("question", "").strip().lower() not in existing:
        session_state["flashcard_wrong_cards"].append(dict(current_card))
    wo += 1; total = len(current_flashcards)
    if int(ci) >= total-1: return render_results_html(co, wo, total), int(ci), False, co, wo, *dmode(), session_state
    idx = int(ci)+1
    return render_card_html(current_flashcards[idx], idx, total, False, co, wo), idx, False, co, wo, *qmode(), session_state

def prev_card(session_state, ci, co, wo):
    session_state = ensure_session_state(session_state)
    current_flashcards = session_state.get("current_flashcards", [])
    if not current_flashcards: return render_empty_card(), 0, False, co, wo, *qmode(), session_state
    idx = (int(ci)-1) % len(current_flashcards)
    return render_card_html(current_flashcards[idx], idx, len(current_flashcards), False, co, wo), idx, False, co, wo, *qmode(), session_state

def study_again(session_state):
    session_state = ensure_session_state(session_state)
    current_flashcards = session_state.get("current_flashcards", [])
    if not current_flashcards: return render_empty_card(), 0, False, 0, 0, *qmode(), session_state
    return render_card_html(current_flashcards[0], 0, len(current_flashcards), False), 0, False, 0, 0, *qmode(), session_state

def study_wrong_flashcards(session_state):
    session_state = ensure_session_state(session_state)
    wrong_cards = dedupe_cards(session_state.get("flashcard_wrong_cards", []))
    if not wrong_cards:
        return ("ℹ️ No missed cards to review yet.",
                render_empty_card(), 0, False, 0, 0, *qmode(), session_state)
    session_state["current_flashcards"] = [dict(card) for card in wrong_cards]
    return (f"🔁 Reviewing {len(wrong_cards)} missed card(s).",
            render_card_html(session_state["current_flashcards"][0], 0, len(session_state["current_flashcards"]), False),
            0, False, 0, 0, *qmode(), session_state)

def study_hard_flashcards(session_state):
    session_state = ensure_session_state(session_state)
    master_cards = session_state.get("flashcards_master", [])
    hard_cards = get_hard_flashcards(master_cards)
    if not hard_cards:
        return ("ℹ️ No hard cards identified yet. Miss a few cards first or build more history.",
                render_empty_card(), 0, False, 0, 0, *qmode(), session_state)
    session_state["current_flashcards"] = [dict(card) for card in hard_cards]
    return (f"🔥 Studying {len(hard_cards)} hard card(s).",
            render_card_html(session_state["current_flashcards"][0], 0, len(session_state["current_flashcards"]), False),
            0, False, 0, 0, *qmode(), session_state)

def export_current_flashcards(session_state):
    session_state = ensure_session_state(session_state)
    cards = session_state.get("flashcards_master") or session_state.get("current_flashcards", [])
    if not cards:
        return None, "ℹ️ Generate flashcards before exporting."
    export_path = export_flashcards_csv(
        cards=cards,
        source_label=session_state.get("current_flashcard_source_label", "studymind"),
        difficulty=session_state.get("current_flashcard_difficulty", "Medium"),
    )
    return export_path, f"📄 Flashcards exported to: {os.path.basename(export_path)}"

# ── Mindmap ───────────────────────────────────────────────────────
def render_mm_status(msg, ok=True):
    if not msg: return ""
    c = "#10b981" if ok else "#ef4444"
    return (f'<div style="background:#1e293b;border:1px solid {c}33;border-left:4px solid {c};'
            f'border-radius:12px;padding:12px 18px;font-family:\'Segoe UI\',sans-serif;'
            f'font-size:13px;color:#f1f5f9;font-weight:500;">{_html.escape(str(msg))}</div>')

def render_mm_empty():
    return ('<div style="background:#1e293b;border:2px dashed #334155;border-radius:16px;min-height:520px;'
            'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;font-family:\'Segoe UI\',sans-serif;">'
            '<div style="font-size:40px;">🗺️</div>'
            '<div style="color:#64748b;font-size:15px;font-weight:600;">No mindmap yet</div>'
            '<div style="color:#334155;font-size:12px;">Select documents and click Generate above</div>'
            '</div>')

def render_mm_loading(step="Building your mindmap…"):
    return (f'<style>@keyframes rk-spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg);}}}}</style>'
            f'<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;min-height:520px;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;font-family:\'Segoe UI\',sans-serif;">'
            f'<div style="font-size:42px;animation:rk-spin 3s linear infinite;">🗺️</div>'
            f'<div style="color:#818cf8;font-size:15px;font-weight:600;">{_html.escape(step)}</div>'
            f'<div style="color:#475569;font-size:13px;">This may take a moment…</div>'
            f'</div>')

def make_mindmap_full(session_state, topic, selected_docs):
    session_state = ensure_session_state(session_state)
    if not is_lmstudio_online():
        yield render_mm_status("🔴 LM Studio is offline. Open LM Studio, load a model, and start the local server.", ok=False), render_mm_empty(), None, session_state
        return
    selected_docs = sanitize_docs(selected_docs, session_state)
    if not selected_docs:
        yield render_mm_status("⚠️ No documents selected.", ok=False), render_mm_empty(), None, session_state
        return
    chunks = get_chunks_from_selection(selected_docs, session_state)
    if not chunks:
        yield render_mm_status("⚠️ Selected documents have no text.", ok=False), render_mm_empty(), None, session_state
        return

    title = topic.strip() if topic.strip() else (
        f"{len(selected_docs)} Documents" if len(selected_docs) > 1
        else get_library(session_state)[selected_docs[0]]["filename"].rsplit(".", 1)[0]
    )
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else get_library(session_state)[selected_docs[0]]["filename"]

    yield render_mm_status("⏳ Generating mindmap…"), render_mm_loading("Generating mindmap…"), None, session_state

    mm_result = generate_mindmap_tree_result(topic=topic, chunks=chunks)
    tree = mm_result.get("data", {}).get("tree", {})
    html_out = mindmap_to_html(tree, title=title)
    file_path = save_mindmap_file(tree, title=title)

    yield render_mm_status(f"✅ Mindmap ready · {_html.escape(source)}{generation_status_note(mm_result)} · 📂 Download below to open with full controls"), html_out, file_path, session_state



# ── Audio Overview Helpers ───────────────────────────────────────────────────

def render_audio_status(message: str = "", ok: bool = True) -> str:
    if not message:
        return ""
    color = "#10b981" if ok else "#ef4444"
    return (
        f'<div style="background:#1e293b;border:1px solid {color}33;border-left:4px solid {color};'
        'border-radius:12px;padding:13px 18px;font-family:\'Segoe UI\',sans-serif;'
        f'font-size:13px;color:#f1f5f9;white-space:pre-line;line-height:1.7;">{_html.escape(str(message))}</div>'
    )


def render_audio_empty() -> str:
    return (
        '<div style="background:#1e293b;border:2px dashed #334155;border-radius:16px;min-height:220px;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;'
        'font-family:\'Segoe UI\',sans-serif;">'
        '<div style="font-size:36px;">🎙️</div>'
        '<div style="color:#64748b;font-size:14px;font-weight:600;">Generate an audio overview to preview the transcript</div>'
        '</div>'
    )


def render_audio_loading(step: str) -> str:
    return (
        '<style>@keyframes rk-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}</style>'
        '<div style="background:#111827;border:1px solid #312e81;border-radius:16px;min-height:220px;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;'
        'font-family:\'Segoe UI\',sans-serif;">'
        '<div style="font-size:40px;animation:rk-spin 3s linear infinite;">🎙️</div>'
        f'<div style="color:#818cf8;font-size:15px;font-weight:700;">{_html.escape(step)}</div>'
        '<div style="color:#64748b;font-size:13px;">Local generation can take a moment.</div>'
        '</div>'
    )


def get_audio_context_for_doc(session_state, doc_id, duration_label):
    library = get_library(session_state)
    doc = library.get(doc_id)
    if not doc:
        return "", "No document selected"

    preset = get_duration_preset(duration_label)
    query = (
        "main ideas, key examples, misconceptions, surprising facts, conclusions, "
        "and the best educational flow for an audio overview"
    )
    try:
        evidence = search_similar_chunks(
            question=query,
            doc_id=doc_id,
            session_id=session_state["session_id"],
            top_k=int(preset.get("top_k", 8)),
            include_metadata=True,
        )
    except Exception as exc:
        evidence = []
        print(f"[audio_overview] retrieval failed, using balanced fallback: {exc}")

    if evidence:
        context = "\n\n---\n\n".join(item["text"] for item in evidence)
        chunks = ", ".join(str(item.get("chunk_index", 0) + 1) for item in evidence)
        return context, f"{doc.get('filename', 'document')} chunks {chunks}"

    try:
        ctx_words = min(adaptive_strategy.detect_model()["context_max_words"], int(preset.get("max_context_words", 4200)))
    except Exception:
        ctx_words = int(preset.get("max_context_words", 4200))
    context = build_balanced_context(doc.get("chunks", []), max_words=ctx_words, target_chunks=int(preset.get("top_k", 8)))
    return context, f"{doc.get('filename', 'document')} balanced fallback"


def make_audio_overview(session_state, doc_id, duration_label, synthesize_audio, voice_a, voice_b):
    session_state = ensure_session_state(session_state)
    library = get_library(session_state)
    if not doc_id or doc_id not in library:
        yield render_audio_status("⚠️ Select a Library document first.", ok=False), render_audio_empty(), None, None, None, session_state
        return
    if not is_lmstudio_online():
        yield render_audio_status("🔴 LM Studio is offline. Open LM Studio, load a model, and start the local server.", ok=False), render_audio_empty(), None, None, None, session_state
        return

    doc = library[doc_id]
    source_title = doc.get("filename", "Audio Overview").rsplit(".", 1)[0]
    yield (
        render_audio_status(f"⏳ Retrieving grounded context from {doc.get('filename', 'document')}…"),
        render_audio_loading("Retrieving grounded context…"),
        None,
        None,
        None,
        session_state,
    )

    context, source_note = get_audio_context_for_doc(session_state, doc_id, duration_label)
    if not context.strip():
        yield render_audio_status("⚠️ Selected document has no usable text chunks.", ok=False), render_audio_empty(), None, None, None, session_state
        return

    yield (
        render_audio_status(f"⏳ Writing staged two-host script…\nSource: {source_note}"),
        render_audio_loading("Writing transcript…"),
        None,
        None,
        None,
        session_state,
    )

    result = generate_audio_overview_result(
        source_title=source_title,
        context=context,
        duration_label=duration_label,
        voice_a=voice_a,
        voice_b=voice_b,
        synthesize_audio=bool(synthesize_audio),
    )
    if not result.get("ok"):
        note = result.get("note") or "Audio overview generation failed."
        yield render_audio_status(f"❌ {note}", ok=False), render_audio_empty(), None, None, None, session_state
        return

    data = result.get("data", {})
    script = data.get("script")
    audio_path = data.get("audio_path") or None
    transcript_path = data.get("transcript_md") or None
    turns = result.get("counts", {}).get("turns", 0)
    note = result.get("note", "")
    status = f"✅ Audio overview ready · {turns} turns · Source: {source_note}"
    if note:
        status += f"\n{note}"
    yield (
        render_audio_status(status, ok=True),
        render_transcript_html(script),
        audio_path,
        audio_path,
        transcript_path,
        session_state,
    )


# ── Coding Helpers ──────────────────────────────────────────────────────────

def render_ca_empty_output() -> str:
    return (
        '<div style="background:#1e293b;border:2px dashed #334155;border-radius:16px;min-height:180px;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;'
        'font-family:\'Segoe UI\',sans-serif;">'
        '<div style="font-size:36px;">⚡</div>'
        '<div style="color:#64748b;font-size:14px;font-weight:600;">Load a file, pick a mode, and run</div>'
        '</div>'
    )


def ca_load_file_fn(session_state, doc_id):
    session_state = ensure_session_state(session_state)
    library = get_library(session_state)
    if not doc_id or doc_id not in library:
        return render_code_empty_state(), "", "", "⚠️ Select a code file."
    info = library[doc_id]
    filename = info.get("filename", "")
    code_text = info.get("code_text", "") or "\n".join(info.get("chunks", []))
    if not code_text:
        return render_code_empty_state(), "", filename, "⚠️ No code content found."
    lang = get_language_from_filename(filename)
    preview = syntax_highlight_html(code_text, lang, filename)
    lines = len(code_text.split("\n"))
    return preview, code_text, filename, f"✅ Loaded: {filename}  ({lines} lines)"


def ca_switch_mode(mode: str):
    def btn(active): return gr.update(variant="primary" if active else "secondary")
    def col(active): return gr.update(visible=active)
    return (
        mode,
        btn(mode == "explain"), btn(mode == "ask_ai"),
        col(mode == "explain"), col(mode == "ask_ai"),
    )


def ca_run_explain_fn(code_text, filename):
    if not code_text:
        return '<div style="color:#f87171;padding:16px;font-family:\'Segoe UI\',sans-serif;">⚠️ Load a code file first.</div>'
    return render_explain_html(explain_code(code_text, filename), filename)


def ca_run_qa_fn(code_text, question, history):
    history = list(history or [])
    if not code_text:
        return render_qa_history_html(history), history, ""
    if not (question or "").strip():
        return render_qa_history_html(history), history, ""
    answer = qa_code(code_text, question, history)
    history.append((question, answer))
    return render_qa_history_html(history), history, ""


def ca_clear_qa_fn():
    return render_qa_history_html([]), []


# ── CSS ───────────────────────────────────────────────────────────
css = """
html, body {
  background: #060b18 !important;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
.gradio-container {
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 16px 24px 40px !important;
  background: transparent !important;
}
footer { display: none !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4F46E5; }
#rk-app-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; background: #0d1117;
  border: 1px solid #1e293b; border-radius: 14px; margin-bottom: 18px;
}
#rk-app-header .rk-logo { font-size: 28px; line-height: 1; }
#rk-app-header .rk-title { font-size: 19px; font-weight: 800; color: #f1f5f9; letter-spacing: -0.3px; }
#rk-app-header .rk-subtitle { font-size: 12px; color: #475569; margin-top: 1px; }
#rk-app-header .rk-spacer { flex: 1; }
#rk-app-header .rk-badge {
  background: #1e293b; border: 1px solid #334155;
  color: #818cf8; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;
  padding: 4px 12px; border-radius: 20px; text-transform: uppercase;
}
.tabs > .tab-nav {
  background: #0d1117 !important; border-bottom: 1px solid #1e293b !important;
  border-radius: 12px 12px 0 0 !important; padding: 4px 8px 0 !important; gap: 2px !important;
}
.tabs > .tab-nav > button {
  background: transparent !important; border: none !important;
  border-bottom: 2px solid transparent !important; color: #475569 !important;
  font-size: 13px !important; font-weight: 600 !important;
  padding: 10px 16px !important; border-radius: 8px 8px 0 0 !important;
  transition: color 0.15s, border-color 0.15s, background 0.15s !important; cursor: pointer !important;
}
.tabs > .tab-nav > button:hover { color: #94a3b8 !important; background: #1e293b44 !important; }
.tabs > .tab-nav > button.selected {
  color: #a5b4fc !important; border-bottom-color: #4F46E5 !important; background: #1e293b66 !important;
}
.tabitem {
  background: #0d1117 !important; border: 1px solid #1e293b !important;
  border-top: none !important; border-radius: 0 0 12px 12px !important; padding: 20px !important;
}
input[type="range"] { accent-color: #4F46E5 !important; }
input[type="checkbox"], input[type="radio"] { accent-color: #4F46E5 !important; }
#rk_chat_display {
  height: 500px; overflow-y: scroll; overflow-x: hidden; padding-right: 4px;
  scrollbar-width: thin; scrollbar-color: #4F46E5 #0f172a;
}
#rk_chat_display::-webkit-scrollbar { width: 8px; }
#rk_chat_display::-webkit-scrollbar-track { background: #0f172a; }
#rk_chat_display::-webkit-scrollbar-thumb { background: #4F46E5; border-radius: 4px; }
#rk_chat_display::-webkit-scrollbar-thumb:hover { background: #818cf8; }
@keyframes rk-dot-bounce {
  0%,80%,100% { transform: translateY(0); opacity: .4; }
  40%          { transform: translateY(-7px); opacity: 1; }
}
.rk-dot {
  display: inline-block; width: 7px; height: 7px;
  border-radius: 50%; background: #818cf8; margin: 0 2px;
  animation: rk-dot-bounce 1.3s ease-in-out infinite;
}
.rk-dot:nth-child(1) { animation-delay: 0s; }
.rk-dot:nth-child(2) { animation-delay: .18s; }
.rk-dot:nth-child(3) { animation-delay: .36s; }
.rk-hidden-btn {
  position: absolute !important; width: 1px !important; height: 1px !important;
  overflow: hidden !important; clip: rect(0,0,0,0) !important;
  white-space: nowrap !important; pointer-events: none !important; opacity: 0 !important;
}
"""


EMPTY_SESSION = {
    "session_id": "preview",
    "library": {},
    "active_doc_id": "",
    "chat_log": [],
    "current_flashcards": [],
    "current_quiz": [],
}


# ── UI ────────────────────────────────────────────────────────────
_COMBINED_CSS = css + "\n" + _SPLASH_CSS

with gr.Blocks(title="🧠 RK StudyMind") as demo:
    session_state = gr.State(None)

    gr.HTML("""
<div id="rk-app-header">
  <div class="rk-logo">🧠</div>
  <div>
    <div class="rk-title">RK StudyMind</div>
    <div class="rk-subtitle">Your personal study companion</div>
  </div>
  <div class="rk-spacer"></div>
  <div class="rk-badge">v1.3</div>
</div>
""")

    with gr.Tabs():

        # 0: Home
        with gr.Tab("🏠 Home"):
            home_html = gr.HTML(value=render_home_stats(EMPTY_SESSION))

            gr.HTML('<div style="border-top:1px solid #1e293b;margin:16px 0;"></div>')
            gr.HTML('<div style="font-size:11px;font-weight:700;color:#475569;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">🤖 AI Engine</div>')
            engine_status_html = gr.HTML(value=render_engine_status_html())

            gr.HTML('<div style="border-top:1px solid #1e293b;margin:16px 0;"></div>')
            refresh_home_btn = gr.Button("🔄 Refresh Stats & Check AI", variant="primary", size="lg")

        # 1: Library
        with gr.Tab("📚 Library"):
            gr.HTML('<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #4F46E5;border-radius:8px;padding:10px 16px;font-size:12.5px;color:#64748b;margin-bottom:4px;">📎 Supported: <strong style="color:#94a3b8;">PDF · DOCX · TXT · MD · PPTX · EPUB · PY · JS · TS · C · CPP · JAVA · HTML · CSS</strong> &nbsp;·&nbsp; Max 25 MB per file &nbsp;·&nbsp; All tabs update automatically after upload.</div>')
            with gr.Row():
                file_input = gr.File(label="Upload PDF, DOCX, TXT, MD, PPTX, EPUB or Code (.py .js .ts .c .cpp .java .html .css)", file_types=[".pdf",".docx",".txt",".md",".pptx",".epub",".py",".js",".ts",".c",".cpp",".java",".html",".css"], file_count="multiple")
                upload_btn = gr.Button("Add to Library 📚", variant="primary", scale=0)
            upload_info    = gr.HTML("")
            gr.Markdown("---")
            library_html   = gr.HTML(value=render_library_html({}, ""))
            lib_doc_status = gr.Textbox(label="Active Document", interactive=False, lines=1, value=get_doc_status(EMPTY_SESSION))
            doc_selector   = gr.Radio(label="📂 Select a document", choices=[], value=None, interactive=True)
            with gr.Row():
                set_active_btn = gr.Button("✅ Set as Active", variant="primary",   scale=1)
                remove_btn     = gr.Button("🗑 Remove",         variant="secondary", scale=1)
                refresh_btn    = gr.Button("🔄 Refresh",         variant="secondary", scale=1)

        # 2: Q&A
        with gr.Tab("💬 Q&A"):
            qa_status_html    = gr.HTML(value=render_qa_status_html(EMPTY_SESSION))
            search_mode       = gr.Radio(choices=["🔍 Active Document Only","🌐 All Documents"],
                                         value="🔍 Active Document Only", label="Search Scope")
            chat_html_display = gr.HTML(value=render_chat_bubbles(EMPTY_SESSION), elem_id="rk_chat_display")
            with gr.Row():
                question_input = gr.Textbox(label="Your question",
                    placeholder="e.g. What is Newton's first law?", lines=2, scale=5,
                    elem_id="rk_qa_input")
                ask_btn = gr.Button("Ask 🔍", variant="primary", scale=1)
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            ask_btn.click(fn=answer_question, inputs=[session_state,question_input,chat_html_display,search_mode], outputs=[chat_html_display,question_input,session_state])
            question_input.submit(fn=answer_question, inputs=[session_state,question_input,chat_html_display,search_mode], outputs=[chat_html_display,question_input,session_state])
            clear_btn.click(fn=clear_chat, inputs=[session_state], outputs=[chat_html_display,question_input,session_state])

        # 3: Quiz
        with gr.Tab("📝 Quiz"):
            quiz_doc_selector = gr.CheckboxGroup(label="📄 Select Documents", choices=[], value=[], interactive=True)
            with gr.Row():
                num_q_slider    = gr.Slider(minimum=3, maximum=30, value=5, step=1, label="Questions", scale=3)
                quiz_difficulty = gr.Radio(DIFFICULTY_CHOICES, value="Medium", label="Difficulty", scale=3)
                start_quiz_btn  = gr.Button("Generate Quiz 📝", variant="primary", scale=2)
            quiz_status   = gr.Textbox(label="Status", interactive=False, lines=1)
            quiz_html_out = gr.HTML(value=render_quiz_empty())
            q_idx = gr.State(0); sel_ans = gr.State(None); rev_ans = gr.State(False); sc_ans = gr.State(0)
            with gr.Row(elem_classes=["rk-hidden-btn"]):
                btn_a = gr.Button("A", elem_id="rk_quiz_btn_a")
                btn_b = gr.Button("B", elem_id="rk_quiz_btn_b")
                btn_c = gr.Button("C", elem_id="rk_quiz_btn_c")
                btn_d = gr.Button("D", elem_id="rk_quiz_btn_d")
                sub_btn = gr.Button("Submit", elem_id="rk_quiz_submit")
                nxt_btn = gr.Button("Next",   elem_id="rk_quiz_next")
                rst_btn = gr.Button("Restart",elem_id="rk_quiz_restart")
            with gr.Accordion("📋 After Quiz", open=False):
                with gr.Row():
                    retry_wrong_btn  = gr.Button("🔁 Retry Wrong Answers", variant="secondary")
                    study_topics_btn = gr.Button("📌 Study Missed Topics",  variant="secondary")
                    export_quiz_btn  = gr.Button("📄 Export Report",        variant="secondary")
                quiz_export_file    = gr.File(label="Study Report", interactive=False)
                quiz_analytics_html = gr.HTML(value=render_quiz_analytics_html())
            qbo   = [btn_a,btn_b,btn_c,btn_d,sub_btn,nxt_btn,rst_btn]
            qouts = [quiz_html_out,q_idx,sel_ans,rev_ans,sc_ans]+qbo+[session_state, quiz_analytics_html]
            start_quiz_btn.click(fn=start_quiz, inputs=[session_state,num_q_slider,quiz_doc_selector,quiz_difficulty],
                outputs=[quiz_status,quiz_html_out,q_idx,sel_ans,rev_ans,sc_ans]+qbo+[session_state, quiz_analytics_html])
            btn_a.click(fn=lambda s,qi,sel,rev,sc:quiz_select_answer(s,qi,"A",rev,sc), inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_b.click(fn=lambda s,qi,sel,rev,sc:quiz_select_answer(s,qi,"B",rev,sc), inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_c.click(fn=lambda s,qi,sel,rev,sc:quiz_select_answer(s,qi,"C",rev,sc), inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_d.click(fn=lambda s,qi,sel,rev,sc:quiz_select_answer(s,qi,"D",rev,sc), inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            sub_btn.click(fn=quiz_submit,  inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            nxt_btn.click(fn=quiz_next,    inputs=[session_state,q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            rst_btn.click(fn=quiz_restart, inputs=[session_state], outputs=qouts)
            retry_wrong_btn.click(fn=retry_wrong_quiz, inputs=[session_state],
                outputs=[quiz_status,quiz_html_out,q_idx,sel_ans,rev_ans,sc_ans]+qbo+[session_state, quiz_analytics_html])
            study_topics_btn.click(fn=study_missed_topics, inputs=[session_state], outputs=[quiz_status, quiz_analytics_html, session_state])
            export_quiz_btn.click(fn=export_current_quiz_report, inputs=[session_state], outputs=[quiz_export_file, quiz_status])

        # 4: Flashcards
        with gr.Tab("🃏 Flashcards"):
            fc_selector = gr.CheckboxGroup(label="📄 Select Documents", choices=[], value=[], interactive=True)
            with gr.Row():
                num_cards_slider = gr.Slider(minimum=5, maximum=30, value=10, step=5, label="Cards", scale=3)
                fc_difficulty    = gr.Radio(DIFFICULTY_CHOICES, value="Medium", label="Difficulty", scale=3)
                generate_btn     = gr.Button("Generate Flashcards 🃏", variant="primary", scale=2)
            fc_status         = gr.Textbox(label="Status", interactive=False, lines=1)
            card_html_display = gr.HTML(value=render_empty_card())
            card_idx=gr.State(0); show_ans=gr.State(False); correct_st=gr.State(0); wrong_st=gr.State(0)
            with gr.Row():
                prev_btn        = gr.Button("⬅️ Prev",   variant="secondary", interactive=True,  scale=1)
                reveal_btn      = gr.Button("🔄 Reveal", variant="primary",   interactive=True,  scale=2)
                correct_btn     = gr.Button("✅ Got It",  variant="secondary", interactive=False, scale=1)
                wrong_btn_fc    = gr.Button("❌ Missed",  variant="secondary", interactive=False, scale=1)
                study_again_btn = gr.Button("🔁 Again",   variant="secondary", interactive=False, scale=1)
            with gr.Accordion("📋 More Options", open=False):
                with gr.Row():
                    study_wrong_btn  = gr.Button("📚 Study Missed Cards", variant="secondary")
                    hard_cards_btn   = gr.Button("🔥 Hard Cards Only",     variant="secondary")
                    export_cards_btn = gr.Button("📤 Export CSV (Anki)",   variant="secondary")
                fc_export_file = gr.File(label="Flashcards CSV", interactive=False)
            card_outs = [card_html_display,card_idx,show_ans,correct_st,wrong_st,
                         prev_btn,reveal_btn,correct_btn,wrong_btn_fc,study_again_btn,session_state]
            generate_btn.click(fn=make_flashcards, inputs=[session_state,num_cards_slider,fc_selector,fc_difficulty],
                outputs=[fc_status,card_html_display,card_idx,show_ans,correct_st,wrong_st,
                         prev_btn,reveal_btn,correct_btn,wrong_btn_fc,study_again_btn,session_state])
            reveal_btn.click(fn=reveal_answer,  inputs=[session_state,card_idx,show_ans,correct_st,wrong_st], outputs=card_outs)
            correct_btn.click(fn=score_correct, inputs=[session_state,card_idx,correct_st,wrong_st],          outputs=card_outs)
            wrong_btn_fc.click(fn=score_wrong,  inputs=[session_state,card_idx,correct_st,wrong_st],          outputs=card_outs)
            prev_btn.click(fn=prev_card,        inputs=[session_state,card_idx,correct_st,wrong_st],          outputs=card_outs)
            study_again_btn.click(fn=study_again, inputs=[session_state],                                      outputs=card_outs)
            study_wrong_btn.click(fn=study_wrong_flashcards, inputs=[session_state],
                outputs=[fc_status,card_html_display,card_idx,show_ans,correct_st,wrong_st,
                         prev_btn,reveal_btn,correct_btn,wrong_btn_fc,study_again_btn,session_state])
            hard_cards_btn.click(fn=study_hard_flashcards, inputs=[session_state],
                outputs=[fc_status,card_html_display,card_idx,show_ans,correct_st,wrong_st,
                         prev_btn,reveal_btn,correct_btn,wrong_btn_fc,study_again_btn,session_state])
            export_cards_btn.click(fn=export_current_flashcards, inputs=[session_state], outputs=[fc_export_file, fc_status])

        # 5: Mindmap
        with gr.Tab("🗺️ Mindmap"):
            gr.HTML('<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #4F46E5;border-radius:8px;padding:10px 16px;font-size:12.5px;color:#64748b;margin-bottom:8px;">🗺️ Generates a structured study tree from your selected documents. &nbsp;<strong style="color:#94a3b8;">Expand</strong>, <strong style="color:#94a3b8;">collapse</strong>, fit, zoom, or export from the tree toolbar.</div>')
            mm_doc_selector = gr.CheckboxGroup(label="📄 Select Documents for Mindmap", choices=[], value=[], interactive=True)
            with gr.Row():
                topic_input     = gr.Textbox(label="Topic (optional)", placeholder="Leave blank to auto-detect", lines=1, scale=3)
                mm_generate_btn = gr.Button("Generate Mindmap 🗺️", variant="primary", scale=0)
            mm_status_html = gr.HTML("")
            mm_display     = gr.HTML(value=render_mm_empty())
            with gr.Accordion("📂 Open in Browser (recommended for full controls)", open=True):
                gr.HTML('<div style="font-size:12px;color:#64748b;margin-bottom:6px;">Download the .html file below to open the same structured tree in your browser.</div>')
                mm_file_out = gr.File(label="Mindmap HTML File", interactive=False)
            mm_generate_btn.click(fn=make_mindmap_full,
                inputs=[session_state, topic_input, mm_doc_selector],
                outputs=[mm_status_html, mm_display, mm_file_out, session_state])

        # 6: Audio Overview
        with gr.Tab("🎙️ Audio"):
            gr.HTML('<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #4F46E5;border-radius:8px;padding:10px 16px;font-size:12.5px;color:#64748b;margin-bottom:10px;">'
                    '🎙️ <strong style="color:#94a3b8;">Audio Overview</strong> — Generate a grounded two-host study transcript and synthesize local audio when Piper voices are configured.</div>')

            with gr.Row():
                audio_doc_selector = gr.Dropdown(
                    label="📄 Library Document",
                    choices=[], value=None, interactive=True, scale=3,
                )
                audio_duration = gr.Radio(
                    AUDIO_DURATION_CHOICES,
                    value=DEFAULT_DURATION,
                    label="Length",
                    scale=2,
                )
                audio_generate_btn = gr.Button("Generate Audio 🎙️", variant="primary", scale=1)

            with gr.Accordion("🎛️ Local Voice Setup", open=False):
                audio_synthesize_check = gr.Checkbox(
                    label="Synthesize with Piper if available",
                    value=True,
                    interactive=True,
                )
                with gr.Row():
                    audio_voice_a = gr.Textbox(
                        label="Host A voice (.onnx)",
                        placeholder="Optional path or STUDYMIND_PIPER_VOICE_A",
                        lines=1,
                    )
                    audio_voice_b = gr.Textbox(
                        label="Host B voice (.onnx)",
                        placeholder="Optional path or STUDYMIND_PIPER_VOICE_B",
                        lines=1,
                    )
                gr.HTML('<div style="font-size:12px;color:#64748b;line-height:1.6;">Put Piper <code>.onnx</code> voices in <code>StudyMind\\voices</code> for automatic Host A/Host B selection. Manual paths and <code>STUDYMIND_PIPER_VOICE_A</code> / <code>STUDYMIND_PIPER_VOICE_B</code> still override folder detection. If audio is unavailable, StudyMind still exports the transcript.</div>')

            audio_status_html = gr.HTML("")
            with gr.Row():
                audio_player = gr.Audio(label="Audio Overview", type="filepath", interactive=False, scale=2)
                with gr.Column(scale=1):
                    audio_file_out = gr.File(label="Audio File", interactive=False)
                    audio_transcript_file = gr.File(label="Transcript", interactive=False)
            audio_transcript_html = gr.HTML(value=render_audio_empty())

            audio_generate_btn.click(
                fn=make_audio_overview,
                inputs=[session_state, audio_doc_selector, audio_duration, audio_synthesize_check, audio_voice_a, audio_voice_b],
                outputs=[audio_status_html, audio_transcript_html, audio_player, audio_file_out, audio_transcript_file, session_state],
            )

        # 7: Coding
        with gr.Tab("⚡ Coding"):
            gr.HTML('<div style="background:#0f172a;border:1px solid #1e293b;border-left:3px solid #4F46E5;border-radius:8px;padding:10px 16px;font-size:12.5px;color:#64748b;margin-bottom:10px;">'
                    '⚡ <strong style="color:#94a3b8;">Coding</strong> — Explain code or ask AI questions about loaded source files. '
                    'Upload code files (<code>.py .js .ts .c .cpp .java .html .css</code>) to the 📚 Library tab first.</div>')

            # Mode switcher
            ca_mode_state = gr.State("explain")
            with gr.Row():
                ca_explain_btn = gr.Button("🔍 Explain", variant="primary",   size="sm", scale=1)
                ca_qa_btn      = gr.Button("💬 Ask AI",   variant="secondary", size="sm", scale=1)

            gr.HTML('<div style="border-top:1px solid #1e293b;margin:10px 0;"></div>')

            # File picker (Library-sourced)
            ca_file_selector = gr.Dropdown(
                label="📁 Code File from Library",
                choices=[], value=None, interactive=True,
            )
            with gr.Row():
                ca_load_btn    = gr.Button("Load & Preview 📂", variant="secondary", size="sm", scale=0)
                ca_load_status = gr.Textbox(label="", value="", interactive=False, lines=1, scale=4)
            ca_code_preview = gr.HTML(value=render_code_empty_state())
            ca_code_state   = gr.State("")
            ca_fname_state  = gr.State("")

            gr.HTML('<div style="border-top:1px solid #1e293b;margin:12px 0;"></div>')

            # Explain section
            with gr.Column(visible=True) as ca_explain_col:
                ca_explain_run = gr.Button("🔍 Explain This Code", variant="primary")
                ca_explain_out = gr.HTML(value=render_ca_empty_output())

            # Ask AI section
            with gr.Column(visible=False) as ca_qa_col:
                ca_qa_state    = gr.State([])
                ca_qa_hist_html = gr.HTML(value=render_qa_history_html([]))
                with gr.Row():
                    ca_qa_input = gr.Textbox(
                        label="Ask a question about the code",
                        placeholder="e.g. What does this function return? How does the loop work?",
                        lines=2, scale=5,
                    )
                    ca_qa_run   = gr.Button("Ask 💬", variant="primary", scale=1)
                ca_qa_clear_btn = gr.Button("Clear Chat 🗑️", variant="secondary", size="sm")

            # ── Coding wiring ─────────────────────────────────────────────
            _ca_mode_outs = [
                ca_mode_state,
                ca_explain_btn, ca_qa_btn,
                ca_explain_col, ca_qa_col,
                # outputs are NOT cleared on mode switch — spec: preserve loaded file and current output
            ]
            ca_explain_btn.click(fn=lambda: ca_switch_mode("explain"), outputs=_ca_mode_outs)
            ca_qa_btn.click(     fn=lambda: ca_switch_mode("ask_ai"),  outputs=_ca_mode_outs)

            # Load file
            ca_load_btn.click(
                fn=ca_load_file_fn,
                inputs=[session_state, ca_file_selector],
                outputs=[ca_code_preview, ca_code_state, ca_fname_state, ca_load_status],
            )

            # Explain
            ca_explain_run.click(
                fn=ca_run_explain_fn,
                inputs=[ca_code_state, ca_fname_state],
                outputs=[ca_explain_out],
            )

            # Ask AI
            ca_qa_run.click(
                fn=ca_run_qa_fn,
                inputs=[ca_code_state, ca_qa_input, ca_qa_state],
                outputs=[ca_qa_hist_html, ca_qa_state, ca_qa_input],
            )
            ca_qa_input.submit(
                fn=ca_run_qa_fn,
                inputs=[ca_code_state, ca_qa_input, ca_qa_state],
                outputs=[ca_qa_hist_html, ca_qa_state, ca_qa_input],
            )
            ca_qa_clear_btn.click(fn=ca_clear_qa_fn, outputs=[ca_qa_hist_html, ca_qa_state])

    # ── Wiring ────────────────────────────────────────────────────
    refresh_home_btn.click(
        fn=refresh_home,
        inputs=[session_state],
        outputs=[home_html, engine_status_html, session_state],
    )

    lib_sync = [library_html, lib_doc_status, doc_selector,
                quiz_doc_selector, fc_selector, mm_doc_selector, audio_doc_selector,
                qa_status_html, ca_file_selector, session_state]

    upload_btn.click(fn=load_files, inputs=[session_state, file_input],
        outputs=[upload_info, library_html, lib_doc_status, doc_selector,
                 quiz_doc_selector, fc_selector, mm_doc_selector, audio_doc_selector,
                 qa_status_html, ca_file_selector, home_html, session_state])
    set_active_btn.click(fn=switch_active_doc, inputs=[session_state, doc_selector], outputs=lib_sync)
    remove_btn.click(fn=delete_doc,            inputs=[session_state, doc_selector], outputs=lib_sync)
    refresh_btn.click(fn=refresh_library,      inputs=[session_state],               outputs=lib_sync)


if __name__ == "__main__":
    demo.queue()
    demo.launch(inbrowser=True, theme=gr.themes.Soft(), css=_COMBINED_CSS, js=_SPLASH_JS)
