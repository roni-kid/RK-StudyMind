# 🧠 RK StudyMind — Changelog

> All notable changes to this project are documented here.
> Format: `[Date] | File(s) Changed | What Changed | Why`
> Order: **Newest first**

---

## Session Log

### [2026-05-29] — Audio Overview MVP

**Summary:** Added a native `🎙️ Audio` tab that turns a selected Library document into a grounded two-host study transcript, with optional local Piper synthesis and MP3/WAV export.

| File | Change | Reason |
|---|---|---|
| `modules/audio_overview.py` | **New module** — staged outline + dialogue generation, strict JSON validation/repair, transcript export, Piper voice routing, WAV assembly, and optional ffmpeg MP3 conversion | Adds NotebookLM-style audio overview behavior without duplicating StudyMind's retrieval stack |
| `modules/ai_engine.py` | Added optional `max_tokens` parameter to `ask_lmstudio()` | Audio scripts need a larger structured response budget while preserving existing defaults |
| `app.py` | Added `🎙️ Audio` tab, Library document selector sync, retrieval-backed context building, transcript preview, audio player, and transcript/audio downloads | Integrates the feature into the existing Gradio workflow |
| `tests/test_structured_generation.py` | Added audio overview validation and WAV assembly tests | Proves speaker routing repair and dependency-free audio stitching behavior |
| `README.md` | Documented the Audio Overview feature, optional Piper/ffmpeg setup, and new module | Keep user-facing docs aligned with the visible app surface |

**Implementation note:** Piper and ffmpeg are optional local tools. If they are missing, StudyMind still generates and exports the transcript instead of failing the whole workflow.

### [2026-05-25] — Dead Code Removal Pass

| File | Change | Reason |
|---|---|---|
| `app.py` | Removed stale imports, an unused text-sanitizer helper, and an unused document-info helper; simplified Home refresh to the LM Studio-only path | Trim app-layer dead code left behind by earlier engine/theme and math-renderer changes |
| `modules/engine_manager.py` | Removed unused mode/theme config plumbing and kept only the active LM Studio ask/status helpers | The app no longer exposes engine-mode switching or theme persistence through this module |
| `modules/quiz.py` + `modules/flashcards.py` + `modules/mindmap.py` | Removed unused compatibility wrapper functions that were no longer called by the app | Keep generation modules aligned with the live Gradio surface |
| `modules/vector_store.py` | Removed the unused `is_model_ready()` helper | The app no longer reads this preload status directly |
| `modules/math_renderer.py` | Removed the dormant plain-text second-pass renderer and kept the active LaTeX rendering path only | The current app uses only the LaTeX rendering path, so the extra pass was dead code |
| `modules/execution_sandbox.py` + `diagnose.py` + `patch_format_header.py` | Deleted detached sandbox/debug/one-shot patch files that are no longer used anywhere in the app | Remove non-functional leftovers from older Coding Agent and repair work |
| `README.md` | Updated module descriptions to match the trimmed codebase | Keep repo documentation aligned with the current files |

### [2026-05-25] — Quiz And Flashcard Session Caps

| File | Change | Reason |
|---|---|---|
| `app.py` | Reduced Quiz and Flashcards slider maximums from 40 to 30 and clamped handler inputs to the same caps | Keep the UI and app-layer requests aligned with the new session limit |
| `modules/quiz.py` | Capped generated quiz requests at 30 questions | Enforce the new quiz maximum even if a larger value bypasses the UI |
| `modules/flashcards.py` | Capped generated flashcard requests at 30 cards | Enforce the new flashcard maximum even if a larger value bypasses the UI |
| `README.md` | Updated quiz and flashcard feature descriptions from 40 to 30 | Keep visible documentation accurate |

### [2026-05-21] — Coding Tab Scope Reduction

**Summary:** Renamed `⚡ Coding Agent` to `⚡ Coding` and reduced the feature to two modes only: **Explain** and **Ask AI**.

| File | Change | Reason |
|---|---|---|
| `app.py` | Removed Tutor and Agent mode buttons, columns, state objects, and callback wiring from the Coding tab | Current Coding feature should only expose Explain and Ask AI |
| `app.py` | Renamed the tab and header copy from `⚡ Coding Agent` to `⚡ Coding`; renamed the code Q&A mode button from `Q&A` to `Ask AI` | Match the requested product wording |
| `app.py` | Removed unused Tutor/Agent imports and helper functions from the app layer | Avoid dead UI paths and hidden callbacks |
| `modules/coding_agent.py` | Removed Tutor and Agent mode generation/rendering functions; updated module copy to describe Explain + Ask AI only | Keep the module aligned with the active UI surface |
| `README.md` | Updated feature list, supported file types, project structure, and version history for the simplified Coding tab | Keep user-facing docs current |

