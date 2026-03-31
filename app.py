import gradio as gr
import sys
import os
import random
import html as _html

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
# 🧠 RK StudyMind v1.1 — Built by RoniKid
# =============================================

chat_log = []
current_flashcards = []
current_quiz = []

STUDY_TIPS = [
    "💡 Tip: Upload multiple PDFs at once by holding Ctrl while selecting files.",
    "💡 Tip: Use the Q&A tab to quiz yourself before generating a formal quiz.",
    "💡 Tip: Flashcards work best in short 10-minute sessions — take a break after each round.",
    "💡 Tip: Generate a Mindmap first to understand a topic, then dive into Q&A for details.",
    "💡 Tip: Mix documents in Flashcards and Quiz mode to test cross-topic knowledge.",
    "💡 Tip: If quiz quality is low, try a document with more detailed text content.",
]

# Tab indices (0-based):
# 0=Home, 1=Library, 2=Q&A, 3=Quiz, 4=Flashcards, 5=Mindmap

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
    fns = get_all_filenames()
    return gr.update(choices=fns, value=fns)

def get_radio_update():
    """Radio always pre-selects the current active doc so the user doesn't need to re-click."""
    fns = get_all_filenames()
    active = get_active_filename()
    selected = active if active in fns else (fns[0] if fns else None)
    return gr.update(choices=fns, value=selected)

def sanitize_docs(selected_docs) -> list:
    """Coerces any stale browser value into a clean list of docs that exist in the library."""
    if not selected_docs:
        return []
    if isinstance(selected_docs, str):
        selected_docs = [selected_docs]
    return [d for d in selected_docs if d in library]

def get_text_from_selection(selected_docs: list) -> str:
    if not selected_docs:
        return ""
    parts = []
    for fn in selected_docs:
        if fn in library:
            parts.append(f"[From: {fn}]\n{library[fn]['text']}")
    return "\n\n---\n\n".join(parts)

# -----------------------------------------------
# TAB 1: Home
# -----------------------------------------------
def render_home_stats(ai_status: str = "") -> str:
    doc_count   = len(library)
    word_count  = sum(info.get("words", 0) for info in library.values())
    chunk_count = sum(len(info.get("chunks", [])) for info in library.values())
    tip = random.choice(STUDY_TIPS)

    if not ai_status:
        ai_color, ai_icon, ai_label = "#475569", "⚙️", "Not checked"
    elif "✅" in ai_status:
        ai_color, ai_icon, ai_label = "#10b981", "✅", "Connected"
    else:
        ai_color, ai_icon, ai_label = "#ef4444", "❌", "Offline"

    def stat_card(icon, value, label, color):
        return f"""<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;
            padding:20px 24px;flex:1;min-width:140px;text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">{icon}</div>
          <div style="font-size:26px;font-weight:800;color:{color};">{value}</div>
          <div style="font-size:12px;color:#64748b;margin-top:4px;">{label}</div>
        </div>"""

    def feature_card(icon, title, desc):
        return f"""<div style="background:#1e293b;border:1px solid #334155;border-radius:16px;
                 padding:20px 16px;flex:1;min-width:140px;text-align:center;">
          <div style="font-size:28px;margin-bottom:8px;">{icon}</div>
          <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:6px;">{title}</div>
          <div style="font-size:11px;color:#64748b;line-height:1.5;">{desc}</div>
        </div>"""

    return f"""
<style>
@keyframes gradientShimmer {{
  0%   {{ background-position: 0% 50%; }}
  50%  {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}
@keyframes glossMove {{
  0%   {{ left: -60%; opacity: 0; }}
  15%  {{ opacity: 1; }}
  85%  {{ opacity: 1; }}
  100% {{ left: 130%; opacity: 0; }}
}}
@keyframes pulseBadge {{
  0%, 100% {{ box-shadow: 0 0 0 0 rgba(79,70,229,0.5); }}
  50%       {{ box-shadow: 0 0 0 8px rgba(79,70,229,0); }}
}}
</style>

<div style="font-family:'Segoe UI',sans-serif;max-width:960px;margin:0 auto;padding:8px 0;">

  <!-- Hero -->
  <div style="position:relative;overflow:hidden;border-radius:22px;margin-bottom:24px;
              background:linear-gradient(135deg,#1e1b4b,#312e81,#1e1b4b,#0f172a,#1e293b,#4F46E5,#1e1b4b);
              background-size:400% 400%;animation:gradientShimmer 7s ease infinite;
              padding:48px 40px;text-align:center;border:1px solid #3730a3;">
    <div style="position:absolute;top:0;left:-60%;width:40%;height:100%;
                background:linear-gradient(90deg,transparent,rgba(255,255,255,0.08),transparent);
                transform:skewX(-15deg);animation:glossMove 4s ease-in-out infinite;pointer-events:none;"></div>
    <div style="font-size:54px;margin-bottom:12px;position:relative;">🧠</div>
    <div style="font-size:38px;font-weight:800;color:#f1f5f9;letter-spacing:-0.5px;position:relative;">RK StudyMind</div>
    <div style="font-size:15px;color:#a5b4fc;margin-top:8px;position:relative;">Your personal AI-powered study companion</div>
    <div style="display:inline-block;background:#4F46E5;color:#fff;border-radius:20px;
                padding:4px 18px;font-size:12px;font-weight:700;margin-top:16px;
                letter-spacing:1px;position:relative;animation:pulseBadge 2s ease infinite;">v1.1</div>
  </div>

  <!-- Stats -->
  <div style="font-size:11px;font-weight:700;color:#475569;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Library Stats</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px;">
    {stat_card("📚", doc_count,         "Documents",     "#818cf8")}
    {stat_card("📝", f"{word_count:,}", "Words Indexed", "#34d399")}
    {stat_card("🔍", chunk_count,       "Vector Chunks", "#f59e0b")}
    {stat_card(ai_icon, ai_label,       "AI Engine",     ai_color)}
  </div>

  <div style="font-size:11px;font-weight:700;color:#475569;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px;">Features</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;">
    {feature_card("📚", "Library",    "Upload & manage your documents")}
    {feature_card("💬", "Q&A",        "Chat with your documents")}
    {feature_card("📝", "Quiz",       "Auto-generated MCQs")}
    {feature_card("🃏", "Flashcards", "Score-tracked study cards")}
    {feature_card("🗺️", "Mindmap",   "Visual topic maps")}
  </div>

  <!-- Tip -->
  <div style="background:#1e293b;border:1px solid #334155;border-left:4px solid #4F46E5;
              border-radius:12px;padding:14px 18px;">
    <div style="font-size:13px;color:#94a3b8;line-height:1.6;">{tip}</div>
  </div>
</div>
"""

