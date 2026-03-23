import gradio as gr
import sys
import os

sys.path.append(os.path.dirname(__file__))
from modules.pdf_reader import read_pdf, get_page_count, chunk_text
from modules.ai_engine import ask_lmstudio, check_lmstudio_connection

# =============================================
# 🧠 RK StudyMind - Your Personal AI Study App
# Built by: RoniKid @ GCTU
# AI Brain: LM Studio (100% Offline)
# =============================================

# Global state
loaded_pdf_text = {"text": "", "chunks": [], "filename": ""}

# -----------------------------------------------
# TAB 1: Home
# -----------------------------------------------
def greet(name):
    if not name.strip():
        return "⚠️ Please enter your name!"
    status = check_lmstudio_connection()
    return (
        f"👋 Welcome to RK StudyMind, {name}!\n\n"
        f"📚 Your AI-powered study companion is ready.\n\n"
        f"🤖 AI Status: {status}"
    )

def check_status():
    return check_lmstudio_connection()

# -----------------------------------------------
# TAB 2: PDF Reader
# -----------------------------------------------
def load_pdf(file):
    if file is None:
        return "⚠️ No file uploaded.", ""

    file_path = file.name
    page_count = get_page_count(file_path)
    raw_text = read_pdf(file_path)
    chunks = chunk_text(raw_text)

    loaded_pdf_text["text"] = raw_text
    loaded_pdf_text["chunks"] = chunks
    loaded_pdf_text["filename"] = os.path.basename(file_path)

    info = (
        f"✅ PDF loaded successfully!\n"
        f"📄 Pages: {page_count}\n"
        f"🔤 Words: {len(raw_text.split())}\n"
        f"🧩 Chunks created: {len(chunks)}\n"
        f"📁 File: {loaded_pdf_text['filename']}\n\n"
        f"✅ Ready — go to the 💬 Q&A tab!"
    )

    preview = raw_text[:2000] + "\n\n... [truncated]" if len(raw_text) > 2000 else raw_text
    return info, preview

# -----------------------------------------------
# TAB 3: Document Q&A
# Using gr.Textbox instead of gr.Chatbot
# to avoid all version compatibility issues
# -----------------------------------------------
chat_log = []

def answer_question(question, history_display):
    global chat_log

    if not question.strip():
        return history_display, ""

    if not loaded_pdf_text["text"]:
        chat_log.append(("You", question))
        chat_log.append(("RK StudyMine", "⚠️ No document loaded. Please go to 📄 PDF Reader first and upload a PDF."))
    else:
        context = loaded_pdf_text["text"][:4000]
        answer = ask_lmstudio(prompt=question, context=context)
        chat_log.append(("You", question))
        chat_log.append(("RK StudyMine", answer))

    # Format chat as readable text
    display = ""
    for speaker, msg in chat_log:
        if speaker == "You":
            display += f"🧑 You:\n{msg}\n\n"
        else:
            display += f"🤖 RK StudyMine:\n{msg}\n\n{'─'*50}\n\n"

    return display, ""

def clear_chat():
    global chat_log
    chat_log = []
    return "", ""

# -----------------------------------------------
# UI Layout
# -----------------------------------------------
css = """
    .gradio-container {
        max-width: 100% !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 20px !important;
    }
    footer { display: none !important; }
"""

with gr.Blocks(title="🧠 RK StudyMine") as demo:

    gr.Markdown("# 🧠 RK StudyMine")
    gr.Markdown("### Your Personal AI Study Companion — GCTU Edition")

    with gr.Tabs():

        # ---- TAB 1: Home ----
        with gr.Tab("🏠 Home"):
            gr.Markdown("#### Check your AI connection and get started")
            with gr.Row():
                name_input = gr.Textbox(label="Your name", placeholder="e.g. RoniKid", lines=1)
                output = gr.Textbox(label="Status", interactive=False, lines=6)
            start_btn = gr.Button("Launch RK StudyMine 🚀", variant="primary", size="lg")
            start_btn.click(fn=greet, inputs=name_input, outputs=output)
            gr.Markdown("---")
            status_output = gr.Textbox(label="LM Studio Connection", interactive=False, lines=2)
            check_btn = gr.Button("Check LM Studio 🔌", variant="secondary")
            check_btn.click(fn=check_status, inputs=[], outputs=status_output)

        # ---- TAB 2: PDF Reader ----
        with gr.Tab("📄 PDF Reader"):
            gr.Markdown("### Upload a lecture note or textbook PDF")
            gr.Markdown("_Supported: Any text-based PDF (not scanned images)_")
            pdf_input = gr.File(label="Upload PDF", file_types=[".pdf"])
            load_btn = gr.Button("Read PDF 📖", variant="primary")
            with gr.Row():
                info_output = gr.Textbox(label="Document Info", lines=8, interactive=False)
                preview_output = gr.Textbox(label="Text Preview", lines=8, interactive=False)
            load_btn.click(fn=load_pdf, inputs=pdf_input, outputs=[info_output, preview_output])

        # ---- TAB 3: Q&A ----
        with gr.Tab("💬 Q&A"):
            gr.Markdown("### Chat with your uploaded document")
            gr.Markdown("_Upload a PDF first, then ask anything about it_")

            chat_display = gr.Textbox(
                label="Conversation",
                lines=18,
                interactive=False,
                placeholder="Your conversation will appear here..."
            )

            with gr.Row():
                question_input = gr.Textbox(
                    label="Ask a question",
                    placeholder="e.g. What topics are covered in Week 3?",
                    lines=2,
                    scale=4
                )
                ask_btn = gr.Button("Ask 🔍", variant="primary", scale=1)

            clear_btn = gr.Button("Clear Chat 🗑️", variant="secondary")

            ask_btn.click(
                fn=answer_question,
                inputs=[question_input, chat_display],
                outputs=[chat_display, question_input]
            )
            question_input.submit(
                fn=answer_question,
                inputs=[question_input, chat_display],
                outputs=[chat_display, question_input]
            )
            clear_btn.click(fn=clear_chat, inputs=[], outputs=[chat_display, question_input])

if __name__ == "__main__":
    demo.launch(
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=css
    )