**Current Coding modes:**
- **Explain** — structured six-section code breakdown rendered by the app
- **Ask AI** — chat-style questions about the loaded Library code file

**Deferred:** Agent mode and its sandbox module are not exposed in the UI and will be reviewed later.

### [2026-05-21] — Coding Agent Tab (v1.3)

**Summary:** New `⚡ Coding Agent` tab with four modes — Explain, Q&A, Tutor, Agent — sharing one Library-sourced file picker, a styled button mode switcher, and a local execution sandbox that runs code across six languages with a 3-attempt auto-fix retry loop.

| File | Change | Reason |
|---|---|---|
| `modules/coding_agent.py` | **New module** — `explain_code()`, `qa_code()`, `tutor_code()`, `agent_code()`, `get_agent_explanation()`, `render_agent_failure_html()`, and HTML renderers for all four modes | Core logic for all Coding Agent modes |
| `modules/execution_sandbox.py` | **New module** — `run_code()` with subprocess runner, 10s hard timeout, per-language compile+run flows (Python, C, C++, JS, Java, HTML/CSS), `check_dependencies()`, `get_dependency_banner_html()`, `render_agent_output_html()` | Execution layer for Agent mode |
| `modules/code_viewer.py` | **New module** — `syntax_highlight_html()` with Pygments (fallback: styled `<pre>`), `get_language_from_filename()`, `render_code_empty_state()` | VS Code-style code previewer used in file picker |
| `app.py` | Added `⚡ Coding Agent` as Tab 6 with mode switcher, Library file picker, code preview panel, and per-mode input/output sections | New feature tab |
| `app.py` | Imported all three new modules at top of file | Make new modules available |
| `app.py` | `APP_VERSION` bumped `v1.2` → `v1.3` | New major feature |
| `app.py` | `CODE_EXTENSIONS` constant added (`{.py .js .ts .c .cpp .java .html .css}`) | Shared extension set used by Library and Coding Agent |
| `app.py` | `load_files()` extended to accept code file extensions; stores `code_text` field in library entry for code files; added code-file emoji icons | Library now handles code files |
| `app.py` | `get_code_file_dropdown_update()` helper added — filters library to code files only | Powers the Coding Agent file picker dropdown |
| `app.py` | `get_library_outputs()` extended to return `ca_file_selector` update (8 outputs → was 7) | Coding Agent file picker auto-updates on every Library change |
| `app.py` | `lib_sync`, `upload_btn.click` outputs, and all Library button wirings updated to include `ca_file_selector` | Keeps file picker in sync across all Library operations |
| `app.py` | Library tab info banner updated to list code formats | Users can see code files are supported |
| `app.py` | `file_input` updated to accept code extensions | Gradio file picker shows code files in the OS dialog |
| `app.py` | Added all Coding Agent handler functions: `ca_load_file_fn`, `ca_switch_mode`, `ca_switch_to_agent`, `ca_run_explain_fn`, `ca_run_qa_fn`, `ca_clear_qa_fn`, `ca_start_tutor_fn`, `ca_start_quiz_fn`, `ca_submit_answer_fn`, `ca_run_agent_fn`, `render_ca_empty_output` | Coding Agent UI logic |

**Feature detail — Four Modes:**
- **Explain** — LLM returns JSON with 6 sections (Summary, Functions, Classes, Logic Flow, Issues, Test Suggestions); app renders as structured HTML cards
- **Q&A** — Full code injected as context per message; chat history kept; last 3 turns sent to model
- **Tutor** — Phase 1: topic explanation; Phase 2: interactive quiz with `▶ Start Quiz` transition button
- **Agent** — Task description + language dropdown → LLM generates code → subprocess runs it (10s timeout) → AI explains result → auto-fix retry up to 3 attempts with attempt indicator

**Smart truncation:** Context limit read from LM Studio `/v1/models`; falls back to 2048 tokens. Files that exceed the budget have their middle section condensed with a visible truncation banner.

**Security:** Agent mode shows a one-time warning. Code runs locally. Docker isolation deferred to v2.0.

---

### [2026-05-14] — OCR: Scanned PDF Support