def refresh_home():
    status = check_lmstudio_connection()
    return render_home_stats(status)

# -----------------------------------------------
# TAB 2: Library
# -----------------------------------------------
def render_upload_info_html(msg, ok=True):
    if not msg:
        return ""
    color = "#10b981" if ok else "#ef4444"
    safe = _html.escape(str(msg))
    return (f'<div style="background:#1e293b;border:1px solid {color}33;border-left:4px solid {color};'
            f'border-radius:12px;padding:13px 18px;font-family:\'Segoe UI\',sans-serif;'
            f'font-size:13px;color:#f1f5f9;white-space:pre-line;line-height:1.7;">{safe}</div>')

def render_qa_status_html():
    fn = get_active_filename()
    if not fn:
        return ('<div style="background:#1e293b;border-left:4px solid #ef4444;border-radius:0 10px 10px 0;'
                'padding:10px 16px;font-family:\'Segoe UI\',sans-serif;font-size:13px;color:#94a3b8;">'
                '❌ No active document — upload in Library</div>')
    return (f'<div style="background:#1e293b;border-left:4px solid #10b981;border-radius:0 10px 10px 0;'
            f'padding:10px 16px;font-family:\'Segoe UI\',sans-serif;font-size:13px;color:#34d399;">'
            f'✅ {_html.escape(fn)} &nbsp;·&nbsp; {len(library)} doc(s) loaded</div>')

def load_files(files):
    if files is None:
        return (render_upload_info_html("⚠️ No files uploaded.", ok=False),
                render_library_html(), get_doc_status(), render_qa_status_html(),
                get_radio_update(), get_checkbox_update(), get_checkbox_update(),
                get_checkbox_update(), render_home_stats())

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
        results.append(
            f"{file_icon} '{filename}' — {page_count} {get_page_label(file_path)}, "
            f"{len(raw_text.split())} words, {len(chunks)} chunks"
        )

    info = f"✅ {len(results)} file(s) processed:\n" + "\n".join(results)
    info += f"\n📚 Total docs in library: {len(library)}"

    return (
        render_upload_info_html(info),
        render_library_html(), get_doc_status(), render_qa_status_html(),
        get_radio_update(), get_checkbox_update(), get_checkbox_update(),
        get_checkbox_update(), render_home_stats(),
    )

def switch_active_doc(filename):
    if filename:
        set_active(filename)
    return (render_library_html(), get_doc_status(), get_radio_update(),
            get_checkbox_update(), get_checkbox_update(), get_checkbox_update(),
            render_qa_status_html())

def delete_doc(filename):
    if filename:
        remove_document(filename)
    return (render_library_html(), get_doc_status(), get_radio_update(),
            get_checkbox_update(), get_checkbox_update(), get_checkbox_update(),
            render_qa_status_html())

def refresh_library():
    return (render_library_html(), get_doc_status(), get_radio_update(),
            get_checkbox_update(), get_checkbox_update(), get_checkbox_update(),
            render_qa_status_html())

# -----------------------------------------------
# TAB 3: Q&A — Chat bubbles
# -----------------------------------------------
import re as _re

MATHJAX_SCRIPT = """
<script>
if (!window._rkMathJaxLoaded) {
  window._rkMathJaxLoaded = true;
  window.MathJax = {
    tex: {
      inlineMath: [['\\(','\\)']],
      displayMath: [['\\[','\\]']],
      processEscapes: true
    },
    options: { skipHtmlTags: ['script','noscript','style','textarea','pre'] },
    startup: { typeset: false }
  };
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.min.js';
  s.async = true;
  s.onload = function() { MathJax.typesetPromise && MathJax.typesetPromise(); };
  document.head.appendChild(s);
} else if (window.MathJax && window.MathJax.typesetPromise) {
  MathJax.typesetPromise();
}
</script>
"""

def format_ai_message(text: str) -> str:
    """Convert AI response markdown/LaTeX to safe HTML without losing math delimiters."""
    LATEX_BLOCK = _re.compile(r'(\\\[.*?\\\]|\\\(.*?\\\))', _re.DOTALL)
    parts = LATEX_BLOCK.split(text)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            result.append(part)
        else:
            safe = _html.escape(part)
            safe = _re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#f1f5f9;">\1</strong>', safe)
            safe = _re.sub(r'(?<![*_])\*([^*\n]+?)\*(?![*_])', r'<em>\1</em>', safe)
            safe = _re.sub(r'`([^`]+)`',
                r'<code style="background:#0f172a;padding:1px 6px;border-radius:4px;'
                r'font-size:13px;color:#a5b4fc;font-family:monospace;">\1</code>', safe)
            safe = _re.sub(r'(?m)^(\d+\.\s)',
                r'<span style="color:#818cf8;font-weight:700;">\1</span>', safe)
            safe = _re.sub(r'(?m)^([•\-]\s)',
                r'<span style="color:#818cf8;">\1</span>', safe)
            safe = safe.replace('\n', '<br>')
            result.append(safe)
    return ''.join(result)

