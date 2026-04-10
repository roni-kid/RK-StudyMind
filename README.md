# 🧠 RK StudyMind
> Your Personal AI-Powered Study Companion — Built by RoniKid

RK StudyMind is a fully offline AI study app that lets you chat with your lecture notes, generate flashcards with score tracking, take multiple choice quizzes, and generate interactive mindmaps — all running locally on your PC using LM Studio. No internet, no API keys, no subscriptions.

---

## ✨ Features — v1.1

| Feature | Description |
|---|---|
| 📚 **Document Library** | Upload PDFs, DOCX, TXT, Markdown, PowerPoint (.pptx), and EPUB files. Styled document cards show file type, page/slide/chapter count, word count and chunk count. |
| 💬 **Document Q&A (RAG)** | Chat with your documents using Retrieval Augmented Generation. Inter-font chat bubbles with right-aligned user messages, left-aligned AI responses with 🧠 avatar, timestamps, source badges, and an animated 3-dot typing indicator. |
| 📝 **Smart Quiz** | Auto-generates multiple choice questions (A–D) with a progress bar, live score pill, inline answer selection, and a final results screen. Supports up to 40 questions with batch generation. |
| 🃏 **Flashcards** | Generates up to 40 Q&A study cards. One card at a time with ✅ / ❌ score tracking, a live score bar, and a session results screen. |
| 🗺️ **Mindmap** | AI generates a structured topic map rendered as an interactive radial canvas — embedded directly inside the app. Scroll to zoom, drag to pan, Reset/+/− controls. |
| 🔍 **Semantic Search** | ChromaDB + sentence-transformers power meaning-based search across all your documents. |
| 🖥️ **Splash Screen** | macOS-style spinner + segmented progress bar while the embedding model loads on startup. Dismisses automatically the moment the model is ready. |

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| UI | Gradio 6.0+ (Python) |
| AI Brain | LM Studio (100% Offline, any local model) |
| Document Reading | PyMuPDF (PDF) · python-docx (DOCX) · python-pptx (PPTX) · ebooklib + BeautifulSoup (EPUB) · built-in (TXT, MD) |
| Semantic Search | ChromaDB + sentence-transformers |
| Mindmap Rendering | Custom HTML5 Canvas radial renderer (no external dependencies) |
| Embeddings | all-MiniLM-L6-v2 (local, auto-downloaded once) |
| Fonts | Inter (chat UI) · JetBrains Mono (code blocks) via Google Fonts |

---

## 📂 Supported File Types

| Extension | Type | Extraction Method |
|---|---|---|
| `.pdf` | PDF | PyMuPDF — page by page |
| `.docx` | Word Document | python-docx — paragraphs + tables |
| `.pptx` | PowerPoint | python-pptx — slide text + tables + speaker notes |
| `.epub` | Ebook | ebooklib + BeautifulSoup — chapter by chapter |
| `.md` | Markdown | Built-in — strips `#`, `**`, `` ` `` markers before indexing |
| `.txt` | Plain Text | Built-in — auto encoding fallback (utf-8 → latin-1 → cp1252) |

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/roni-kid/StudyMine.git
cd StudyMine
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start LM Studio
- Open **LM Studio** on your PC
- Load any model (e.g. `qwen3-4b`, `gemma-3-4b`, `mistral`, `deepseek`)
- Go to the **Local Server** tab and click **Start Server**
- Default port: `1234`

> 💡 **Recommended**: Use a small, fast model like `qwen3-4b` or `gemma-3-4b` for best response times. Larger models (8B+) give richer answers but are slower.

### 5. Run the app
```bash
python app.py
```

Your browser will open automatically at `http://127.0.0.1:7860`

A splash screen will appear while the embedding model loads. It dismisses automatically when the model is ready — usually 10–30 seconds on first run.

---

## 📁 Project Structure
```
StudyMind/
├── modules/
│   ├── ai_engine.py       # LM Studio connection, prompting, is_lmstudio_online()
│   ├── pdf_reader.py      # PDF, DOCX, TXT, MD, PPTX, EPUB text extraction + chunking
│   ├── vector_store.py    # ChromaDB semantic search & indexing
│   ├── doc_library.py     # Multi-document library management & HTML rendering
│   ├── flashcards.py      # Flashcard generation (batched, up to 40)
│   ├── quiz.py            # MCQ generation — 3-strategy parser, batch loop, 40q support
│   ├── mindmap.py         # Radial mindmap — Canvas renderer, no iframe needed
│   └── __init__.py
├── data/                  # ChromaDB vector store + library metadata (JSON)
├── assets/                # Icons and images
├── app.py                 # Main Gradio app (all tabs, UI, splash screen)
├── requirements.txt       # Python dependencies
├── push_to_github.bat     # One-click GitHub push script (Windows)
├── CHANGELOG.md           # Full history of changes
└── README.md
```

---

## 📋 Requirements

```
gradio
chromadb
PyMuPDF
sentence-transformers
requests
python-docx
python-pptx
ebooklib
beautifulsoup4
```

Install all with:
```bash
pip install -r requirements.txt
```

---

## 🖥️ System Requirements

- **OS:** Windows 10/11 (Mac/Linux also supported)
- **Python:** 3.10 or higher
- **RAM:** 8GB minimum (16GB recommended for larger models)
- **GPU:** Optional but recommended for faster inference (NVIDIA with CUDA)
- **LM Studio:** Required — download at [lmstudio.ai](https://lmstudio.ai)

---

## 📌 Important Notes

- RK StudyMind runs **100% offline** — no internet required after first setup
- The embedding model (`all-MiniLM-L6-v2`, ~90MB) downloads automatically on first launch
- The `UNEXPECTED key: embeddings.position_ids` warning in the terminal is harmless — it's a known `sentence-transformers` quirk
- Scanned PDFs (image-based) are not supported — text-based PDFs only
- PowerPoint files extract text + speaker notes; images on slides are ignored
- DRM-protected EPUBs cannot be extracted
- Documents are persisted across sessions via `data/library.json`

---

## 🗺️ Changelog

### ✅ Version 1.1 — Current
- **6 file formats** — PDF, DOCX, TXT, MD, PPTX, EPUB all supported in Library
- **Chat UI** — Inter font, JetBrains Mono for code, timestamps, source badges, 3-dot typing indicator, proper bubble borders
- **Splash screen** — macOS-style spinner + segmented bar, dismisses when embedding model is actually ready (polls signal — not a hardcoded timer)
- **Quiz** — Up to 40 questions, batch generation, 3-strategy parser, running score
- **Mindmap** — Radial Canvas renderer, no external browser needed
- **LM Studio offline detection** — clear error bubbles before each generation attempt

### ✅ Version 1.0
- Multi-document library (PDF + DOCX)
- RAG-powered Q&A with semantic search
- Smart Quiz (MCQ with score)
- Flashcards with score system and results screen
- Interactive Mindmap generator

---

## 👤 Author

**RoniKid**

---

> Built with 🧠 and Python. Powered by local AI.