| File | Change | Reason |
|---|---|---|
| `modules/pdf_reader.py` | Added `_setup_tesseract()` — auto-detects Tesseract at 4 common Windows install paths before falling back to PATH | Tesseract installed via the Windows GUI is not on PATH by default; auto-detection makes OCR work without manual config |
| `modules/pdf_reader.py` | `_ocr_page()` now calls `_setup_tesseract()`, upgrades render scale 2× → 3× (~216 DPI), converts to grayscale, applies contrast boost (1.4×) + sharpening, passes `--oem 3 --psm 6` to Tesseract | Higher DPI + preprocessing significantly improves accuracy on lecture slide scans |
| `modules/pdf_reader.py` | `_missing_ocr_dependencies()` refactored to call `_setup_tesseract()` — eliminates duplicate detection logic | Single source of truth for Tesseract availability |
| `modules/pdf_reader.py` | Error message updated with exact download URL and pip install steps | Previous message had no link; new message gives the Windows installer URL and exact commands |
| `requirements.txt` | `pytesseract==0.3.13` and `Pillow==11.3.0` already present — no change | Python OCR packages were already correct |

**One-time user setup required:** Download Tesseract from https://github.com/UB-Mannheim/tesseract/wiki and run the Windows installer. The app auto-detects it after that.

---

### [2026-05-14] — Mindmap Structured Tree UI Overhaul

| File | Change | Reason |
|---|---|---|
| `modules/mindmap.py` | Replaced the radial SVG node map with a dark structured left-to-right study tree using root panel, stacked branch lanes, rectangular cards, readable child rows, and restrained branch accents | Makes Mindmaps easier to scan and study without pan/zoom fiddling |
| `modules/mindmap.py` | Updated Mindmap generation prompt to request 4-8 major branches, meaningful child phrases, and optional branch summaries | Produces richer, more readable study structures instead of cramped 3-word bubbles |
| `modules/mindmap.py` | Hardened Markdown cleanup and parsing for summaries, fallback branches, empty children, and weak model output | Keeps bad or partial LLM output from breaking the renderer |
| `modules/mindmap.py` | Added tree-native controls for Expand All, Collapse All, Fit, zoom, and in-widget HTML export | Aligns controls with review workflows while preserving export parity |
| `app.py` | Updated Mindmap UI copy from radial/drag language to structured-tree language | Keeps the app text aligned with the new renderer |

---

### Re-check — Additional Fixes (v1.1)
**Date:** 2026-05-09

| File | Issue | Fix |
|------|-------|-----|
| `app.py` | `entry` dict stored full raw text in memory (`text: raw`) even after snapshot was fixed to omit it — ~900 KB per 150K-word doc sitting in RAM for the entire session | Set `"text": ""` in the in-memory entry; chunks are sufficient for all features |
| `app.py` | Comment on `current_total_words += word_count` was missing — easy to accidentally remove thinking it was dead code | Added inline comment clarifying it maintains session limit tracking across the upload loop |
| `modules/adaptive_chunking.py` | Module docstring and `validate_document` docstring both said "v1.2" | Corrected to "v1.1" and "session limits" |
| `modules/vector_store.py` | `get_or_create_collection()` and `drop_session()` were not thread-safe — the background indexing thread introduced in the previous session could race with the Gradio thread when creating or evicting ChromaDB clients | Added `_session_lock = threading.Lock()` and wrapped the client lookup/creation block in `with _session_lock:` |

---

### Re-check Fixes (v1.1)
**Date:** 2026-05-09

| File | Issue | Fix |
|------|-------|-----|
| `app.py` | **Critical syntax error** — `format_ai_message()` had a truncated `re.sub()` call on the header-conversion regex. The closing `)` and replacement argument were missing, causing a `SyntaxError` that crashed the app on every Q&A response | Completed the call: `_re.sub(r'...', convert_header, text)` |
| `app.py` | Two inline comments in `load_files()` still read `v1.2 adaptive validation` and `v1.2 adaptive chunk size` | Removed the stale version prefix from both comments |
| `modules/vector_store.py` | `drop_session()` removed entries from `_session_clients` without holding `_session_lock`, creating a potential race condition when two uploads trigger the session eviction path concurrently | Wrapped the `.pop()` inside `with _session_lock:` |

---

**Date:** 2026-05-09

