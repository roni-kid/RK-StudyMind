import gradio as gr
import sys
import os
import tempfile

sys.path.append(os.path.dirname(__file__))
from modules.pdf_reader import read_file, get_page_count, get_page_label, chunk_text
from modules.ai_engine import ask_lmstudio, check_lmstudio_connection
from modules.vector_store import index_chunks, search_similar_chunks
from modules.flashcards import generate_flashcards
from modules.mindmap import generate_mindmap_markdown, mindmap_to_html
from modules.quiz import generate_quiz
from modules.doc_library import (
    library, active_doc,
    add_document, set_active, remove_document,
    get_active_text, get_active_chunks, get_active_filename,
    get_all_filenames, get_doc_info, render_library_html
)

# =============================================
# 🧠 RK StudyMind v1.0
# Built by: RoniKid
# =============================================

chat_log = []
current_flashcards = []
current_quiz = []

# -----------------------------------------------
# HELPERS
# -----------------------------------------------
def get_doc_status():
    fn = get_active_filename()
    if not fn:
        return "❌ No document loaded — upload a PDF or DOCX first"
    info = get_doc_info(fn)
    return f"✅ Active: {fn} ({info.get('pages','?')} pages) — {len(library)} doc(s) in library"

def get_filenames_for_dropdown():
    fns = get_all_filenames()
    return gr.update(choices=fns, value=fns[0] if fns else None)

def get_checkbox_update():
    """Returns updated CheckboxGroup choices for doc selector."""
    fns = get_all_filenames()
    return gr.update(choices=fns, value=fns)  # default: all selected

def get_text_from_selection(selected_docs: list) -> str:
    """Combines text from selected documents."""
    if not selected_docs:
        return ""
    parts = []
    for fn in selected_docs:
        if fn in library:
            parts.append(f"[From: {fn}]\n{library[fn]['text']}")
    return "\n\n---\n\n".join(parts)

def get_combined_text():
    return "\n\n---\n\n".join(
        f"[From: {fn}]\n{info['text']}" for fn, info in library.items()
    )

# -----------------------------------------------
# TAB 1: Home
# -----------------------------------------------
def greet(name):
    if not name.strip():
        return "⚠️ Please enter your name!"
    status = check_lmstudio_connection()
    return f"👋 Welcome to RK StudyMind, {name}!\n\n📚 Your personal AI-powered study companion is ready.\n\n🤖 AI Status: {status}"

def check_status():
    return check_lmstudio_connection()

# -----------------------------------------------
# TAB 2: Library
# -----------------------------------------------
def load_files(files):
    if files is None:
        return "⚠️ No files uploaded.", "", render_library_html(), get_doc_status(), get_filenames_for_dropdown(), get_checkbox_update(), get_checkbox_update(), get_checkbox_update()

    if not isinstance(files, list):
        files = [files]

    results = []
    for file in files:
        file_path = file.name
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            results.append(f"❌ Skipped '{filename}': unsupported type ({ext})")
            continue
        page_count = get_page_count(file_path)
        raw_text = read_file(file_path)
        chunks = chunk_text(raw_text)
        add_document(filename, raw_text, chunks, page_count)
        index_chunks(chunks, filename)
        file_icon = "📄" if ext == ".pdf" else "📝"
        results.append(f"{file_icon} '{filename}' — {page_count} {get_page_label(file_path)}, {len(raw_text.split())} words, {len(chunks)} chunks")

    info = f"✅ {len(results)} file(s) processed:\n\n" + "\n".join(results)
    info += f"\n\n📚 Total docs in library: {len(library)}"
    preview = ""
    if get_active_filename():
        text = get_active_text()
        preview = text[:2000] + "\n\n... [truncated]" if len(text) > 2000 else text

    return (info, preview, render_library_html(), get_doc_status(),
            get_filenames_for_dropdown(), get_checkbox_update(), get_checkbox_update(), get_checkbox_update())  # fc, quiz, mm selectors

def switch_active_doc(filename):
    if not filename:
        return render_library_html(), get_doc_status()
    set_active(filename)
    return render_library_html(), get_doc_status()

