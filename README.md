# 🧠 RK StudyMind
> Your Personal AI-Powered Study Companion — Built by RoniKid

RK StudyMind is a fully offline AI study app that lets you chat with your lecture notes, generate flashcards with score tracking, take multiple choice quizzes, generate structured mindmaps, create grounded audio overviews, and analyze code — all running locally on your PC using LM Studio. No internet, no API keys, no subscriptions.

---

## ✨ Features — v1.3

| Feature | Description |
|---|---|
| 📚 **Document Library** | Upload PDFs, DOCX, TXT, Markdown, PowerPoint (.pptx), EPUB, and source code files. Styled document cards show file type, page/slide/chapter count, word count, chunk count, and adaptive chunking strategy tag. Large documents are auto-split into parts. Library state persists across sessions. |
| 💬 **Document Q&A (RAG)** | Chat with your documents using Retrieval Augmented Generation. Inter-font chat bubbles with right-aligned user messages, left-aligned AI responses with 🧠 avatar, timestamps, source badges, and an animated 3-dot typing indicator. Search scope toggles between active document and all documents. Balanced context selection reduces first-chunk bias. |
| 📝 **Smart Quiz** | Auto-generates up to 30 multiple choice questions (A–D) with a progress bar, live score pill, inline answer selection, and a final results screen. Batch generation with a 3-strategy parser (numbered / markdown table / loose) handles any model output format. Context limits adapt to the detected model's context window. |
| 🃏 **Flashcards** | Generates up to 30 Q&A study cards. One card at a time with ✅ / ❌ score tracking, a live score bar, and a session results screen. Deduplication pass removes repeat cards. Hard cards only mode uses session history to surface your weakest cards. |
| 🗺️ **Mindmap** | AI generates a structured left-to-right study tree with root panel, stacked branch lanes, and readable child rows — rendered directly in the app. Controls: Expand All, Collapse All, Fit, zoom (+/−), and in-widget HTML export. Concept-clustering algorithm groups related ideas automatically. |
| 🎙️ **Audio Overview** | Generates a grounded two-host study transcript using staged LM Studio prompting over retrieved document chunks. Synthesizes local audio when Piper TTS voices are configured. Exports transcript as Markdown and optionally as MP3/WAV — no cloud services involved. |
| ⚡ **Coding** | Upload source code files through the Library and analyze them in two modes. Explain mode renders a structured six-section breakdown (Summary, Functions, Classes, Logic Flow, Issues, Test Suggestions). Ask AI mode answers code-specific questions with recent chat history and smart context truncation. |
| 🔍 **Semantic Search** | ChromaDB powers meaning-based search across all your documents. Embeddings route through LM Studio's `/v1/embeddings` first, falling back automatically to local `sentence-transformers` if LM Studio is offline. Background indexing keeps the UI responsive during large uploads. |
| 🖨️ **Scanned PDF OCR** | Scanned and image-only PDFs are automatically detected page-by-page and processed with Tesseract OCR at 216 DPI with contrast enhancement and sharpening. Auto-detects Tesseract at 4 common Windows install paths — no PATH config needed. |
| ➗ **Math Rendering** | Two-pass math pipeline: Pass 1 handles LaTeX delimiters (`$...$`, `\[...\]`, `\(...\)`); Pass 2 catches plain-text patterns the LLM writes naturally (`x^2` → x², `sqrt(x)` → √(x), `1/2` → ½, `->` → →, `pi` → π, etc.). |
| 📊 **Adaptive Chunking** | On startup, detects the loaded LM Studio model and infers its context window. Each uploaded document is chunked at the optimal token size across five tiers (TINY → XLARGE) based on word count. Documents too large for one session part are automatically split. |
| 📤 **Export** | Export quiz results as a Markdown study report and flashcards as an Anki-compatible CSV — all from inside the app. Mindmaps export as standalone HTML files. Audio transcripts export as Markdown. |

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| UI | Gradio 6.9.0 (Python) |
| AI Brain | LM Studio (100% Offline, any local model) — port `1234` |
| Document Reading | PyMuPDF 1.25.5 (PDF) · python-docx (DOCX) · python-pptx (PPTX) · ebooklib + BeautifulSoup (EPUB) · built-in (TXT, MD, code files) |
| OCR (Scanned PDFs) | Tesseract OCR · pytesseract · Pillow — auto-detected on Windows, no PATH config needed; 216 DPI + contrast boost |
| Semantic Search | ChromaDB 1.5.5 — dual-mode embeddings (LM Studio `/v1/embeddings` → sentence-transformers fallback) |
| Adaptive Chunking | `adaptive_chunking.py` — model detection, 5-tier chunk sizing, session limit enforcement |
| File Profiling | `file_profiler.py` — pre-scan word count estimation, smart split/stretch logic for large documents |
| Structured Generation | `structured_generation.py` — JSON extraction, deduplication, result envelope shared by Quiz, Flashcards, Mindmap, Audio |
| Mindmap Rendering | `mindmap.py` — custom dark structured tree renderer, concept clustering, HTML5, no external dependencies |
| Math Rendering | `math_renderer.py` — LaTeX-to-Unicode rendering for chat, quiz, and flashcards |
| Audio Overview | `audio_overview.py` — staged LM Studio JSON script generation, Piper TTS routing, stdlib WAV assembly, optional ffmpeg MP3 export |
| Code Viewer | `code_viewer.py` — VS Code-style Pygments syntax highlighting with monospace fallback |
| Embeddings | all-MiniLM-L6-v2 (local, auto-downloaded once on first run) |
| Fonts | Inter (chat UI) · JetBrains Mono (code blocks) via Google Fonts |

