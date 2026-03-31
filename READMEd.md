# 🧠 RK StudyMind
> Your Personal AI-Powered Study Companion — Built by RoniKid

RK StudyMind is a fully offline AI study app that lets you chat with your lecture notes, generate flashcards with a score system, take multiple choice quizzes, auto-summarize documents, generate interactive mindmaps, and more — all running locally on your PC using LM Studio. No internet, no API keys, no subscriptions.

---

## ✨ Features — v1.0

| Feature | Description |
|---|---|
| 📚 **Document Library** | Upload multiple PDFs and DOCX files at once. Switch between documents or query across all of them. |
| 💬 **Document Q&A (RAG)** | Ask questions and get answers from your documents using Retrieval Augmented Generation — finds relevant content from anywhere in the document. |
| 📝 **Smart Quiz** | Auto-generates multiple choice questions (A/B/C/D) with instant feedback, explanations, and a final score screen. |
| ✍️ **Auto Summary** | One-click Quick Summary (5 bullet points) or Detailed Summary with full structured breakdown. Select which documents to summarize. |
| 🃏 **Flashcards** | Generates up to 40 Q&A study cards using batched generation. One card at a time with ✅❌ score tracking and a results screen. |
| 🗺️ **Mindmap** | AI generates a structured topic map rendered as an interactive visual mindmap in your browser using Markmap.js. |
| 🔍 **Semantic Search** | ChromaDB + sentence-transformers power meaning-based search across all your documents. |

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| UI | Gradio 6.0+ (Python) |
| AI Brain | LM Studio (100% Offline, any local model) |
| Document Reading | PyMuPDF (PDF) + python-docx (DOCX) |
| Semantic Search | ChromaDB + sentence-transformers |
| Mindmap Rendering | Markmap.js (browser-based) |
| Embeddings | all-MiniLM-L6-v2 (local, auto-downloaded once) |

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
- Load any model (e.g. `gemma-3-4b`, `nemotron-3-nano`, `mistral`, `deepseek`)
- Go to the **Local Server** tab and click **Start Server**
- Default port: `1234`

### 5. Run the app
```bash
python app.py
```

Your browser will open automatically at `http://127.0.0.1:7860`

---

## 📁 Project Structure

```
StudyMind/
├── modules/
│   ├── ai_engine.py       # LM Studio connection & prompting
│   ├── pdf_reader.py      # PDF & DOCX text extraction and chunking
│   ├── vector_store.py    # ChromaDB semantic search & indexing
│   ├── doc_library.py     # Multi-document library management
│   ├── flashcards.py      # Flashcard generation (batched, up to 40)
│   ├── quiz.py            # Multiple choice quiz generation & parsing
│   ├── summary.py         # Quick & detailed summary generation
│   ├── mindmap.py         # Mindmap markdown generation & HTML rendering
│   └── __init__.py
├── data/                  # ChromaDB vector store + mindmap HTML files
├── assets/                # Icons and images
├── app.py                 # Main Gradio app (all tabs and UI)
├── requirements.txt       # Python dependencies
├── push_to_github.bat     # One-click GitHub push script (Windows)
└── README.md
```

---

## 📋 Requirements

```
gradio
anthropic
chromadb
PyMuPDF
sentence-transformers
requests
python-docx
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
- Any model loaded in LM Studio works — larger models give better quality answers
- Scanned PDFs (image-based) are not supported — text-based PDFs only
- Documents are stored in memory per session — re-upload after restarting the app

---

## 🗺️ Roadmap

### ✅ Version 1.0 — Complete
- Multi-document library (PDF + DOCX)
- RAG-powered Q&A with semantic search
- Smart Quiz (MCQ with score)
- Auto Summary (Quick + Detailed)
- Flashcards with score system and results screen (up to 40 cards)
- Interactive Mindmap generator

### 🔜 Version 1.1 — Coming Soon
- Pomodoro Timer
- *(More features TBA)*

---

## 👤 Author

**RoniKid** 

---

> Built with 🧠 and Python. Powered by local AI.