def delete_doc(filename):
    fns = get_all_filenames()
    if not filename:
        return (render_library_html(), get_doc_status(),
                gr.update(choices=fns, value=fns[0] if fns else None),
                gr.update(choices=fns, value=None),
                get_checkbox_update(), get_checkbox_update(), get_checkbox_update())
    remove_document(filename)
    fns = get_all_filenames()  # refresh after removal
    new_val = fns[0] if fns else None
    return (render_library_html(), get_doc_status(),
            gr.update(choices=fns, value=new_val),   # switch_dropdown
            gr.update(choices=fns, value=None),       # delete_dropdown — cleared
            get_checkbox_update(), get_checkbox_update(), get_checkbox_update())  # fc, quiz, mm

def refresh_library():
    return (render_library_html(), get_doc_status(), get_filenames_for_dropdown(),
            get_checkbox_update(), get_checkbox_update(), get_checkbox_update())  # fc, quiz, mm

# -----------------------------------------------
# TAB 3: Q&A
# -----------------------------------------------
def format_chat():
    if not chat_log:
        return ""
    display = ""
    for speaker, msg in chat_log:
        if speaker == "You":
            display += f"🧑 You:\n{msg}\n\n"
        else:
            display += f"🤖 RK StudyMind:\n{msg}\n\n{'─' * 60}\n\n"
    return display.strip()

def answer_question(question, history_display, search_mode):
    global chat_log
    if not question.strip():
        return history_display, "", get_doc_status()
    if not get_active_filename():
        chat_log.append(("You", question))
        chat_log.append(("RK StudyMind", "⚠️ No document loaded. Please upload a PDF or DOCX first."))
        return format_chat(), "", get_doc_status()
    if search_mode == "🔍 Active Document Only":
        relevant_chunks = search_similar_chunks(question=question, filename=get_active_filename(), top_k=3)
        context = "\n\n---\n\n".join(relevant_chunks) if relevant_chunks else get_active_text()[:4000]
        source_note = f"[Source: {get_active_filename()}]"
    else:
        all_chunks = []
        for fname in get_all_filenames():
            chunks = search_similar_chunks(question=question, filename=fname, top_k=2)
            for chunk in chunks:
                all_chunks.append(f"[From: {fname}]\n{chunk}")
        context = "\n\n---\n\n".join(all_chunks) if all_chunks else get_active_text()[:4000]
        source_note = f"[Searched {len(library)} documents]"
    answer = ask_lmstudio(prompt=question, context=context)
    chat_log.append(("You", question))
    chat_log.append(("RK StudyMind", f"{answer}\n\n_{source_note}_"))
    return format_chat(), "", get_doc_status()

def clear_chat():
    global chat_log
    chat_log = []
    return "", "", get_doc_status()

# -----------------------------------------------
# TAB 4: Smart Quiz
# -----------------------------------------------
def render_quiz_question(q, index, total, selected=None, revealed=False):
    color_map = {"A": "#4F46E5", "B": "#0891B2", "C": "#059669", "D": "#D97706"}
    options_html = ""
    for letter, text in q["options"].items():
        if revealed:
            if letter == q["answer"]:
                bg = "#10b981"; border = "2px solid #10b981"; text_col = "#fff"; icon = "✅ "
            elif letter == selected:
                bg = "#ef4444"; border = "2px solid #ef4444"; text_col = "#fff"; icon = "❌ "
            else:
                bg = "#1e293b"; border = "1px solid #334155"; text_col = "#94a3b8"; icon = ""
        else:
            if letter == selected:
                bg = color_map[letter]; border = f"2px solid {color_map[letter]}"; text_col = "#fff"; icon = "▶ "
            else:
                bg = "#1e293b"; border = "1px solid #334155"; text_col = "#e2e8f0"; icon = ""
        options_html += f"""<div style="background:{bg};border:{border};border-radius:10px;padding:12px 18px;
            margin-bottom:8px;color:{text_col};font-family:'Segoe UI',sans-serif;font-size:15px;font-weight:500;">
            <strong>{icon}{letter}.</strong> {text}</div>"""
    explanation = ""
    if revealed:
        explanation = f"""<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;
            padding:14px 18px;margin-top:12px;color:#94a3b8;font-size:13px;font-family:'Segoe UI',sans-serif;">
            💡 <strong style="color:#e2e8f0;">Explanation:</strong> {q.get('explanation', 'Correct answer: ' + q['answer'])}</div>"""
    return f"""<div style="display:flex;justify-content:center;padding:10px;">
      <div style="background:#1e293b;border:2px solid #334155;border-radius:20px;width:100%;max-width:720px;
                  padding:30px 40px;box-shadow:0 8px 30px rgba(0,0,0,0.25);font-family:'Segoe UI',sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
          <span style="background:#4F46E5;color:#fff;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:700;">
            Question {index+1} of {total}</span>
          {'<span style="color:#10b981;font-weight:700;font-size:13px;">✅ Revealed</span>' if revealed else ''}
        </div>
        <div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:20px;line-height:1.5;">{q['question']}</div>
        {options_html}{explanation}
      </div></div>"""