---

## 📂 Supported File Types

| Extension | Type | Extraction Method |
|---|---|---|
| `.pdf` | PDF (text-based) | PyMuPDF — page by page |
| `.pdf` | PDF (scanned/image) | PyMuPDF renders page → Tesseract OCR at 216 DPI — auto-detected per page |
| `.docx` | Word Document | python-docx — paragraphs + tables |
| `.pptx` | PowerPoint | python-pptx — slide text + tables + speaker notes |
| `.epub` | Ebook | ebooklib + BeautifulSoup — chapter by chapter |
| `.md` | Markdown | Built-in — strips `#`, `**`, `` ` `` markers before indexing |
| `.txt` | Plain Text | Built-in — auto encoding fallback (utf-8 → latin-1 → cp1252) |
| `.py`, `.js`, `.ts`, `.c`, `.cpp`, `.java`, `.html`, `.css` | Source Code | Built-in — preserves code text and indentation for the ⚡ Coding tab |

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

### 4. (Optional) Enable Scanned PDF Support

Skip this if you only use text-based PDFs. If you have scanned lecture notes or image-only PDFs:

**a. Install Tesseract OCR** (one-time, ~50 MB)
- Download the Windows installer: [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- Run the `.exe` — you don't need to check "Add to PATH". StudyMind auto-detects Tesseract at these locations:
  - `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
  - `C:\Users\<you>\AppData\Local\Tesseract-OCR\tesseract.exe`
  - `C:\tools\tesseract\tesseract.exe`

**b. Python packages** (already in `requirements.txt` — no extra step needed)
```bash
# Already included — just confirm they're installed:
pip install pytesseract Pillow
```

> 💡 After Tesseract is installed, restart the app. Scanned PDFs are automatically detected page-by-page — no settings to change.

### 5. (Optional) Enable Audio Overview Voice Synthesis

The 🎙️ Audio tab always generates a transcript. To synthesize playable audio, install Piper separately and provide two local `.onnx` voices. You can either paste voice paths in the Audio tab or set environment variables before launching StudyMind:

```bash
set STUDYMIND_PIPER_BIN=C:\path\to\piper.exe
set STUDYMIND_PIPER_VOICE_A=C:\path\to\voice_a.onnx
set STUDYMIND_PIPER_VOICE_B=C:\path\to\voice_b.onnx
```

For MP3 export, install `ffmpeg` and make sure it is on PATH. Without ffmpeg, StudyMind keeps the generated `.wav` file.