def render_chat_bubbles():
    """Renders chat_log as styled HTML chat bubbles with LaTeX and markdown support."""
    if not chat_log:
        return """<div style="display:flex;align-items:center;justify-content:center;
            min-height:300px;font-family:'Segoe UI',sans-serif;color:#334155;font-size:15px;">
            💬 Ask a question about your documents to get started
        </div>"""

    bubbles = ""
    for speaker, msg in chat_log:
        if speaker == "You":
            safe_msg = _html.escape(msg).replace("\n", "<br>")
            bubbles += f"""
            <div style="display:flex;justify-content:flex-end;margin-bottom:16px;">
              <div style="max-width:72%;background:linear-gradient(135deg,#4F46E5,#6366f1);
                          color:#fff;border-radius:18px 18px 4px 18px;padding:13px 18px;
                          font-size:14px;line-height:1.6;box-shadow:0 4px 12px rgba(79,70,229,0.3);">
                {safe_msg}
              </div>
            </div>"""
        else:
            if "_[Source:" in msg or "_[Searched" in msg:
                parts = msg.rsplit("\n\n_", 1)
                body   = format_ai_message(parts[0])
                source = (f'<div style="margin-top:8px;font-size:11px;color:#64748b;'
                          f'border-top:1px solid #334155;padding-top:6px;">'
                          f'{_html.escape(parts[1].strip("_"))}</div>') if len(parts) > 1 else ""
            else:
                body   = format_ai_message(msg)
                source = ""

            bubbles += f"""
            <div style="display:flex;gap:10px;margin-bottom:16px;align-items:flex-start;">
              <div style="width:34px;height:34px;border-radius:10px;background:#1e293b;
                          border:1px solid #334155;display:flex;align-items:center;
                          justify-content:center;font-size:18px;flex-shrink:0;">🧠</div>
              <div style="max-width:76%;background:#1e293b;border:1px solid #334155;
                          border-radius:4px 18px 18px 18px;padding:13px 18px;
                          font-size:14px;color:#e2e8f0;line-height:1.75;
                          box-shadow:0 2px 8px rgba(0,0,0,0.2);">
                {body}
                {source}
              </div>
            </div>"""

    return (f'<div style="font-family:\'Segoe UI\',sans-serif;padding:12px 4px;'
            f'display:flex;flex-direction:column;">'
            f'{bubbles}</div>'
            f'{MATHJAX_SCRIPT}')

THINKING_BUBBLE = """
<div style="display:flex;gap:10px;margin-bottom:16px;align-items:flex-start;" id="rk_thinking">
  <div style="width:34px;height:34px;border-radius:10px;background:#1e293b;
              border:1px solid #334155;display:flex;align-items:center;
              justify-content:center;font-size:18px;flex-shrink:0;">🧠</div>
  <div style="background:#1e293b;border:1px solid #4F46E580;border-radius:4px 18px 18px 18px;
              padding:13px 20px;font-size:14px;color:#818cf8;font-style:italic;
              display:flex;align-items:center;gap:8px;">
    <span style="display:inline-block;animation:rk-pulse 1.2s ease-in-out infinite;">⋯</span>
    Thinking...
  </div>
</div>
<style>
@keyframes rk-pulse {
  0%,100%{opacity:0.3;transform:scale(0.9)}
  50%{opacity:1;transform:scale(1.1)}
}
</style>
"""

SCROLL_JS = """<script>
(function(){
  var d=document.getElementById('rk_chat_display');
  if(!d)return;
  var s=d;
  while(s&&s!==document.body){
    if(s.scrollHeight>s.clientHeight+2){s.scrollTop=s.scrollHeight;break;}
    s=s.parentElement;
  }
  window.scrollTo(0,document.body.scrollHeight);
})();
</script>"""

def render_chat_with_scroll():
    return render_chat_bubbles() + SCROLL_JS

def answer_question(question, chat_html, search_mode):
    global chat_log
    if not question.strip():
        yield chat_html, ""
        return

    chat_log.append(("You", question))

    if not get_active_filename():
        chat_log.append(("RK StudyMind", "⚠️ No document loaded. Please upload a PDF or DOCX in the Library tab first."))
        yield render_chat_with_scroll(), ""
        return

    # Show thinking bubble immediately
    yield render_chat_bubbles() + THINKING_BUBBLE + SCROLL_JS, ""

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
    chat_log.append(("RK StudyMind", f"{answer}\n\n_[{source_note}]_"))
    yield render_chat_with_scroll(), ""

def clear_chat():
    global chat_log
    chat_log = []
    return render_chat_bubbles(), ""

def get_qa_status():
    fn = get_active_filename()
    if not fn:
        return "❌ No active document — upload in Library"
    return f"✅ Active: {fn} — {len(library)} doc(s) loaded"