def render_quiz_empty():
    return """<div style="display:flex;justify-content:center;padding:20px;"><div style="background:#1e293b;
        border:2px dashed #475569;border-radius:20px;width:100%;max-width:720px;min-height:200px;
        display:flex;align-items:center;justify-content:center;color:#94a3b8;
        font-size:18px;font-family:'Segoe UI',sans-serif;">Generate a quiz to start 📝</div></div>"""

def render_quiz_results(score, total):
    pct = int((score / total) * 100) if total > 0 else 0
    if pct >= 80: emoji, msg, color = "🏆", "Excellent!", "#10b981"
    elif pct >= 60: emoji, msg, color = "👍", "Good job!", "#f59e0b"
    elif pct >= 40: emoji, msg, color = "📚", "Keep studying!", "#f97316"
    else: emoji, msg, color = "💪", "Review and retry!", "#ef4444"
    return f"""<div style="display:flex;justify-content:center;padding:10px;">
      <div style="background:#1e293b;border:2px solid {color};border-radius:20px;width:100%;max-width:720px;
                  min-height:200px;padding:40px;box-shadow:0 8px 30px rgba(0,0,0,0.25);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',sans-serif;text-align:center;gap:12px;">
        <div style="font-size:48px;">{emoji}</div>
        <div style="font-size:24px;font-weight:800;color:#f1f5f9;">Quiz Complete!</div>
        <div style="font-size:15px;color:{color};font-weight:600;">{msg}</div>
        <div style="display:flex;gap:32px;margin-top:8px;">
          <div style="text-align:center;"><div style="font-size:34px;font-weight:800;color:#10b981;">{score}</div><div style="font-size:13px;color:#94a3b8;">Correct</div></div>
          <div style="text-align:center;"><div style="font-size:34px;font-weight:800;color:#ef4444;">{total-score}</div><div style="font-size:13px;color:#94a3b8;">Wrong</div></div>
          <div style="text-align:center;"><div style="font-size:34px;font-weight:800;color:{color};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score</div></div>
        </div>
      </div></div>"""

def quiz_question_mode():
    return (
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
    )

def quiz_answer_mode():
    return (
        gr.update(interactive=True,  variant="secondary"),
        gr.update(interactive=True,  variant="secondary"),
        gr.update(interactive=True,  variant="secondary"),
        gr.update(interactive=True,  variant="secondary"),
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
    )

def quiz_revealed_mode():
    return (
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=True,  variant="primary"),
        gr.update(interactive=False, variant="secondary"),
    )

def quiz_done_mode():
    return (
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=False, variant="secondary"),
        gr.update(interactive=True,  variant="primary"),
    )

def start_quiz(num_q, selected_docs):
    global current_quiz
    if not selected_docs:
        return ("⚠️ No documents selected. Tick at least one document.", render_quiz_empty(),
                0, None, False, 0, *quiz_question_mode())
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        return ("⚠️ Selected documents have no text.", render_quiz_empty(),
                0, None, False, 0, *quiz_question_mode())
    questions = generate_quiz(text=text, num_questions=int(num_q))
    if not questions:
        return ("⚠️ Could not generate quiz. Try a different document or model.", render_quiz_empty(),
                0, None, False, 0, *quiz_question_mode())
    current_quiz = questions
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else selected_docs[0]
    return (f"✅ {len(questions)} questions from: {source}",
            render_quiz_question(questions[0], 0, len(questions)),
            0, None, False, 0, *quiz_question_mode())

def quiz_select_answer(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), q_index, selected_letter, revealed, score, *quiz_question_mode()
    idx = int(q_index)
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz), selected_letter, revealed),
            idx, selected_letter, revealed, score, *quiz_answer_mode())

