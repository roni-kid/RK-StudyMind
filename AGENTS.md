# StudyMind — Codex Project Instructions

## Who You Are Working With
RoniKid — Level 100 Computer Engineering student. Building StudyMind: a locally-run, AI-powered study assistant app. Direct, no hand-holding, dark aesthetic, values clean functional code.

---

## Project Overview

**Stack:** Python · Gradio · ChromaDB · LM Studio (local LLM, port 1234) · sentence-transformers
**Supported formats:** PDF, DOCX, TXT, MD, PPTX, EPUB, and source code files (.py .js .ts .c .cpp .java .html .css)
**Current version:** v1.3 (released)

**Key paths:**
| File | Purpose |
|------|---------|
| `C:\Users\rocks\Documents\CLaude\StudyMind\app.py` | Main Gradio app — corrected from `Codex\StudyMind`, which is not where the codebase lives |
| `modules\quiz.py` | Quiz generation logic |
| `modules\flashcards.py` | Flashcard logic |
| `modules\mindmap.py` | Mindmap logic |
| `C:\Users\rocks\Documents\Codex\Memory\memory.md` | Session memory file |
| `CHANGELOG.md` | Project changelog (maintain actively) |

**Tab status (v1.3):** Home · Library · Q&A · Quiz · Flashcards · Mindmap · Coding · Audio — all complete

---

## 🐛 Debugging Rules

1. **Read before diagnosing.** Always fetch the exact current file via Filesystem MCP before forming any opinion about a bug. Never assume file state from context.
2. **State the bug clearly first** — what's wrong, why it's wrong, where it lives — before touching any code.
3. **Know the Gradio traps:**
   - `onclick`, `onmouseover`, `onmouseout` in `gr.HTML()` are stripped and rendered as visible text — interactivity must be pure CSS or Gradio's own event system
   - Quiz answer buttons must be `visible=True` with CSS off-screen (`top: -9999px`); JS must use `getElementById` + `.querySelector('button')`, not `querySelectorAll`
   - `CheckboxGroup` values go stale across sessions — `sanitize_docs()` must guard all entry points
4. **Know the Python traps:** Backslashes inside nested f-strings cause `SyntaxError` — always avoid.
5. **Check LM Studio first** when generation bugs appear — verify `is_lmstudio_online()` before assuming the logic is broken.
6. **No silent ChromaDB errors.** Any bare `except: pass` is a bug. All errors must surface to the UI or logs.

---

## ✏️ Editing Rules

1. **Always use `view_range`** to read the exact target lines before and after any edit. No full-file reads or writes unless explicitly requested. Stale context breaks indentation and line numbers.
2. **Surgical edits only** — use str_replace style targeting. No full rewrites unless the scope explicitly demands it.
3. **Preserve existing patterns** — naming conventions, Gradio component structure, CSS variable names.
4. **Changelog discipline** — after any meaningful change, append an entry to `CHANGELOG.md` with version, date, and what changed.
5. **Scope edits to one tab per session** — don't touch multiple tabs in one pass unless explicitly asked.

---

## 🔍 Vulnerability Scan Checklist

Run this mentally on any code review or audit request:

- [ ] Bare `except: pass` anywhere → must log or surface
- [ ] ChromaDB calls without error handling → silent crash risk
- [ ] Generation entry points missing `is_lmstudio_online()` pre-flight → must add
- [ ] `CheckboxGroup` selectors not covered by `sanitize_docs()` → stale state bug
- [ ] Upload handlers missing file-type validation → bad input risk
- [ ] UI state that survives Gradio restarts without sanitization → stale browser crash risk
- [ ] Nested f-strings with backslashes → `SyntaxError`

---

## 🗺️ Planning Rules

1. **Check `V1_improvements.md` and `CHANGELOG.md` before proposing anything** — don't plan work that's already done or already scoped.
2. **Roadmap awareness:**
   - v1.1: Complete across all tabs
   - v1.2: NotebookLM aesthetic overhaul — this is the active target
   - Remaining ~28% of overall app to complete after v1.2
3. **Propose tab-by-tab.** State which tab is in scope, what changes are planned, and what is explicitly out of scope.
4. **Local LLM constraints are real** — batch generation is capped at 3 questions/call, context window capped at 6,000 words. Don't plan features that violate these limits without flagging them.
5. **End-of-session:** Update `memory.md` with what changed and what's next.

---

## General Behavior

- Be direct. State what's wrong, what to fix, and the exact value. "Improve spacing" is useless.
- No excessive confirmation loops — read the file, form a plan, present it once, execute on approval.
- When in doubt about file state: read it. Always.
- `summary.py` still exists in modules but is dead code — flag it if encountered, don't use it.