# -----------------------------------------------
# TAB 4: Smart Quiz
# -----------------------------------------------
def render_quiz_question(q, index, total, selected=None, revealed=False, score=0):
    progress_pct = int(((index + 1) / total) * 100)
    options_html = ""
    for letter, text in q["options"].items():
        if revealed:
            if letter == q["answer"]:
                lbg, lclr, rbg, rborder, tclr, fw = "#10b981","#fff","#0d2318","2px solid #10b981","#6ee7b7","700"
                icon = "✅"
            elif letter == selected:
                lbg, lclr, rbg, rborder, tclr, fw = "#ef4444","#fff","#2d1212","2px solid #ef4444","#fca5a5","600"
                icon = "❌"
            else:
                lbg, lclr, rbg, rborder, tclr, fw = "#1e293b","#334155","#0f172a","1px solid #1e293b","#334155","400"
                icon = letter
            click = ""
        else:
            if letter == selected:
                lbg, lclr, rbg, rborder, tclr, fw = "#4F46E5","#fff","#1a1f4a","2px solid #4F46E5","#c7d2fe","700"
            else:
                lbg, lclr, rbg, rborder, tclr, fw = "#1e293b","#64748b","#0f172a","1px solid #334155","#e2e8f0","400"
            icon = letter
            hover_in  = f"if(this.dataset.picked!='1'){{this.style.background='#1a2540';this.style.borderColor='#475569';}}"
            hover_out = f"if(this.dataset.picked!='1'){{this.style.background='{rbg}';this.style.borderColor='#334155';}}"
            click = (f'onclick="var el=document.getElementById(\'rk_quiz_btn_{letter.lower()}\');'
                     f'if(el){{(el.querySelector(\'button\')||el).click();}}" '
                     f'onmouseover="{hover_in}" onmouseout="{hover_out}"')

        options_html += f"""<div {click}
          style="display:flex;align-items:center;gap:12px;background:{rbg};border:{rborder};
                 border-radius:12px;padding:13px 16px;margin-bottom:8px;
                 cursor:{'default' if revealed else 'pointer'};transition:all 0.15s;user-select:none;">
          <div style="width:30px;height:30px;border-radius:8px;background:{lbg};flex-shrink:0;
                      display:flex;align-items:center;justify-content:center;
                      font-size:12px;font-weight:700;color:{lclr};">{icon}</div>
          <div style="color:{tclr};font-size:14px;font-weight:{fw};line-height:1.45;">{text}</div>
        </div>"""

    explanation = ""
    if revealed:
        exp_text = _html.escape(q.get('explanation', f"Correct answer: {q['answer']}"))
        explanation = f"""<div style="background:#0f172a;border-left:3px solid #4F46E5;
            border-radius:0 10px 10px 0;padding:13px 16px;margin-top:4px;
            color:#94a3b8;font-size:13px;line-height:1.6;">
            💡 <strong style="color:#c7d2fe;">Why:</strong> {exp_text}</div>"""

    score_pill = f"""<span style="background:#10b98120;color:#34d399;border:1px solid #10b98140;
        border-radius:20px;padding:3px 12px;font-size:11px;font-weight:700;">✅ {score}/{index+1}</span>""" if revealed or score > 0 else ""

    if revealed:
        is_last = (index >= total - 1)
        label = "See Results 🏆" if is_last else "Next Question →"
        color = "#10b981" if is_last else "#4F46E5"
        action_js = "var el=document.getElementById('rk_quiz_next');if(el){(el.querySelector('button')||el).click();}"
        action_btn = f"""<div onclick="{action_js}"
            style="margin-top:18px;background:{color};border-radius:12px;padding:14px;
                   color:#fff;font-size:14px;font-weight:700;text-align:center;
                   cursor:pointer;user-select:none;"
            onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
            {label}</div>"""
    elif selected:
        submit_js = "var el=document.getElementById('rk_quiz_submit');if(el){(el.querySelector('button')||el).click();}"
        action_btn = f"""<div onclick="{submit_js}"
            style="margin-top:18px;background:#4F46E5;border-radius:12px;padding:14px;
                   color:#fff;font-size:14px;font-weight:700;text-align:center;
                   cursor:pointer;user-select:none;"
            onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
            Submit Answer ✅</div>"""
    else:
        action_btn = """<div style="margin-top:18px;background:#0f172a;border:1px dashed #334155;
            border-radius:12px;padding:13px;color:#475569;font-size:13px;text-align:center;">
            Select an answer to continue</div>"""

    q_text = _html.escape(q['question'])
    return f"""<div style="font-family:'Segoe UI',sans-serif;padding:4px 0;">
      <div style="background:#1e293b;border:1px solid #334155;border-radius:20px;
                  padding:28px 32px;max-width:760px;margin:0 auto;">
        <div style="background:#0f172a;border-radius:10px;height:5px;margin-bottom:20px;overflow:hidden;">
          <div style="background:linear-gradient(90deg,#4F46E5,#818cf8);height:100%;
                      border-radius:10px;width:{progress_pct}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
          <span style="background:#4F46E530;color:#a5b4fc;border:1px solid #4F46E550;
                       border-radius:20px;padding:4px 14px;font-size:11px;font-weight:700;">
            Q {index+1} / {total}</span>
          {score_pill}
        </div>
        <div style="font-size:17px;font-weight:700;color:#f1f5f9;margin-bottom:20px;line-height:1.55;">{q_text}</div>
        {options_html}{explanation}{action_btn}
      </div></div>"""