def quiz_submit(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz or selected_letter is None:
        return render_quiz_empty(), q_index, selected_letter, True, score, *quiz_answer_mode()
    idx = int(q_index)
    q = current_quiz[idx]
    new_score = score + (1 if selected_letter == q["answer"] else 0)
    return (render_quiz_question(q, idx, len(current_quiz), selected_letter, True),
            idx, selected_letter, True, new_score, *quiz_revealed_mode())

def quiz_next(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), 0, None, False, score, *quiz_question_mode()
    idx = int(q_index) + 1
    if idx >= len(current_quiz):
        return (render_quiz_results(score, len(current_quiz)),
                idx - 1, None, False, score, *quiz_done_mode())
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz)),
            idx, None, False, score, *quiz_question_mode())

def quiz_restart():
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), 0, None, False, 0, *quiz_question_mode()
    return (render_quiz_question(current_quiz[0], 0, len(current_quiz)),
            0, None, False, 0, *quiz_question_mode())

# -----------------------------------------------
# TAB 5: Flashcards (with doc selector, up to 40)
# -----------------------------------------------
CARD_COLORS = ["#4F46E5", "#0891B2", "#059669", "#D97706", "#DC2626", "#7C3AED"]

def question_mode():
    return (gr.update(interactive=True, variant="secondary"),
            gr.update(interactive=True, variant="primary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"))

def answer_mode():
    return (gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=True, variant="primary"),
            gr.update(interactive=True, variant="secondary"),
            gr.update(interactive=False, variant="secondary"))

def done_mode():
    return (gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=False, variant="secondary"),
            gr.update(interactive=True, variant="primary"))

def render_score_bar(correct, wrong, total):
    answered = correct + wrong
    if answered == 0: return ""
    pct = int((correct / answered) * 100)
    bar_fill = int((correct / total) * 100)
    return f"""<div style="max-width:680px;margin:0 auto 10px auto;font-family:'Segoe UI',sans-serif;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="color:#94a3b8;font-size:13px;">Score: {answered}/{total} answered</span>
            <span style="font-size:14px;font-weight:700;color:#10b981;">✅ {correct} &nbsp; ❌ {wrong} &nbsp; {pct}%</span>
        </div>
        <div style="background:#1e293b;border-radius:10px;height:8px;overflow:hidden;">
            <div style="background:#10b981;width:{bar_fill}%;height:100%;border-radius:10px;"></div>
        </div></div>"""

def render_results_html(correct, wrong, total):
    pct = int((correct / total) * 100) if total > 0 else 0
    if pct >= 80: emoji, msg, color = "🏆", "Excellent work!", "#10b981"
    elif pct >= 60: emoji, msg, color = "👍", "Good job!", "#f59e0b"
    elif pct >= 40: emoji, msg, color = "📚", "Keep practising!", "#f97316"
    else: emoji, msg, color = "💪", "Don't give up!", "#ef4444"
    return f"""<div style="display:flex;justify-content:center;padding:10px;">
      <div style="background:#1e293b;border:2px solid {color};border-radius:20px;width:100%;max-width:680px;
                  min-height:280px;padding:40px 50px;box-shadow:0 8px 30px rgba(0,0,0,0.25);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',sans-serif;text-align:center;gap:16px;">
        <div style="font-size:52px;">{emoji}</div>
        <div style="font-size:26px;font-weight:800;color:#f1f5f9;">Session Complete!</div>
        <div style="font-size:16px;color:{color};font-weight:600;">{msg}</div>
        <div style="display:flex;gap:32px;margin-top:8px;">
          <div style="text-align:center;"><div style="font-size:36px;font-weight:800;color:#10b981;">{correct}</div><div style="font-size:13px;color:#94a3b8;">Correct ✅</div></div>
          <div style="text-align:center;"><div style="font-size:36px;font-weight:800;color:#ef4444;">{wrong}</div><div style="font-size:13px;color:#94a3b8;">Wrong ❌</div></div>
          <div style="text-align:center;"><div style="font-size:36px;font-weight:800;color:{color};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score 📊</div></div>
        </div>
        <div style="font-size:13px;color:#475569;margin-top:8px;">Click <strong style="color:#f1f5f9;">🔁 Study Again</strong> to restart</div>
      </div></div>"""

