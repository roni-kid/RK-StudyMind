# 🧠 RK StudyMind
> Your Personal AI-Powered Study Companion — Built by RoniKid

RK StudyMind is a fully offline AI study app that lets you chat with your lecture notes and textbooks, generate flashcards, search semantically across documents, and more — all running locally on your PC using LM Studio.

---

## ✨ Features
- 📄 **PDF Reader** — Upload and extract text from any lecture note or textbook
- 💬 **Document Q&A** — Ask questions and get answers from your uploaded PDFs
- 🃏 **Flashcard Generation** — Auto-generate study cards *(coming soon)*
- 🔍 **Semantic Search** — Search by meaning, not just keywords *(coming soon)*
- 🗺️ **Mindmap Generator** — Visual topic maps *(coming soon)*

---

## 🛠️ Tech Stack
| Layer | Tool |
|---|---|
| UI | Gradio (Python) |
| AI Brain | LM Studio (100% Offline) |
| PDF Reading | PyMuPDF |
| Vector Search | ChromaDB |
| Embeddings | sentence-transformers |

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/StudyMind.git
cd StudyMind
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
- Open LM Studio on your PC
- Load any model (e.g. gemma-3-4b, deepseek, mistral)
- Start the local server (port 1234)

### 5. Run the app
```bash
python app.py
```

Open your browser at `http://127.0.0.1:7860`

---

## 📁 Project Structure
```
StudyMind/
├── modules/
│   ├── pdf_reader.py     # PDF text extraction & chunking
│   ├── ai_engine.py      # LM Studio connection & prompting
│   └── __init__.py
├── uploads/              # Drop your PDFs here
├── data/                 # ChromaDB vector store
├── assets/               # Icons and images
├── app.py                # Main Gradio app
├── requirements.txt      # Python dependencies
└── README.md
```

---

## 👤 Author
**RoniKid** 

---

## 📌 Note
This app requires **LM Studio** installed locally with a model loaded and the server running. It does not require an internet connection or any API keys.