def render_quiz_empty():
    return """<div style="font-family:'Segoe UI',sans-serif;padding:4px 0;">
      <div style="background:#1e293b;border:2px dashed #334155;border-radius:20px;
                  max-width:760px;margin:0 auto;min-height:220px;
                  display:flex;flex-direction:column;align-items:center;
                  justify-content:center;gap:10px;">
        <div style="font-size:36px;">📝</div>
        <div style="color:#64748b;font-size:15px;font-weight:600;">Generate a quiz to start</div>
        <div style="color:#334155;font-size:12px;">Select documents and hit Generate above</div>
      </div></div>"""

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
          <div><div style="font-size:34px;font-weight:800;color:#10b981;">{score}</div><div style="font-size:13px;color:#94a3b8;">Correct</div></div>
          <div><div style="font-size:34px;font-weight:800;color:#ef4444;">{total-score}</div><div style="font-size:13px;color:#94a3b8;">Wrong</div></div>
          <div><div style="font-size:34px;font-weight:800;color:{color};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score</div></div>
        </div>
      </div></div>"""

def qbm(): # quiz button mode helper — waiting for generation / between questions
    return (gr.update(interactive=True,variant="primary"),)*4 + (gr.update(interactive=False,variant="secondary"),)*3
def qam(): # answer selected, ready to submit
    return (gr.update(interactive=True,variant="secondary"),)*4 + (gr.update(interactive=True,variant="primary"),gr.update(interactive=False,variant="secondary"),gr.update(interactive=False,variant="secondary"))
def qrm(): # revealed, ready for next
    return (gr.update(interactive=False,variant="secondary"),)*5 + (gr.update(interactive=True,variant="primary"),gr.update(interactive=False,variant="secondary"))
def qdm(): # done — show restart
    return (gr.update(interactive=False,variant="secondary"),)*6 + (gr.update(interactive=True,variant="primary"),)

def start_quiz(num_q, selected_docs):
    global current_quiz
    selected_docs = sanitize_docs(selected_docs)
    if not selected_docs:
        return "⚠️ No documents selected — please upload files and tick at least one.", render_quiz_empty(), 0, None, False, 0, *qbm()
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        return "⚠️ Documents have no text.", render_quiz_empty(), 0, None, False, 0, *qbm()
    questions = generate_quiz(text=text, num_questions=int(num_q))
    if not questions:
        return "⚠️ Could not generate quiz.", render_quiz_empty(), 0, None, False, 0, *qbm()
    current_quiz = questions
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else selected_docs[0]
    return (f"✅ {len(questions)} questions from: {source}",
            render_quiz_question(questions[0], 0, len(questions), score=0), 0, None, False, 0, *qbm())

def quiz_select_answer(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), q_index, selected_letter, revealed, score, *qbm()
    idx = int(q_index)
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz), selected_letter, revealed, score),
            idx, selected_letter, revealed, score, *qam())

def quiz_submit(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz or selected_letter is None:
        return render_quiz_empty(), q_index, selected_letter, True, score, *qam()
    idx = int(q_index)
    q = current_quiz[idx]
    new_score = score + (1 if selected_letter == q["answer"] else 0)
    return (render_quiz_question(q, idx, len(current_quiz), selected_letter, True, new_score),
            idx, selected_letter, True, new_score, *qrm())

def quiz_next(q_index, selected_letter, revealed, score):
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), 0, None, False, score, *qbm()
    idx = int(q_index) + 1
    if idx >= len(current_quiz):
        return render_quiz_results(score, len(current_quiz)), idx-1, None, False, score, *qdm()
    return (render_quiz_question(current_quiz[idx], idx, len(current_quiz), score=score),
            idx, None, False, score, *qbm())

def quiz_restart():
    global current_quiz
    if not current_quiz:
        return render_quiz_empty(), 0, None, False, 0, *qbm()
    return (render_quiz_question(current_quiz[0], 0, len(current_quiz), score=0), 0, None, False, 0, *qbm())

# -----------------------------------------------
# TAB 5: Flashcards
# -----------------------------------------------
CARD_COLORS = ["#4F46E5", "#0891B2", "#059669", "#D97706", "#DC2626", "#7C3AED"]

def qmode():
    return (gr.update(interactive=True,variant="secondary"), gr.update(interactive=True,variant="primary"),
            gr.update(interactive=False,variant="secondary"), gr.update(interactive=False,variant="secondary"),
            gr.update(interactive=False,variant="secondary"))
def amode():
    return (gr.update(interactive=False,variant="secondary"), gr.update(interactive=False,variant="secondary"),
            gr.update(interactive=True,variant="primary"), gr.update(interactive=True,variant="secondary"),
            gr.update(interactive=False,variant="secondary"))
def dmode():
    return (gr.update(interactive=False,variant="secondary"),)*4 + (gr.update(interactive=True,variant="primary"),)

def render_score_bar(correct, wrong, total):
    answered = correct + wrong
    if answered == 0: return ""
    pct = int((correct / answered) * 100)
    bar_fill = int((correct / total) * 100)
    return f"""<div style="max-width:680px;margin:0 auto 10px auto;font-family:'Segoe UI',sans-serif;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="color:#94a3b8;font-size:13px;">Score: {answered}/{total} answered</span>
          <span style="font-size:14px;font-weight:700;color:#10b981;">✅ {correct} &nbsp;❌ {wrong} &nbsp;{pct}%</span>
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
          <div><div style="font-size:36px;font-weight:800;color:#10b981;">{correct}</div><div style="font-size:13px;color:#94a3b8;">Correct ✅</div></div>
          <div><div style="font-size:36px;font-weight:800;color:#ef4444;">{wrong}</div><div style="font-size:13px;color:#94a3b8;">Wrong ❌</div></div>
          <div><div style="font-size:36px;font-weight:800;color:{color};">{pct}%</div><div style="font-size:13px;color:#94a3b8;">Score 📊</div></div>
        </div>
        <div style="font-size:13px;color:#475569;margin-top:8px;">Click <strong style="color:#f1f5f9;">🔁 Study Again</strong> to restart</div>
      </div></div>"""

def render_card_html(card, index, total, revealed, correct=0, wrong=0):
    color = CARD_COLORS[index % len(CARD_COLORS)]
    score_bar = render_score_bar(correct, wrong, total)
    if not revealed:
        side_label, content = "QUESTION", _html.escape(card["question"])
        text_color, bg_color, border_style = "#ffffff", color, "border:none;"
        hint = "<div style='margin-top:24px;text-align:center;font-size:12px;color:rgba(255,255,255,0.4);'>Think of the answer, then click 🔄 Reveal Answer</div>"
    else:
        side_label, content = "ANSWER", _html.escape(card["answer"])
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
    return """<div style="display:flex;justify-content:center;padding:20px;">
        <div style="background:#1e293b;border:2px dashed #475569;border-radius:20px;
                    width:100%;max-width:680px;min-height:280px;display:flex;align-items:center;
                    justify-content:center;color:#94a3b8;font-size:18px;font-family:'Segoe UI',sans-serif;">
          Generate flashcards to start studying 🃏</div></div>"""

def make_flashcards(num_cards, selected_docs):
    global current_flashcards
    selected_docs = sanitize_docs(selected_docs)
    if not selected_docs:
        return "⚠️ No documents selected.", render_empty_card(), 0, False, 0, 0, *qmode()
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        return "⚠️ Selected documents have no text.", render_empty_card(), 0, False, 0, 0, *qmode()
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else selected_docs[0]
    cards = generate_flashcards(text=text, filename=source, num_cards=int(num_cards))
    current_flashcards = cards
    return (f"✅ {len(cards)} flashcards from: {source}",
            render_card_html(cards[0], 0, len(cards), False), 0, False, 0, 0, *qmode())

def reveal_answer(card_index, show_answer, correct, wrong):
    global current_flashcards
    if not current_flashcards: return render_empty_card(), card_index, True, correct, wrong, *amode()
    idx = int(card_index)
    return render_card_html(current_flashcards[idx], idx, len(current_flashcards), True, correct, wrong), idx, True, correct, wrong, *amode()

def score_correct(card_index, correct, wrong):
    global current_flashcards
    correct += 1
    total = len(current_flashcards)
    if int(card_index) >= total - 1:
        return render_results_html(correct, wrong, total), int(card_index), False, correct, wrong, *dmode()
    idx = int(card_index) + 1
    return render_card_html(current_flashcards[idx], idx, total, False, correct, wrong), idx, False, correct, wrong, *qmode()

def score_wrong(card_index, correct, wrong):
    global current_flashcards
    wrong += 1
    total = len(current_flashcards)
    if int(card_index) >= total - 1:
        return render_results_html(correct, wrong, total), int(card_index), False, correct, wrong, *dmode()
    idx = int(card_index) + 1
    return render_card_html(current_flashcards[idx], idx, total, False, correct, wrong), idx, False, correct, wrong, *qmode()

def prev_card(card_index, correct, wrong):
    global current_flashcards
    if not current_flashcards: return render_empty_card(), 0, False, correct, wrong, *qmode()
    idx = (int(card_index) - 1) % len(current_flashcards)
    return render_card_html(current_flashcards[idx], idx, len(current_flashcards), False, correct, wrong), idx, False, correct, wrong, *qmode()

def study_again():
    global current_flashcards
    if not current_flashcards: return render_empty_card(), 0, False, 0, 0, *qmode()
    return render_card_html(current_flashcards[0], 0, len(current_flashcards), False), 0, False, 0, 0, *qmode()

# -----------------------------------------------
# TAB 6: Mindmap
# -----------------------------------------------
def render_mindmap_status_html(msg, ok=True):
    if not msg:
        return ""
    color = "#10b981" if ok else "#ef4444"
    safe = _html.escape(str(msg))
    return (f'<div style="background:#1e293b;border:1px solid {color}33;border-left:4px solid {color};'
            f'border-radius:12px;padding:12px 18px;font-family:\'Segoe UI\',sans-serif;'
            f'font-size:13px;color:#f1f5f9;font-weight:500;">{safe}</div>')

def render_mindmap_empty():
    return """<div style="background:#1e293b;border:2px dashed #334155;border-radius:16px;
        min-height:480px;display:flex;flex-direction:column;align-items:center;
        justify-content:center;gap:12px;font-family:'Segoe UI',sans-serif;">
      <div style="font-size:40px;">🗺️</div>
      <div style="color:#64748b;font-size:15px;font-weight:600;">No mindmap yet</div>
      <div style="color:#334155;font-size:12px;">Select documents and click Generate above</div>
    </div>"""

def render_mindmap_loading():
    return """
    <style>@keyframes rk-mm-spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}</style>
    <div style="background:#1e293b;border:1px solid #334155;border-radius:16px;
        min-height:480px;display:flex;flex-direction:column;align-items:center;
        justify-content:center;gap:16px;font-family:'Segoe UI',sans-serif;">
      <div style="font-size:42px;animation:rk-mm-spin 3s linear infinite;">🗺️</div>
      <div style="color:#818cf8;font-size:15px;font-weight:600;">Building your mindmap…</div>
      <div style="color:#475569;font-size:13px;">Analysing document structure</div>
    </div>"""

def render_mindmap_iframe(html_content, title=""):
    srcdoc = html_content.replace("&", "&amp;").replace('"', "&quot;")
    safe_title = _html.escape(title)
    return f"""<div style="font-family:'Segoe UI',sans-serif;">
      <div style="background:#1e293b;border:1px solid #334155;border-radius:16px;overflow:hidden;">
        <div style="background:#0f172a;padding:10px 18px;display:flex;align-items:center;
                    justify-content:space-between;border-bottom:1px solid #334155;">
          <div style="font-size:13px;color:#a5b4fc;font-weight:600;">🗺️ {safe_title}</div>
          <div style="font-size:11px;color:#475569;">Scroll to zoom &nbsp;·&nbsp; Drag to pan &nbsp;·&nbsp; Click nodes to expand/collapse</div>
        </div>
        <iframe srcdoc="{srcdoc}"
          style="width:100%;height:580px;border:none;display:block;"
          sandbox="allow-scripts allow-same-origin"></iframe>
      </div>
    </div>"""

def make_mindmap_full(topic, selected_docs):
    selected_docs = sanitize_docs(selected_docs)
    if not selected_docs:
        yield render_mindmap_status_html("⚠️ No documents selected.", ok=False), render_mindmap_empty()
        return
    text = get_text_from_selection(selected_docs)
    if not text.strip():
        yield render_mindmap_status_html("⚠️ Selected documents have no text.", ok=False), render_mindmap_empty()
        return

    title = topic.strip() if topic.strip() else (
        f"{len(selected_docs)} Documents" if len(selected_docs) > 1
        else selected_docs[0].rsplit(".", 1)[0]
    )
    source = f"{len(selected_docs)} doc(s)" if len(selected_docs) > 1 else selected_docs[0]

    # Show loading state immediately (requires demo.queue())
    yield render_mindmap_status_html("⏳ Generating mindmap… this may take a moment."), render_mindmap_loading()

    md = generate_mindmap_markdown(text=text, topic=topic)
    html_out = mindmap_to_html(md, title=title)

    yield (render_mindmap_status_html(f"✅ Mindmap ready · {_html.escape(source)}"),
           render_mindmap_iframe(html_out, title))

# -----------------------------------------------
# UI
# -----------------------------------------------
css = """
    .gradio-container{max-width:100%!important;width:100%!important;margin:0!important;padding:20px!important;}
    footer{display:none!important;}
    .rk-hidden-btn {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip: rect(0,0,0,0) !important;
        white-space: nowrap !important;
        pointer-events: none !important;
        opacity: 0 !important;
    }