| File | Bug | Fix |
|------|-----|-----|
| `modules/ai_engine.py` | Context and question were sent as two consecutive `user` messages, which many models (Qwen, Gemma, Llama) reject or handle incorrectly | Merged into a single `user` message with `<document_context>` tags wrapping the reference material |
| `modules/doc_library.py` | `save_library_snapshot()` wrote full raw document text for every file — a 100K-word doc produces a ~600 KB snapshot that grows with every save | Removed `"text"` from the snapshot payload entirely; chunks already contain all content needed for Q&A, quiz, and flashcards; `load_library_snapshot()` updated to set `text: ""` on restore |
| `modules/adaptive_chunking.py` + `app.py` | `detect_model()` cache was never invalidated — swapping a model in LM Studio mid-session left the app using the old context window size for the rest of the session | `adaptive_strategy.invalidate_cache()` is now called inside `refresh_home()`, so pressing "🔄 Refresh" re-detects the loaded model |
| `modules/vector_store.py` | `index_chunks()` called `_embed_texts()` synchronously on the Gradio main thread, blocking the entire UI for several seconds during indexing of large documents | `index_chunks()` is now a thin wrapper that dispatches work to a background thread via `queue.Queue` and blocks the caller until done — keeps Gradio's yield-based progress updates flowing while embedding runs |

---

**Date:** 2026-05-08

| File | Change | Why |
|------|--------|-----|
| `modules/ai_engine.py` | `ask_lmstudio()` gains `temperature` param (default `0.7` for Q&A, `0.2` for structured tasks) | Callers can now tune randomness per task — structured generation needs lower temperature for reliable output |
| `modules/ai_engine.py` | Context + question merged into a single user message instead of two consecutive `user` turns | Many models (Qwen, Gemma, Llama) mishandle or reject two back-to-back user messages; merged format is universally compatible |
| `modules/quiz.py` | Quiz context limit reads from `adaptive_strategy.detect_model()` (capped at 6 000 words) instead of hardcoded value | Models with 4K context windows no longer overflow during quiz generation |
| `modules/quiz.py` | All `ask_lmstudio()` calls pass `temperature=0.2` | Lower temperature produces more consistently-formatted MCQ output, reducing parser failures |
| `modules/flashcards.py` | Flashcard context limit reads from `adaptive_strategy.detect_model()` (capped at 5 000 words) | Same overflow protection as quiz — prevents context spill on small models |
| `modules/flashcards.py` | All `ask_lmstudio()` calls pass `temperature=0.2` | More deterministic output means fewer duplicate cards and less post-processing |
| `modules/mindmap.py` | Mindmap context limit reads from `adaptive_strategy.detect_model()` (capped at 4 000 words) | Same overflow protection — mindmap prompts are already large; this prevents silent truncation |
| `modules/mindmap.py` | All `ask_lmstudio()` calls pass `temperature=0.2` | Structured Markdown heading output is far more reliable at lower temperature |
| `modules/engine_manager.py` | `get_engine_status()` rewritten to make a single HTTP request (was two: `is_lmstudio_online()` + `check_lmstudio_connection()`) | Halves network overhead on every Home tab render and auto-refresh |

---

### Adaptive Document Analysis (v1.1 feature addition)
**Date:** 2026-05-08

| File | Change | Why |
|------|--------|-----|
| `modules/adaptive_chunking.py` | **New module** — `AdaptiveStrategy` class with model detection, chunk sizing, and document validation | Core of v1.2 adaptive engine |
| `modules/pdf_reader.py` | `chunk_text()` gains `chunk_size_tokens` param | Allows caller to pass adaptive token budget |
| `modules/study_context.py` | `build_balanced_context()` `max_words` now defaults to `None`; auto-queries adaptive strategy | Q&A context respects detected model window |
| `app.py` | `initialize_adaptive_strategy()` called at startup | Detects LM Studio model once on boot |
| `app.py` | `MAX_DOC_WORDS` 40K → 150K, `MAX_TOTAL_WORDS` 250K → 400K, `MAX_DOC_CHUNKS` 250 → 500 | Accept larger documents |
| `app.py` | `render_engine_status_html()` shows detected model name + context window info | User can see which model is loaded |
| `app.py` | `load_files()` uses `adaptive_strategy.validate_document()` + `compute_chunk_size()` | Per-document adaptive validation and chunking |
| `app.py` | Upload success line includes `[STRATEGY]` tag (TINY/SMALL/MEDIUM/LARGE/XLARGE) | Transparent feedback on chunk decision |
| `app.py` | Q&A fallback context uses `detect_model()["context_max_words"]` instead of hardcoded 4200 | Prevents context overflow on small models |

---

### [2026-05-05] — Q&A Chat Display: Scroll + Overflow Fix