### 6. Start LM Studio
- Open **LM Studio** on your PC
- Load any model (e.g. `qwen3-4b`, `gemma-3-4b`, `mistral`, `deepseek`)
- Go to the **Local Server** tab and click **Start Server**
- Default port: `1234`

> 💡 **Recommended**: Use a small, fast model like `qwen3-4b` or `gemma-3-4b` for best response times. Larger models (8B+) give richer answers but are slower.
>
> 💡 **Adaptive detection**: On startup, StudyMind queries LM Studio to detect the loaded model and infers its context window automatically. Press **🔄 Refresh** on the Home tab any time you swap models.

### 7. Run the app
```bash
python app.py
```

Your browser will open automatically at `http://127.0.0.1:7860`

---

## 📁 Project Structure

```
StudyMind/
├── app.py                      # Main Gradio app — all 8 tabs, UI logic, render functions
├── adaptive_chunking.py        # Model detection, 5-tier chunk sizing, session limit enforcement
├── ai_engine.py                # LM Studio HTTP client, temperature control, merged-context prompting
├── audio_overview.py           # Audio tab — staged two-host transcript generation + optional Piper TTS
├── code_viewer.py              # VS Code-style Pygments syntax highlighting for code previews
├── coding_agent.py             # Coding tab — Explain + Ask AI over Library-sourced code files
├── doc_library.py              # Multi-document library — HTML cards, JSON persistence
├── engine_manager.py           # LM Studio router — single-request status check
├── exporters.py                # CSV and study report export helpers
├── file_profiler.py            # Upload pre-scan — word count estimation, split/stretch logic
├── flashcards.py               # Batched flashcard generation — deduplication, adaptive context, low-temp
├── math_renderer.py            # Two-pass LaTeX-to-Unicode math rendering
├── mindmap.py                  # Structured study tree renderer — concept clustering, adaptive context
├── pdf_reader.py               # PDF, DOCX, TXT, MD, PPTX, EPUB, code file extraction + OCR
├── quiz.py                     # MCQ generation — 3-strategy parser, adaptive context, low-temp calls
├── structured_generation.py    # Shared JSON extraction, deduplication, result envelope
├── study_context.py            # Balanced context builder — auto-detects adaptive max_words
├── study_history.py            # Quiz session history and flashcard performance tracking
├── vector_store.py             # ChromaDB — dual-mode embeddings, background indexing, thread-safe sessions
├── _splash_patch.py            # Startup splash screen CSS + JS (injected at launch)
├── data/                       # ChromaDB vector store + library metadata (JSON) + config.json
├── exports/                    # Quiz reports, flashcard CSVs, mindmap HTMLs, audio transcripts
├── requirements.txt            # Pinned Python dependencies
├── Studymind.bat               # One-click app launcher (Windows)
├── push_to_github.bat          # One-click GitHub push script (Windows)
├── memory.md                   # Permanent project design decisions and rules
├── CHANGELOG.md                # Full session-by-session history of changes
└── README.md
```

---

## 📋 Requirements

```
gradio==6.9.0
chromadb==1.5.5
PyMuPDF==1.25.5
sentence-transformers==5.3.0
requests==2.32.5
python-docx==1.2.0
python-pptx==1.0.2
ebooklib==0.20
beautifulsoup4==4.14.3
pytesseract==0.3.13
Pillow==11.3.0
```

Install all with:
```bash
pip install -r requirements.txt
```