def render_card_html(card, index, total, revealed, correct=0, wrong=0):
    color = CARD_COLORS[index % len(CARD_COLORS)]
    score_bar = render_score_bar(correct, wrong, total)
    if not revealed:
        side_label, content = "QUESTION", card["question"]
        text_color, bg_color, border_style = "#ffffff", color, "border:none;"
        hint = "<div style='margin-top:24px;text-align:center;font-size:12px;color:rgba(255,255,255,0.4);'>Think of the answer, then click 🔄 Reveal Answer</div>"
    else:
        side_label, content = "ANSWER", card["answer"]
        text_color, bg_color = "#1e293b", "#f8fafc"
        border_style = f"border:4px solid {color};"
        hint = "<div style='margin-top:24px;text-align:center;font-size:12px;color:rgba(0,0,0,0.35);'>Did you remember it? Click ✅ or ❌ below</div>"
    return f"""{score_bar}<div style="display:flex;justify-content:center;padding:10px;">
      <div style="background:{bg_color};{border_style}border-radius:20px;width:100%;max-width:680px;min-height:280px;
                  padding:40px 50px;box-shadow:0 8px 30px rgba(0,0,0,0.25);display:flex;flex-direction:column;
                  position:relative;font-family:'Segoe UI',sans-serif;">
        <div style="position:absolute;top:16px;right:24px;background:rgba({'0,0,0' if revealed else '255,255,255'},0.1);
                    color:{'#64748b' if revealed else '#fff'};border-radius:20px;padding:4px 14px;font-size:13px;font-weight:600;">
          {index+1} / {total}</div>
        <div style="font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;
                    color:{'rgba(0,0,0,0.3)' if revealed else 'rgba(255,255,255,0.55)'};">{side_label}</div>
        <div style="font-size:20px;font-weight:600;color:{text_color};line-height:1.6;flex-grow:1;display:flex;align-items:center;">{content}</div>
        {hint}</div></div>"""

def render_empty_card():
    return """<div style="display:flex;justify-content:center;padding:20px;"><div style="background:#1e293b;border:2px dashed #475569;border-radius:20px;width:100%;max-width:680px;min-height:280px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:18px;font-family:'Segoe UI',sans-serif;">Generate flashcards to start studying 🃏</div></div>"""

def make_flashcards(num_cards, selected_docs):
    global current_flashcards
    if not selected_docs:
        return ("⚠️ No documents selected. Tick at least one document.", render_empty_card(),
                0, False, 0, 0, *question_mode())
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        return ("⚠️ Selected documents have no text.", render_empty_card(),
                0, False, 0, 0, *question_mode())
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else selected_docs[0]
    cards = generate_flashcards(text=text, filename=source, num_cards=int(num_cards))
    current_flashcards = cards
    return (f"✅ {len(cards)} flashcards from: {source}",
            render_card_html(cards[0], 0, len(cards), False, 0, 0),
            0, False, 0, 0, *question_mode())

def reveal_answer(card_index, show_answer, correct, wrong):
    global current_flashcards
    if not current_flashcards: return render_empty_card(), card_index, True, correct, wrong, *answer_mode()
    idx = int(card_index)
    return (render_card_html(current_flashcards[idx], idx, len(current_flashcards), True, correct, wrong),
            idx, True, correct, wrong, *answer_mode())

def score_correct(card_index, correct, wrong):
    global current_flashcards
    correct += 1
    total = len(current_flashcards)
    if int(card_index) >= total - 1:
        return (render_results_html(correct, wrong, total), int(card_index), False, correct, wrong, *done_mode())
    idx = int(card_index) + 1
    return (render_card_html(current_flashcards[idx], idx, total, False, correct, wrong),
            idx, False, correct, wrong, *question_mode())

def score_wrong(card_index, correct, wrong):
    global current_flashcards
    wrong += 1
    total = len(current_flashcards)
    if int(card_index) >= total - 1:
        return (render_results_html(correct, wrong, total), int(card_index), False, correct, wrong, *done_mode())
    idx = int(card_index) + 1
    return (render_card_html(current_flashcards[idx], idx, total, False, correct, wrong),
            idx, False, correct, wrong, *question_mode())

def prev_card(card_index, correct, wrong):
    global current_flashcards
    if not current_flashcards: return render_empty_card(), 0, False, correct, wrong, *question_mode()
    idx = (int(card_index) - 1) % len(current_flashcards)
    return (render_card_html(current_flashcards[idx], idx, len(current_flashcards), False, correct, wrong),
            idx, False, correct, wrong, *question_mode())

def study_again():
    global current_flashcards
    if not current_flashcards: return render_empty_card(), 0, False, 0, 0, *question_mode()
    return (render_card_html(current_flashcards[0], 0, len(current_flashcards), False, 0, 0),
            0, False, 0, 0, *question_mode())