| File | Change | Reason |
|---|---|---|
| `app.py` | Changed `#rk_chat_display` from `max-height:480px; overflow-y:auto` to `height:500px; overflow-y:scroll; overflow-x:hidden` | Fixed chat bubbles breaking out of container horizontally; `scroll` (vs `auto`) ensures scrollbar is always visible |
| `app.py` | Added dedicated `#rk_chat_display::-webkit-scrollbar` rules — 8px wide, indigo `#4F46E5` thumb, lights to `#818cf8` on hover | Makes scrollbar clearly visible and styled to match app accent color |
| `app.py` | Changed Firefox `scrollbar-color` from `#334155` (dim grey) to `#4F46E5` (indigo) | Consistent across Chrome and Firefox |

---

### [2026-05-02] — Dual-Mode Embedding Backend

| File | Change | Reason |
|---|---|---|
| `modules/vector_store.py` | Full rewrite of embedding logic — dual-mode router: tries LM Studio `/v1/embeddings` first, falls back to sentence-transformers | Eliminates internet check on every startup; LM Studio path requires no PyTorch and signals ready instantly |
| `modules/vector_store.py` | Added `_lmstudio_embed()` — calls `localhost:1234/v1/embeddings`, returns vectors or `None` on failure | Core LM Studio embedding path |
| `modules/vector_store.py` | Added `_embed_texts()` — unified router that picks the active backend; falls back live if LM Studio goes offline mid-session | Single call site used by both `index_chunks` and `search_similar_chunks` |
| `modules/vector_store.py` | Fixed `local_files_only` — preload worker now tries `local_files_only=True` first, only downloads if cache miss | Prevents internet ping on every startup when model is already cached |
| `modules/vector_store.py` | Added `get_embed_backend()` — returns human-readable string for Home tab status card | Surfaces active backend in UI |
| `modules/vector_store.py` | Removed unused `_get_model()` helper; `_embed_texts()` handles all routing cleanly | Simplifies the module |
| `app.py` | Added `get_embed_backend` to vector_store import | Exposes backend name for UI |
| `app.py` | Updated `render_engine_status_html()` — adds Embeddings row showing active backend with color-coded icon | User can see at a glance whether embeddings are running through LM Studio (⚡ green) or local sentence-transformers (🧩 amber) |

---

### [2026-05-02] — Math Renderer Double-Pass Bug Fix

| File | Change | Reason |
|---|---|---|
| `app.py` | Removed duplicate `render_plain_math_html(text)` call in `format_ai_message()` | Previous session's edits added the call twice — once correctly after `escape_non_tags()` (line 586), and again after the markdown formatting pass (line 595 with a stale comment). The second call was redundant and risked double-converting symbols already wrapped in `<span>` tags. Removed the duplicate. |

---

### [2026-04-25] — Rolled back HF model tiers, LM Studio only

| File | Change | Reason |
|---|---|---|
| `modules/engine_manager.py` | Stripped to LM Studio only — removed MODEL_TIERS, all HF code (load_hf_model_generator, ask_hf_model, is_hf_available, is_model_loaded), simplified ask() to always call ask_lmstudio | Reverting multi-tier engine; app now connects exclusively to LM Studio |
| `app.py` | Removed engine_tier_radio, engine_load_btn, engine_progress_html, load_engine_model() from Home tab and wiring | No longer needed without HF tiers |
| `app.py` | Removed render_progress_html() helper | Only used by load_engine_model |
| `app.py` | Simplified render_engine_status_html() — no mode/tier args, always shows LM Studio | Matches LM-Studio-only architecture |
| `app.py` | Removed `if mode != "lmstudio" and not is_model_loaded()` guard blocks from Q&A, Quiz, Flashcards, Mindmap | Only one backend now, guard is redundant |
| `app.py` | Home stat card AI Engine shows "🔧 LM Studio" hardcoded | Tier info no longer needed |

---

### [2026-04-20] — v1.2 Engine Selector + Dark/Light Theme Fix

#### AI Engine Model Selector
| File | Change | Reason |
|---|---|---|
| `modules/engine_manager.py` | Created — unified AI router with 4 tiers: StudyMind Fast (Qwen2.5-1.5B), Smart (Mistral-7B), Pro (Gemma-3-4B), LM Studio | Replaces hardcoded LM Studio dependency with a Claude-style tier picker |
| `app.py` | Added engine_manager imports and AI Engine section in Home tab with Radio selector + Load button + progress bar | UI for switching AI engine tiers |
| `app.py` | All generation calls (Q&A, Quiz, Flashcards, Mindmap) now route through `ask()` from engine_manager | Works with both LM Studio and HuggingFace backends transparently |
| `app.py` | HF model loads show download progress bar via generator pattern | User sees real-time progress when pulling a model for the first time |

