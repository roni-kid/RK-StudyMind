# 🧠 RK StudyMind — Project Memory

> This file captures permanent design decisions, preferences, and rules for this project.
> Claude reads this before making any UI or feature changes.

---

## 👤 Owner

**RoniKid** — solo developer, building a personal offline AI study tool.

---

## 🎨 UI Design Philosophy

### Core Rule: **Simplicity First**
> "I prefer simplicity of UI and appearance for this project."

- Less is more. Every component on screen must earn its place.
- If something can be hidden until needed, it should be.
- Avoid visual clutter — no stacking too many buttons in a row, no visible empty widgets.
- The app should feel calm and focused, not overwhelming.

### Theme
| Property | Value |
|---|---|
| Background | `#060b18` (near-black) |
| Surface | `#1e293b` (dark slate) |
| Border | `#334155` |
| Primary accent | `#4F46E5` (indigo) |
| Text primary | `#f1f5f9` |
| Text muted | `#64748b` |
| Success | `#10b981` |
| Danger | `#ef4444` |

### Typography
- UI text: `'Segoe UI', sans-serif`
- Chat text: `'Inter', sans-serif` (loaded via Google Fonts)
- Code blocks: `'JetBrains Mono', monospace`

---

## 📐 Layout Rules

### Tabs
- No `gr.Markdown("### Tab Title")` headers inside tabs — tab label is enough.
- Keep the first visible element in each tab as the most important action.

### Buttons
- Use short, clear labels. Avoid long phrases like "Didn't Remember" — use "Missed".
- Avoid "Previous" when "Prev" fits. Avoid "Study Again" when "Again" fits.
- Secondary/utility buttons must live inside a `gr.Accordion(open=False)`.
- Never show more than 5 buttons in a single `gr.Row()`.

### Accordions
- Label format: emoji + short noun phrase. e.g. `"📋 After Quiz"`, `"📋 More Options"`
- Always `open=False` by default.
- Never use `"⚙️ More Options"` — too generic. Use a descriptive label.
- The `gr.File` download widget goes inside the accordion, not in the main view.

### File Download Widgets
- Never show a `gr.File` widget in the main layout — always inside an accordion.
- They appear empty when no file is generated, which is visually messy.

### Status Messages
- Use `gr.Textbox(interactive=False, lines=1)` for status — clean single line.
- Green/red HTML status strips are fine for Library and Q&A tabs.

---

## ✅ Feature Retention Rule

> "Do not take away newly added functionalities."

All features must be preserved. Simplification only affects **where** things appear and **how they look**, never **whether they work**.

### Quiz tab — must always have:
- Document selector
- Questions slider + Difficulty radio + Generate button
- Quiz HTML display (progress bar, options, score, results)
- Hidden A/B/C/D + Submit/Next/Restart buttons (for JS triggers)
- `"📋 After Quiz"` accordion containing: Retry Wrong, Study Missed Topics, Export Report, File widget, Analytics

### Flashcard tab — must always have:
- Document selector
- Cards slider + Difficulty radio + Generate button
- Card HTML display (question/answer card, score bar)
- Prev / Reveal / Got It / Missed / Again buttons
- `"📋 More Options"` accordion containing: Study Missed, Hard Cards Only, Export CSV, File widget

---

## 🏗️ Architecture Notes

- **Session state** is a `gr.State(dict)` — all library, chat, quiz, and flashcard data lives in it per browser session.
- **No global mutable state** for user data — all functions take `session_state` as first arg.
- **LM Studio** is the AI backend (local server, port 1234). Check `is_lmstudio_online()` before any AI call.
- **Embedding model** (`all-MiniLM-L6-v2`) loads in background at startup. Splash screen waits for it via `#rk-model-signal` polling.
- **ChromaDB** is used for per-session semantic vector search. Sessions are cleaned up on new page load.

---

## 📁 Supported File Types

`.pdf` · `.docx` · `.txt` · `.md` · `.pptx` · `.epub`

---

## 🤖 Recommended Models

| Use case | Model |
|---|---|
| Best quality | `qwen3-8b` or larger |
| Best speed | `qwen3-4b`, `gemma-3-4b`, `nemotron-nano-3b` |
| Avoid for Q&A | Models >8B unless GPU is available |

> The timeout issue seen with Qwen3 8B is a model speed problem, not a code bug.
> Switch to a smaller/faster model in LM Studio if responses time out.

---

## 📝 Changelog Reference

Full history in `CHANGELOG.md`. Summary of current version:

| Version | Status | Key Features |
|---|---|---|
| v1.0 | ✅ Done | PDF+DOCX library, RAG Q&A, Quiz, Flashcards, Mindmap |
| v1.1 | 🔄 In Progress | Chat UI upgrade, 6 file formats, difficulty levels, session state, splash screen, export, analytics |
| v1.2 | 📋 Planned | Loading screen improvements, NotebookLM-style look |

---

*Last updated: 2026-04-09*