"""

with gr.Blocks(title="🧠 RK StudyMind", css=css) as demo:
    gr.Markdown("# 🧠 RK StudyMind")
    gr.Markdown("### Your Personal AI Study Companion")

    with gr.Tabs():

        # TAB 0: Home
        with gr.Tab("🏠 Home"):
            home_html = gr.HTML(value=render_home_stats())
            gr.Button("🔄 Refresh Stats & Check AI", variant="primary", size="lg").click(
                fn=refresh_home, inputs=[], outputs=home_html)

        # TAB 1: Library
        with gr.Tab("📚 Library"):
            gr.Markdown("### Document Library")
            gr.Markdown("_Upload PDFs or DOCX. All feature tabs update automatically._")
            with gr.Row():
                file_input  = gr.File(label="Upload PDF or DOCX", file_types=[".pdf",".docx"], file_count="multiple")
                upload_btn  = gr.Button("Add to Library 📚", variant="primary", scale=0)
            upload_info     = gr.HTML("")
            gr.Markdown("---")
            library_html    = gr.HTML(value=render_library_html())
            lib_doc_status  = gr.Textbox(label="Active Document", interactive=False, lines=1, value=get_doc_status())
            doc_selector    = gr.Radio(label="📂 Select a document", choices=get_all_filenames(),
                                       value=get_active_filename() or None, interactive=True)
            with gr.Row():
                set_active_btn = gr.Button("✅ Set as Active", variant="primary",   scale=1)
                remove_btn     = gr.Button("🗑 Remove",         variant="secondary", scale=1)
                refresh_btn    = gr.Button("🔄 Refresh",         variant="secondary", scale=1)

        # TAB 2: Q&A
        with gr.Tab("💬 Q&A"):
            gr.Markdown("### Chat with your Documents")
            qa_status_html = gr.HTML(value=render_qa_status_html())
            search_mode = gr.Radio(
                choices=["🔍 Active Document Only", "🌐 All Documents"],
                value="🔍 Active Document Only", label="Search Scope"
            )
            chat_html_display = gr.HTML(value=render_chat_bubbles(), elem_id="rk_chat_display")
            with gr.Row():
                question_input = gr.Textbox(
                    label="Your question",
                    placeholder="e.g. What is Newton's first law?",
                    lines=2, scale=5
                )
                ask_btn = gr.Button("Ask 🔍", variant="primary", scale=1)
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

            ask_btn.click(fn=answer_question,
                inputs=[question_input, chat_html_display, search_mode],
                outputs=[chat_html_display, question_input])
            question_input.submit(fn=answer_question,
                inputs=[question_input, chat_html_display, search_mode],
                outputs=[chat_html_display, question_input])
            clear_btn.click(fn=clear_chat, inputs=[],
                outputs=[chat_html_display, question_input])

        # TAB 3: Quiz
        with gr.Tab("📝 Quiz"):
            gr.Markdown("### Smart Quiz — Multiple Choice")
            quiz_doc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Quiz",
                choices=get_all_filenames(), value=[], interactive=True)
            with gr.Row():
                num_q_slider   = gr.Slider(minimum=3, maximum=10, value=5, step=1, label="Number of questions")
                start_quiz_btn = gr.Button("Generate Quiz 📝", variant="primary")
            quiz_status   = gr.Textbox(label="Status", interactive=False, lines=1)
            quiz_html_out = gr.HTML(value=render_quiz_empty())
            q_idx   = gr.State(value=0)
            sel_ans = gr.State(value=None)
            rev_ans = gr.State(value=False)
            sc_ans  = gr.State(value=0)

            # Off-screen hidden buttons — triggered by JS click events in quiz card HTML
            # Using elem_classes + CSS clip trick (no scrollbar flash vs position:fixed)
            with gr.Row(elem_classes=["rk-hidden-btn"]):
                btn_a = gr.Button("A", elem_id="rk_quiz_btn_a")
                btn_b = gr.Button("B", elem_id="rk_quiz_btn_b")
                btn_c = gr.Button("C", elem_id="rk_quiz_btn_c")
                btn_d = gr.Button("D", elem_id="rk_quiz_btn_d")
                sub_btn = gr.Button("Submit", elem_id="rk_quiz_submit")
                nxt_btn = gr.Button("Next",   elem_id="rk_quiz_next")
                rst_btn = gr.Button("Restart",elem_id="rk_quiz_restart")

            qbo = [btn_a, btn_b, btn_c, btn_d, sub_btn, nxt_btn, rst_btn]
            qouts = [quiz_html_out, q_idx, sel_ans, rev_ans, sc_ans] + qbo
            start_quiz_btn.click(fn=start_quiz, inputs=[num_q_slider, quiz_doc_selector],
                outputs=[quiz_status, quiz_html_out, q_idx, sel_ans, rev_ans, sc_ans] + qbo)
            btn_a.click(fn=lambda a,b,c,d: quiz_select_answer(a,"A",c,d), inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_b.click(fn=lambda a,b,c,d: quiz_select_answer(a,"B",c,d), inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_c.click(fn=lambda a,b,c,d: quiz_select_answer(a,"C",c,d), inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            btn_d.click(fn=lambda a,b,c,d: quiz_select_answer(a,"D",c,d), inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            sub_btn.click(fn=quiz_submit,  inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            nxt_btn.click(fn=quiz_next,    inputs=[q_idx,sel_ans,rev_ans,sc_ans], outputs=qouts)
            rst_btn.click(fn=quiz_restart, inputs=[], outputs=qouts)

        # TAB 4: Flashcards
        with gr.Tab("🃏 Flashcards"):
            gr.Markdown("### Study Flashcards — One Card at a Time")
            fc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Flashcards",
                choices=get_all_filenames(), value=[], interactive=True)
            with gr.Row():
                num_cards_slider = gr.Slider(minimum=5, maximum=40, value=10, step=5, label="Number of flashcards")
                generate_btn     = gr.Button("Generate Flashcards 🃏", variant="primary", scale=0)
            fc_status         = gr.Textbox(label="Status", interactive=False, lines=1)
            card_html_display = gr.HTML(value=render_empty_card())
            card_idx   = gr.State(value=0)
            show_ans   = gr.State(value=False)
            correct_st = gr.State(value=0)
            wrong_st   = gr.State(value=0)
            with gr.Row():
                prev_btn        = gr.Button("⬅️ Previous",        variant="secondary", interactive=True,  scale=1)
                reveal_btn      = gr.Button("🔄 Reveal Answer",    variant="primary",   interactive=True,  scale=2)
                correct_btn     = gr.Button("✅  Got It!",          variant="secondary", interactive=False, scale=1)
                wrong_btn_fc    = gr.Button("❌  Didn't Remember", variant="secondary", interactive=False, scale=1)
                study_again_btn = gr.Button("🔁 Study Again",      variant="secondary", interactive=False, scale=1)
            card_outs = [card_html_display, card_idx, show_ans, correct_st, wrong_st,
                         prev_btn, reveal_btn, correct_btn, wrong_btn_fc, study_again_btn]
            generate_btn.click(fn=make_flashcards, inputs=[num_cards_slider, fc_selector],
                outputs=[fc_status, card_html_display, card_idx, show_ans, correct_st, wrong_st,
                         prev_btn, reveal_btn, correct_btn, wrong_btn_fc, study_again_btn])
            reveal_btn.click(fn=reveal_answer,  inputs=[card_idx,show_ans,correct_st,wrong_st], outputs=card_outs)
            correct_btn.click(fn=score_correct, inputs=[card_idx,correct_st,wrong_st],           outputs=card_outs)
            wrong_btn_fc.click(fn=score_wrong,  inputs=[card_idx,correct_st,wrong_st],           outputs=card_outs)
            prev_btn.click(fn=prev_card,        inputs=[card_idx,correct_st,wrong_st],           outputs=card_outs)
            study_again_btn.click(fn=study_again, inputs=[],                                     outputs=card_outs)

        # TAB 5: Mindmap
        with gr.Tab("🗺️ Mindmap"):
            gr.Markdown("### Generate an Interactive Mindmap")
            mm_doc_selector = gr.CheckboxGroup(
                label="📄 Select Documents for Mindmap",
                choices=get_all_filenames(), value=[], interactive=True)
            with gr.Row():
                topic_input     = gr.Textbox(label="Topic (optional)", placeholder="Leave blank to auto-detect", lines=1, scale=3)
                mm_generate_btn = gr.Button("Generate Mindmap 🗺️", variant="primary", scale=0)
            mm_status_html = gr.HTML("")
            mm_display     = gr.HTML(value=render_mindmap_empty())
            mm_generate_btn.click(fn=make_mindmap_full, inputs=[topic_input, mm_doc_selector],
                outputs=[mm_status_html, mm_display])

    # -----------------------------------------------
    # Library → sync all selectors
    # -----------------------------------------------
    lib_sync_outputs = [library_html, lib_doc_status, doc_selector,
                        quiz_doc_selector, fc_selector, mm_doc_selector, qa_status_html]

    upload_btn.click(fn=load_files, inputs=[file_input],
        outputs=[upload_info, library_html, lib_doc_status, qa_status_html, doc_selector,
                 quiz_doc_selector, fc_selector, mm_doc_selector, home_html])
    set_active_btn.click(fn=switch_active_doc, inputs=[doc_selector], outputs=lib_sync_outputs)
    remove_btn.click(fn=delete_doc,            inputs=[doc_selector], outputs=lib_sync_outputs)
    refresh_btn.click(fn=refresh_library,      inputs=[],             outputs=lib_sync_outputs)

if __name__ == "__main__":
    demo.queue()   # Required for generator functions (mindmap loading state, Q&A thinking bubble)
    demo.launch(inbrowser=True, theme=gr.themes.Soft(), css=css)