#### Dark/Light Theme — 4 Bugs Fixed
| File | Bug | Fix |
|---|---|---|
| `app.py` | CSS selector `[data-theme="light"] html` is invalid — tries to find `html` inside element with attribute, impossible | Changed ALL selectors to `html[data-theme="light"]` — the attribute is ON the html element |
| `app.py` | Theme toggle Gradio button rendered as separate block below header, not inside it | Embedded `<button id="rk-theme-header-btn">` directly in header HTML; uses onclick to trigger hidden Gradio button (same pattern as quiz buttons) |
| `app.py` | `THEME_TOGGLE_JS` queried `.rk-theme-icon` class but no element had that class — icon never updated | JS now targets `#rk-theme-header-btn` directly by ID |
| `app.py` | Refresh home wiring used walrus operator `engine_status_out := gr.HTML(visible=False)` creating a hidden throwaway component | Restructured Home tab so `engine_status_html` is defined before wiring; refresh button now correctly updates visible status |

#### Additional Light Theme Improvements
| File | Change | Reason |
|---|---|---|
| `app.py` | Added `.rk-spacer` flex div in header for proper right-alignment of badge + toggle button | Badge and toggle now push to the right correctly |
| `app.py` | Added `html[data-theme="light"] [style*="color:#64748b"]` override | Muted text was invisible on light background |
| `app.py` | Added `html[data-theme="light"] [style*="background:#312e81"]` override | Indigo gradient backgrounds now render as light lavender |
| `app.py` | Removed old orphaned `.rk-theme-btn` CSS class (replaced by `#rk-theme-header-btn`) | No longer needed |
| `app.py` | `APP_VERSION` bumped to `v1.2` | New features land in v1.2 |

---

### [2026-04-09] — Reliability Pass: Persistence, Citations, and Bug Fixes

#### Confirmed Bug Fixes
| File | Change | Reason |
|---|---|---|
| `modules/mindmap.py` | `generate_mindmap_markdown()` now accepts `chunks=` and imports `re` at module scope | Fixes Mindmap tab crash and cleans up the parser helper |
| `modules/vector_store.py` | Removed `local_files_only=True`, removed invalid `chromadb.Client()` fallback, added lightweight session-cap | Fresh installs can now download embeddings model on first run; fallback no longer breaks on modern ChromaDB |
| `modules/math_renderer.py` | Fixed `\lceil`, guarded `$...$` handling so normal dollar amounts are not treated as math, collapsed redundant command passes | Correct math rendering and fewer false positives in chat/quiz/flashcards |
| `modules/doc_library.py` | Library cards now use per-file unit labels and distinct colors for all supported formats | PPTX/EPUB/TXT/MD cards now render correctly and are visually distinct |
| `app.py` | Quiz report export now uses full quiz length instead of answered-question count | Fixes incorrect score totals when exporting before finishing a quiz |
| `modules/quiz.py` | Table-parser answer fallback now scans trailing cells for the actual answer | Fixes fragile markdown-table parsing edge cases |
| `app.py` | Removed dead `get_text_from_selection()` helper and unused import drift | Keeps the live app consistent with the current chunk-based generation flow |
| `modules/summary.py` | Deleted unused summary module | Summary feature was intentionally removed from the app UI; leftover module was dead code |

#### App Improvements
| File | Change | Reason |
|---|---|---|
| `modules/doc_library.py` | Added `save_library_snapshot()` / `load_library_snapshot()` | Restores uploaded documents across app restarts using persisted extracted text/chunks |
| `app.py` | Upload, active-doc changes, and deletion now persist library snapshot | Keeps Library state consistent between sessions |
| `app.py` | `model_ready_signal()` restores saved library and re-indexes chunks at startup | Brings back the prior library automatically in a new browser session |
| `modules/vector_store.py` + `app.py` | Q&A now supports chunk-level evidence metadata and balanced-context fallbacks | Reduces "first 4000 words" bias and gives more concrete source notes |
| `app.py` | Removed tab-title markdown headers from Library, Q&A, and Mindmap tabs | Aligns UI with project memory: tab label is enough, less vertical clutter |

---

### [2026-04-09] — PyMuPDF Hotfix