> ⚠️ Use `PyMuPDF==1.25.5` exactly. v1.27.x ships a broken `frontend` sub-package that crashes on startup.

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
- The embedding model (`all-MiniLM-L6-v2`, ~90MB) downloads automatically on first launch; subsequent startups use the local cache
- If LM Studio is running, embeddings route through it automatically (`/v1/embeddings`). If LM Studio is offline, the app falls back to local `sentence-transformers` — the Home tab shows which backend is active
- **Adaptive chunking** runs once at startup: the detected model name and context window appear on the Home tab status card. Pressing **🔄 Refresh** re-detects after a model swap in LM Studio
- Document uploads show a `[STRATEGY]` tag (TINY / SMALL / MEDIUM / LARGE / XLARGE) indicating the chunk size chosen for that document
- **Large documents** exceeding the per-document word cap are automatically split into numbered parts (e.g. `Lecture Notes [1/3].pdf`) and indexed separately — no data is lost
- **Session limits:** 150,000 words per document · 400,000 words total per session · 20 documents per session
- **Scanned PDFs** are supported via Tesseract OCR — see OCR setup above
- Text-based PDFs work with no extra setup; OCR only activates on pages with no extractable text
- PowerPoint files extract text + speaker notes; images on slides are ignored
- DRM-protected EPUBs cannot be extracted
- The `UNEXPECTED key: embeddings.position_ids` warning in the terminal is harmless — it's a known `sentence-transformers` quirk
- Library state (uploaded documents and metadata) **persists across sessions** via `data/library.json`. Raw document text is not stored — only chunks and metadata
- Audio Overview transcripts are generated through staged LM Studio prompts over retrieved chunks. Piper and ffmpeg are optional local tools for voice/audio export; if missing, the transcript still exports cleanly as Markdown

---

## 🗺️ Version History

### ✅ Version 1.3 — Current
- **Audio Overview tab** (`🎙️ Audio`) — selects a Library document, retrieves grounded chunks via semantic search, writes a validated two-host transcript with staged LM Studio prompting, and exports transcript plus optional Piper/ffmpeg audio
- **Coding tab** (`⚡ Coding`) — two modes: Explain (structured 6-section code breakdown rendered as HTML) and Ask AI (code Q&A with chat history and smart truncation). Supports `.py .js .ts .c .cpp .java .html .css` files uploaded via the Library
- **File Profiler** (`file_profiler.py`) — pre-scan estimates word count and image ratio before full extraction; smart split/stretch logic automatically partitions oversized documents into indexed parts
- **Structured Generation** (`structured_generation.py`) — shared JSON extraction, deduplication, and result envelope used across Quiz, Flashcards, Mindmap, and Audio modules

### ✅ Version 1.1
- **Adaptive chunking engine** — detects loaded LM Studio model at startup, infers context window, assigns per-document chunk strategy (TINY → XLARGE). Session and per-document word limits enforced at upload time
- **Dual-mode embedding backend** — embeddings route through LM Studio `/v1/embeddings` when available; automatic live fallback to `sentence-transformers`. Active backend shown on Home tab
- **Thread-safe background indexing** — ChromaDB embedding runs in a background thread so the Gradio UI stays responsive during large document uploads
- **Two-pass math renderer** — Pass 1: LaTeX delimiters; Pass 2: plain-text patterns (`x^2`, `sqrt(x)`, `1/2`, `->`, `pi`, `theta`, `>=`, etc.)
- **Mindmap overhaul** — replaced radial canvas with a dark structured left-to-right study tree: root panel, stacked branch lanes, rectangular cards, readable child rows. New controls: Expand All, Collapse All, Fit, zoom, in-widget HTML export
- **Scanned PDF OCR** — upgraded to 3× render scale (~216 DPI), grayscale conversion, 1.4× contrast boost + sharpening, `--oem 3 --psm 6` Tesseract config. Auto-detects Tesseract at 4 Windows paths
- **Temperature control** — Q&A uses `temperature=0.7`; all structured generation (Quiz, Flashcards, Mindmap) uses `temperature=0.2` for consistent output
- **Library persistence** — snapshot saves metadata + chunks but not raw text, keeping `data/library.json` small regardless of document size
- **6 file formats** — PDF, DOCX, TXT, MD, PPTX, EPUB
- **Chat UI** — Inter font, JetBrains Mono for code, timestamps, source badges, 3-dot typing indicator, styled scrollbar
- **Quiz** — up to 30 questions, batch generation (BATCH_SIZE=3), 3-strategy parser (numbered / table / loose), adaptive context limit, running score
- **Flashcards** — up to 30 cards, deduplication, adaptive context limit, session results screen, Hard Cards Only mode
- **Export** — quiz study report (Markdown) + flashcards CSV (Anki-compatible)
- **LM Studio offline detection** — clear error message before every generation attempt

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
