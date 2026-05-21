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

### Dark Theme
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

## 🔢 Math Rendering Strategy

> "Translate fractions, equations and expressions from the LLM response so the LLM has less burden."

The Q&A pipeline applies **two passes** inside `format_ai_message()` in `app.py`:

| Pass | Function | What it handles |
|---|---|---|
| 1 | `render_math_html()` | Explicit LaTeX: `$x^2$`, `\[...\]`, `\(...\)`, `\frac{}{}`, `\lambda` |
| 2 | `render_plain_math_html()` | Plain-text math the LLM writes naturally — no delimiters needed |

### Pass 2 — patterns handled

| LLM writes | Renders as |
|---|---|
| `x^2`, `r^3`, `10^-4` | x², r³, 10⁻⁴ (unicode superscripts) |
| `v_0`, `CO_2` | v₀, CO₂ (unicode subscripts) |
| `sqrt(b^2 - 4ac)` | √(b² - 4ac) |
| `1/2`, `3/4`, `2/3`, `1/8` | ½, ¾, ⅔, ⅛ (unicode fraction chars) |
| `>=`, `<=`, `!=`, `~=` | ≥, ≤, ≠, ≈ |
| `->`, `<->`, `=>`, `<-` | →, ↔, ⇒, ← |
| `+-`, `+/-` | ± |
| `45 deg`, `180 degrees` | 45°, 180° |
| `3 x 4` (digits flanking x) | 3×4 |
| `theta`, `pi`, `lambda`, `sigma` ... | θ, π, λ, σ ... (math context only) |
| `infinity`, `inf` | ∞ (math context only) |

### LLM system prompt (ai_engine.py)
`QA_SYSTEM_PROMPT` now instructs the LLM to:
- Write math naturally: `x^2`, `sqrt(x)`, `1/2`, `>=`, `->`, spell out Greek letter names
- **NOT** use LaTeX dollar signs or backslash commands

### Processing order inside render_plain_math_html
1. Unicode fractions (`1/2` → ½)
2. `sqrt(...)` — runs **before** powers so inner args are clean
3. Powers / superscripts (`x^2` → x²)
4. Subscripts (`v_0` → v₀)
5. Comparison & logic operators (`>=` → ≥, `->` → →)
6. Degree symbol (`45 deg` → 45°)
7. Multiplication sign (`3 x 4` → 3×4)
8. Named constants in math context (`pi` → π)

---

## 🏗️ Architecture Notes

- **Session state** is a `gr.State(dict)` — all library, chat, quiz, and flashcard data lives in it per browser session.
- **No global mutable state** for user data — all functions take `session_state` as first arg.
- **LM Studio** is the AI backend (local server, port 1234). Check `is_lmstudio_online()` before any AI call.
- **Embedding model** (`all-MiniLM-L6-v2`) loads in background at startup via `preload_model_background()`.
- **ChromaDB** is used for per-session semantic vector search. Sessions are cleaned up on new page load.
- **No splash screen** — the app opens directly. The embedding model loads silently in the background.

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
| v1.1 | 🔄 In Progress | Chat UI, 6 file formats, difficulty levels, session state, export, analytics, plain-text math, dark-only, adaptive chunking |
| v1.2 | 📋 Planned | NotebookLM-style look |

---

## ❌ Removed Features

These were explicitly removed — do NOT re-add unless the user asks:

| Feature | Why removed |
|---|---|
| 🎤 Speech-to-Text (Speak button) | Broken — Gradio 5/6 iframe sandboxing blocked `onclick` from reaching top-window JS |
| ☀️ Light Theme toggle | Removed per user request — app is dark-only |
| 👻 Splash Screen | Removed per user request — app opens directly |

---

*Last updated: 2026-05-08*