| File | Change | Reason |
|---|---|---|
| `requirements.txt` | `PyMuPDF==1.27.2.2` → `PyMuPDF==1.25.5` | v1.27.x ships a broken `frontend` sub-package that requires a `static/` directory that doesn't exist — causes `RuntimeError: Directory 'static/' does not exist` on every startup. Pinned to last known-good version. |

---

### [2026-04-27] — Removed STT, Light Theme & Splash Screen

| File | Change | Reason |
|---|---|---|
| `app.py` | Removed `MIC_BUTTON_HTML` constant and `gr.HTML(MIC_BUTTON_HTML)` from Q&A tab | Speech-to-text button was broken (iframe boundary issue) and never worked reliably — removed entirely per user request |
| `app.py` | Removed all mic CSS rules: `#rk-mic-btn`, `#rk-mic-btn:hover`, `#rk-mic-btn.listening`, `#rk-mic-status`, `@keyframes rk-mic-pulse` | No longer needed |
| `app.py` | Removed `THEME_JS_INIT` constant (injected `RK_LIGHT_CSS` + `applyRkTheme()`) | Light theme removed per user request |
| `app.py` | Removed `THEME_TOGGLE_JS` constant | Light theme removed |
| `app.py` | Removed `gr.HTML(THEME_JS_INIT)` from UI | Light theme removed |
| `app.py` | Removed `<button id="rk-theme-header-btn">` from app header HTML | Light theme removed |
| `app.py` | Removed `theme_btn = gr.Button(...)` and `theme_btn.click(...)` Gradio wiring | Light theme removed |
| `app.py` | Removed `#rk_theme_btn`, `#rk-theme-header-btn` CSS rules | Light theme removed |
| `app.py` | Removed `SPLASH_JS` constant (~230 lines of JS) | Splash screen removed per user request |
| `app.py` | Removed `model_signal = gr.Textbox(...)` hidden signal textbox | Splash screen removed |
| `app.py` | Removed `model_ready_signal()` function | Splash screen removed; library restore logic was also here — sessions now start fresh |
| `app.py` | Removed `demo.load(fn=model_ready_signal...)` call | Splash screen removed |
| `app.py` | Removed `js=SPLASH_JS` from `demo.launch()` | Splash screen removed |
| `app.py` | Removed all splash CSS: `#rk-splash`, `@keyframes rk-splash-dismiss`, `#rk-splash-text`, `#rk-splash-bar-wrap`, `.rk-seg`, `.rk-tick`, `#rk-spinner`, `@keyframes rk-spin` | Splash screen removed |
| `app.py` | Fixed broken `@keyframes rk-spin` inside `render_mm_loading()` f-string (was corrupted by CSS regex during removal) | Mindmap loading animation was broken |
| `app.py` | Net result: 2,050 → 1,471 lines, ~26,000 characters removed, syntax verified clean | Leaner, faster startup |

---

### [2026-04-27] — Plain-Text Math Rendering (Q&A Pass 2)

| File | Change | Reason |
|---|---|---|
| `modules/math_renderer.py` | Added `render_plain_math_html()` — second rendering pass that converts plain-text math patterns with no LaTeX delimiters | LLM often ignores LaTeX formatting instructions; this catches what it naturally writes instead |
| `modules/math_renderer.py` | `render_plain_math_html` handles: fractions (`1/2`→½), powers (`x^2`→x²), subscripts (`v_0`→v₀), `sqrt(...)` → √(...), operators (`>=`→≥, `->`→→, `+-`→±), degree (`45 deg`→45°), multiply (`3 x 4`→3×4), named constants (`pi`→π, `theta`→θ) in math context | Full coverage of common plain-text math patterns |
| `modules/math_renderer.py` | `_apply_outside_tags()` helper — all substitutions skip content inside `<span>` and other HTML tags | Prevents Pass 1 results (already in `<span>` tags) from being double-converted |
| `modules/math_renderer.py` | sqrt step runs before powers step — so `sqrt(b^2-4ac)` converts the inner `b^2` cleanly | Processing order matters; sqrt args must be plain text when the sqrt regex runs |
| `app.py` | Added `render_plain_math_html` to import from `modules.math_renderer` | Make the function available in app scope |
| `app.py` | Added `text = render_plain_math_html(text)` as Pass 2 inside `format_ai_message()`, after markdown formatting, before `\n`→`<br>` conversion | Correct insertion point: after HTML structure is built, before final newline conversion |
| `modules/ai_engine.py` | `QA_SYSTEM_PROMPT` updated — removed LaTeX formatting instructions, replaced with natural-writing guidance (`x^2`, `sqrt(x)`, `1/2`, spell out Greek names) | LLM no longer needs to think about formatting; app handles it automatically |
| `memory.md` | Added `Math Rendering Strategy` section documenting the two-pass pipeline, all patterns, processing order, and scope | Permanent record of the design decision |