# -----------------------------------------------
# Mindmap helpers
# -----------------------------------------------
def make_mindmap_full(topic, selected_docs):
    if not selected_docs:
        return "⚠️ No documents selected. Tick at least one document.", None, ""
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        return "⚠️ Selected documents have no text.", None, ""
    if len(selected_docs) > 1:
        title = f"All Selected ({len(selected_docs)} docs)"
    else:
        title = topic.strip() if topic.strip() else selected_docs[0].rsplit(".", 1)[0]
    md = generate_mindmap_markdown(text=text, topic=topic)
    html = mindmap_to_html(md, title=title)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", prefix="rk_mindmap_",
        dir=os.path.join(os.path.dirname(__file__), "data"))
    tmp.write(html.encode("utf-8"))
    tmp.close()
    return "✅ Mindmap ready! Click 'Open Mindmap in Browser'.", tmp.name, md

def open_in_browser(file_path):
    if not file_path or not os.path.exists(file_path):
        return gr.update(value="⚠️ Generate a mindmap first.", visible=True)
    import webbrowser
    webbrowser.open(f"file:///{file_path}")
    return gr.update(value="✅ Opened in browser!", visible=True)

# -----------------------------------------------
# UI Layout
# -----------------------------------------------
css = """
    .gradio-container { max-width:100% !important; width:100% !important; margin:0 !important; padding:20px !important; }
    footer { display:none !important; }
"""