---

### [2026-04-09] — Quiz & Flashcard UI Simplification + memory.md Created

#### Quiz Tab — UI Cleanup
| File | Change | Reason |
|---|---|---|
| `app.py` | Removed `gr.Markdown("### Smart Quiz — Multiple Choice")` header | Tab label is sufficient; header wastes vertical space |
| `app.py` | Renamed accordion from `"⚙️ More Options"` → `"📋 After Quiz"` | Descriptive label; makes it clear when to open it |
| `app.py` | Moved hidden A/B/C/D + Submit/Next/Restart buttons to be defined **before** the accordion | Logical order — hidden controls come right after the quiz display |
| `app.py` | Removed `size="sm"` from Retry/Study/Export buttons inside accordion | Uniform button sizing inside accordion |
| `app.py` | Renamed `"📄 Export Study Report"` → `"📄 Export Report"` | Shorter label |

#### Flashcard Tab — UI Cleanup
| File | Change | Reason |
|---|---|---|
| `app.py` | Removed `gr.Markdown("### Study Flashcards — One Card at a Time")` header | Tab label is sufficient |
| `app.py` | Renamed accordion from `"⚙️ More Options"` → `"📋 More Options"` | Friendlier icon |
| `app.py` | Button labels shortened | Cleaner button row |
| `app.py` | Removed `size="sm"` from accordion buttons | Uniform sizing |

#### memory.md Created
| File | Change | Reason |
|---|---|---|
| `memory.md` | Created — documents UI design philosophy, layout rules, feature retention rules, architecture notes, model recommendations | Permanent reference so Claude reads project preferences before making changes |

---

### [2026-04-02] — v1.1 Full Session — Bug Fixes, UI Overhaul, Reliability

*(see full entry in git history)*

---

## File Index

| File | Purpose | Last Modified |
|---|---|---|
| `app.py` | Main Gradio UI — all tabs, wiring, render functions; syntax error in `format_ai_message` fixed | 2026-05-09 |
| `modules/adaptive_chunking.py` | Adaptive chunk sizing, model detection, document validation | 2026-05-08 |
| `modules/engine_manager.py` | Unified AI router — LM Studio only; single-request status check | 2026-05-08 |
| `modules/ai_engine.py` | LM Studio HTTP client, temperature control, single-message context | 2026-05-08 |
| `modules/quiz.py` | MCQ generation — 3-strategy parser, adaptive context, low-temp calls | 2026-05-08 |
| `modules/flashcards.py` | Batched flashcard generation — deduplication, adaptive context, low-temp | 2026-05-08 |
| `modules/mindmap.py` | Structured study tree renderer — adaptive context, low-temp generation | 2026-05-08 |
| `modules/pdf_reader.py` | PDF, DOCX, TXT, MD, PPTX, EPUB extraction + adaptive chunking | 2026-05-08 |
| `modules/study_context.py` | Balanced context builder — auto-detects adaptive max_words | 2026-05-08 |
| `modules/vector_store.py` | ChromaDB semantic search — dual-mode embedding; `index_chunks` runs off main thread | 2026-05-09 |
| `modules/doc_library.py` | Multi-document library with JSON persistence; snapshot no longer stores raw text | 2026-05-09 |
| `modules/math_renderer.py` | Two-pass math rendering (LaTeX + plain-text patterns) | 2026-04-27 |
| `modules/study_history.py` | Quiz session history and flashcard performance tracking | 2026-04-02 |
| `modules/exporters.py` | CSV and report export helpers | 2026-04-02 |
| `memory.md` | Permanent project design decisions and rules | 2026-05-08 |
| `CHANGELOG.md` | This file | 2026-05-08 |
| `requirements.txt` | Python dependencies | 2026-04-03 |
| `push_to_github.bat` | One-click GitHub push (Windows) | 2026-03-30 |
| `.gitignore` | Excludes venv, data, uploads, model files | 2026-03-29 |

---

## How to Update This File

Add new entries at the **top** of the Session Log (after the `---` separator), newest first.

---

*RK StudyMind — Built by RoniKid*