with gr.Blocks(title="🧠 RK StudyMind") as demo:
    gr.Markdown("# 🧠 RK StudyMind")
    gr.Markdown("### Your Personal AI Study Companion")

    with gr.Tabs():

        # ---- TAB 1: Home ----
        with gr.Tab("🏠 Home"):
            with gr.Row():
                name_input = gr.Textbox(label="Your name", placeholder="e.g. RoniKid", lines=1)
                output = gr.Textbox(label="Status", interactive=False, lines=6)
            start_btn = gr.Button("Launch RK StudyMind 🚀", variant="primary", size="lg")
            start_btn.click(fn=greet, inputs=name_input, outputs=output)
            gr.Markdown("---")
            status_output = gr.Textbox(label="LM Studio Connection", interactive=False, lines=2)
            check_btn = gr.Button("Check LM Studio 🔌", variant="secondary")
            check_btn.click(fn=check_status, inputs=[], outputs=status_output)

        # ---- TAB 2: Library ----
        with gr.Tab("📚 Library"):
            gr.Markdown("### Document Library")
            gr.Markdown("_Upload PDFs or DOCX. Select multiple with Ctrl+Click. Manage docs below._")
            with gr.Row():
                file_input = gr.File(label="Upload PDF or DOCX", file_types=[".pdf", ".docx"], file_count="multiple")
                upload_btn = gr.Button("Add to Library 📚", variant="primary", scale=0)
            with gr.Row():
                info_output   = gr.Textbox(label="Upload Info", lines=6, interactive=False)
                preview_output = gr.Textbox(label="Active Doc Preview", lines=6, interactive=False)
            gr.Markdown("---")
            gr.Markdown("#### 📋 Current Library")
            library_html  = gr.HTML(value=render_library_html())
            lib_doc_status = gr.Textbox(label="Active Document", interactive=False, lines=1, value=get_doc_status())
            gr.Markdown("#### Switch Active Document")
            with gr.Row():
                switch_dropdown = gr.Dropdown(label="Select to activate", choices=get_all_filenames(), interactive=True, scale=3)
                switch_btn = gr.Button("✅ Set as Active", variant="primary", scale=1)
            gr.Markdown("#### Remove a Document")
            with gr.Row():
                delete_dropdown = gr.Dropdown(label="Select to remove", choices=get_all_filenames(), interactive=True, scale=3)
                delete_btn = gr.Button("🗑️ Remove", variant="secondary", scale=1)
            refresh_btn = gr.Button("🔄 Refresh", variant="secondary")

            # Note: upload/delete/refresh click handlers are wired after all tabs
            # so they can reference selectors defined in later tabs.
            switch_btn.click(fn=switch_active_doc, inputs=[switch_dropdown], outputs=[library_html, lib_doc_status])

        # ---- TAB 3: Q&A ----
        with gr.Tab("💬 Q&A"):
            gr.Markdown("### Chat with your Documents")
            qa_doc_status = gr.Textbox(label="📁 Active Document", value=get_doc_status(), interactive=False, lines=1)
            search_mode = gr.Radio(choices=["🔍 Active Document Only", "🌐 All Documents"],
                                   value="🔍 Active Document Only", label="Search Scope")
            chat_display = gr.Textbox(label="💬 Conversation", lines=14, interactive=False,
                                      placeholder="Your conversation will appear here...")
            with gr.Row():
                question_input = gr.Textbox(label="Ask a question", placeholder="e.g. Summarize this document", lines=2, scale=4)
                ask_btn = gr.Button("Ask 🔍", variant="primary", scale=1)
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
            ask_btn.click(fn=answer_question, inputs=[question_input, chat_display, search_mode],
                outputs=[chat_display, question_input, qa_doc_status])
            question_input.submit(fn=answer_question, inputs=[question_input, chat_display, search_mode],
                outputs=[chat_display, question_input, qa_doc_status])
            clear_btn.click(fn=clear_chat, inputs=[], outputs=[chat_display, question_input, qa_doc_status])

        # ---- TAB 4: Quiz ----
        with gr.Tab("📝 Quiz"):
            gr.Markdown("### Smart Quiz — Multiple Choice")
            gr.Markdown("_Select documents, set number of questions, then generate_")
            quiz_doc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Quiz",
                choices=get_all_filenames(),
                value=get_all_filenames(),
                interactive=True
            )
            with gr.Row():
                num_q_slider   = gr.Slider(minimum=3, maximum=10, value=5, step=1, label="Number of questions")
                start_quiz_btn = gr.Button("Generate Quiz 📝", variant="primary")
            quiz_status = gr.Textbox(label="Status", interactive=False, lines=1)
            gr.Markdown("---")
            quiz_html      = gr.HTML(value=render_quiz_empty())
            q_index_state  = gr.State(value=0)
            selected_state = gr.State(value=None)
            revealed_state = gr.State(value=False)
            score_state    = gr.State(value=0)
            with gr.Row():
                btn_a = gr.Button("A", variant="primary", scale=1)
                btn_b = gr.Button("B", variant="primary", scale=1)
                btn_c = gr.Button("C", variant="primary", scale=1)
                btn_d = gr.Button("D", variant="primary", scale=1)
            with gr.Row():
                submit_btn  = gr.Button("✅ Submit Answer", variant="secondary", interactive=False, scale=2)
                next_btn    = gr.Button("➡️ Next Question", variant="secondary", interactive=False, scale=2)
                restart_btn = gr.Button("🔁 Restart Quiz",  variant="secondary", interactive=False, scale=1)
            quiz_btn_outputs = [btn_a, btn_b, btn_c, btn_d, submit_btn, next_btn, restart_btn]
            quiz_outputs = [quiz_html, q_index_state, selected_state, revealed_state, score_state] + quiz_btn_outputs

            start_quiz_btn.click(fn=start_quiz, inputs=[num_q_slider, quiz_doc_selector],
                outputs=[quiz_status, quiz_html, q_index_state, selected_state,
                         revealed_state, score_state] + quiz_btn_outputs)
            btn_a.click(fn=lambda qi, sl, rv, sc: quiz_select_answer(qi, "A", rv, sc),
                inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            btn_b.click(fn=lambda qi, sl, rv, sc: quiz_select_answer(qi, "B", rv, sc),
                inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            btn_c.click(fn=lambda qi, sl, rv, sc: quiz_select_answer(qi, "C", rv, sc),
                inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            btn_d.click(fn=lambda qi, sl, rv, sc: quiz_select_answer(qi, "D", rv, sc),
                inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            submit_btn.click(fn=quiz_submit, inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            next_btn.click(fn=quiz_next, inputs=[q_index_state, selected_state, revealed_state, score_state], outputs=quiz_outputs)
            restart_btn.click(fn=quiz_restart, inputs=[], outputs=quiz_outputs)

        # ---- TAB 5: Flashcards ----
        with gr.Tab("🃏 Flashcards"):
            gr.Markdown("### Study Flashcards — One Card at a Time")
            gr.Markdown("_Select documents, set number of cards, then generate_")
            fc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Flashcards",
                choices=get_all_filenames(),
                value=get_all_filenames(),
                interactive=True
            )
            with gr.Row():
                num_cards_slider = gr.Slider(minimum=5, maximum=40, value=10, step=5, label="Number of flashcards")
                generate_btn = gr.Button("Generate Flashcards 🃏", variant="primary", scale=0)
            fc_status = gr.Textbox(label="Status", interactive=False, lines=1)
            gr.Markdown("---")
            card_html_display = gr.HTML(value=render_empty_card())
            card_index_state  = gr.State(value=0)
            show_answer_state = gr.State(value=False)
            correct_state     = gr.State(value=0)
            wrong_state       = gr.State(value=0)
            with gr.Row():
                prev_btn        = gr.Button("⬅️ Previous",        variant="secondary", interactive=True,  scale=1)
                reveal_btn      = gr.Button("🔄 Reveal Answer",    variant="primary",   interactive=True,  scale=2)
                correct_btn     = gr.Button("✅  Got It!",          variant="secondary", interactive=False, scale=1)
                wrong_btn       = gr.Button("❌  Didn't Remember", variant="secondary", interactive=False, scale=1)
                study_again_btn = gr.Button("🔁 Study Again",      variant="secondary", interactive=False, scale=1)
            card_outputs = [card_html_display, card_index_state, show_answer_state,
                            correct_state, wrong_state, prev_btn, reveal_btn, correct_btn, wrong_btn, study_again_btn]
            generate_btn.click(fn=make_flashcards, inputs=[num_cards_slider, fc_selector],
                outputs=[fc_status, card_html_display, card_index_state, show_answer_state,
                         correct_state, wrong_state, prev_btn, reveal_btn, correct_btn, wrong_btn, study_again_btn])
            reveal_btn.click(fn=reveal_answer, inputs=[card_index_state, show_answer_state, correct_state, wrong_state], outputs=card_outputs)
            correct_btn.click(fn=score_correct, inputs=[card_index_state, correct_state, wrong_state], outputs=card_outputs)
            wrong_btn.click(fn=score_wrong, inputs=[card_index_state, correct_state, wrong_state], outputs=card_outputs)
            prev_btn.click(fn=prev_card, inputs=[card_index_state, correct_state, wrong_state], outputs=card_outputs)
            study_again_btn.click(fn=study_again, inputs=[], outputs=card_outputs)

        # ---- TAB 7: Mindmap ----
        with gr.Tab("🗺️ Mindmap"):
            gr.Markdown("### Generate an Interactive Mindmap")
            gr.Markdown("_Select documents, add an optional topic, then generate_")
            mm_doc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Mindmap",
                choices=get_all_filenames(),
                value=get_all_filenames(),
                interactive=True
            )
            with gr.Row():
                topic_input = gr.Textbox(label="Topic (optional)", placeholder="Leave blank to auto-detect", lines=1, scale=3)
                mm_generate_btn = gr.Button("Generate Mindmap 🗺️", variant="primary", scale=0)
            mm_status = gr.Textbox(label="Status", interactive=False, lines=1)
            mm_file_path = gr.State(value=None)
            mm_open_btn = gr.Button("🌐 Open Mindmap in Browser", variant="secondary", size="lg")
            mm_open_status = gr.Textbox(label="", interactive=False, lines=1, visible=False)
            gr.Markdown("---")
            mm_markdown_display = gr.Textbox(label="Mindmap Outline", lines=15, interactive=False,
                                             placeholder="Mindmap outline will appear here...")
            mm_generate_btn.click(fn=make_mindmap_full, inputs=[topic_input, mm_doc_selector],
                outputs=[mm_status, mm_file_path, mm_markdown_display])
            mm_open_btn.click(fn=open_in_browser, inputs=[mm_file_path], outputs=[mm_open_status])

    # -----------------------------------------------
    # Wire library buttons to keep all tab selectors in sync
    # (must be after all tabs so components are defined)
    # -----------------------------------------------
    upload_btn.click(fn=load_files, inputs=[file_input],
        outputs=[info_output, preview_output, library_html, lib_doc_status,
                 switch_dropdown, fc_selector, quiz_doc_selector, mm_doc_selector])
    delete_btn.click(fn=delete_doc, inputs=[delete_dropdown],
        outputs=[library_html, lib_doc_status, switch_dropdown, delete_dropdown,
                 fc_selector, quiz_doc_selector, mm_doc_selector])
    refresh_btn.click(fn=refresh_library, inputs=[],
        outputs=[library_html, lib_doc_status, switch_dropdown, fc_selector, quiz_doc_selector, mm_doc_selector])

if __name__ == "__main__":
    demo.launch(
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=css
    )
