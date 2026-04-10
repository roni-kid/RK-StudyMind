# 🧠 RK StudyMind — Changelog

> All notable changes to this project are documented here.
> Format: `[Date] | File(s) Changed | What Changed | Why`
> Order: **Newest first**

---

## Session Log

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
| `modules/vector_store.py` + `app.py` | Q&A now supports chunk-level evidence metadata and balanced-context fallbacks | Reduces “first 4000 words” bias and gives more concrete source notes |
| `app.py` | Removed tab-title markdown headers from Library, Q&A, and Mindmap tabs | Aligns UI with project memory: tab label is enough, less vertical clutter |

---

### [2026-04-09] — PyMuPDF Hotfix

| File | Change | Reason |
|---|---|---|
| `requirements.txt` | `PyMuPDF==1.27.2.2` → `PyMuPDF==1.25.5` | v1.27.x ships a broken `frontend` sub-package that requires a `static/` directory that doesn't exist — causes `RuntimeError: Directory 'static/' does not exist` on every startup. Pinned to last known-good version. |

---

### [2026-04-09] — Quiz & Flashcard UI Simplification + memory.md Created

#### Quiz Tab — UI Cleanup
| File | Change | Reason |
|---|---|—|
| `app.py` | Removed `gr.Markdown("### Smart Quiz — Multiple Choice")` header | Tab label is sufficient; header wastes vertical space |
| `app.py` | Renamed accordion from `"⚙️ More Options"` → `"📋 After Quiz"` | Descriptive label; makes it clear when to open it |
| `app.py` | Moved hidden A/B/C/D + Submit/Next/Restart buttons to be defined **before** the accordion | Logical order — hidden controls come right after the quiz display |
| `app.py` | Removed `size="sm"` from Retry/Study/Export buttons inside accordion | Uniform button sizing inside accordion |
| `app.py` | Renamed `"📄 Export Study Report"` → `"📄 Export Report"` | Shorter label |

#### Flashcard Tab — UI Cleanup
| File | Change | Reason |
|---|---|—|
| `app.py` | Removed `gr.Markdown("### Study Flashcards — One Card at a Time")` header | Tab label is sufficient |
| `app.py` | Renamed accordion from `"⚙️ More Options"` → `"📋 More Options"` | Friendlier icon |
| `app.py` | Button labels shortened: `"⬅️ Previous"` → `"⬅️ Prev"`, `"🔄 Reveal Answer"` → `"🔄 Reveal"`, `"✅  Got It!"` → `"✅ Got It"`, `"❌  Didn't Remember"` → `"❌ Missed"`, `"🔁 Study Again"` → `"🔁 Again"` | Cleaner button row; same meaning, less text |
| `app.py` | Renamed `"🔥 Only Hard Cards"` → `"🔥 Hard Cards Only"` | Clearer phrasing |
| `app.py` | Removed `size="sm"` from accordion buttons | Uniform sizing |

#### memory.md Created
| File | Change | Reason |
|---|---|—|
| `memory.md` | Created — documents UI design philosophy, layout rules, feature retention rules, architecture notes, model recommendations | Permanent reference so Claude reads project preferences before making changes |

---


#### Splash Screen — Polling Fix (Critical)
| File | Change | Reason |
|---|---|---|
| `app.py` | `SPLASH_JS` dismiss changed from hardcoded `setTimeout(2300)` to polling `#rk-model-signal textarea` every 250 ms | Splash was dismissing after 2.3 s regardless of model state — embedding model takes 10–30 s on first run, so the app appeared ready before it was |
| `app.py` | Added 60 s safety fallback `setTimeout` after polling loop | Prevents splash from hanging forever if signal never fires |
| `app.py` | Added `dismissSplash()` helper function inside SPLASH_JS | DRY — both the poll path and the fallback path call the same dismiss logic |
| `app.py` | Removed orphaned first `with gr.Blocks(title=..., css=css, js=SPLASH_JS)` block | A second `gr.Blocks()` block was silently overwriting `demo` — the CSS and JS from the first block were never applied to the real app |
| `app.py` | Moved `model_ready_signal()` function definition to before the `gr.Blocks()` context | Cleaner code order — function defined before the `demo.load()` that references it |
| `app.py` | Added comment: `# Gradio 6.0: css and js must be passed to launch()` | Documents why css/js are in launch() not gr.Blocks() |

#### New File Type Support
| File | Change | Reason |
|---|---|---|
| `modules/pdf_reader.py` | Added `read_txt()` — reads plain text with 4-encoding fallback (utf-8 → utf-8-sig → latin-1 → cp1252) | Students frequently have `.txt` lecture notes |
| `modules/pdf_reader.py` | Added `read_md()` — reads Markdown and strips `#`, `**`, `` ` ``, `---`, HTML tags before indexing | LM should receive clean prose, not raw Markdown syntax |
| `modules/pdf_reader.py` | Added `read_pptx()` — extracts slide title + body + table cells + speaker notes via python-pptx | PowerPoint is the dominant lecture format; speaker notes often have the richest content |
| `modules/pdf_reader.py` | Added `read_epub()` — extracts chapters via ebooklib + BeautifulSoup, strips nav/toc blocks | Textbooks distributed as EPUBs |
| `modules/pdf_reader.py` | Added `SUPPORTED_EXTENSIONS` constant | Single source of truth for all supported types |
| `modules/pdf_reader.py` | Extended `get_page_count()` — PPTX → slide count, EPUB → chapter count, TXT/MD → estimated pages (~300 words/page) | Meaningful unit labels per file type |
| `modules/pdf_reader.py` | Extended `get_page_label()` — returns `slides`, `chapters`, `est. pages` per type | Library card shows correct unit (not just "pages" for everything) |
| `app.py` | `gr.File` `file_types` expanded to `[".pdf",".docx",".txt",".md",".pptx",".epub"]` | File picker now shows and accepts all 6 types |
| `app.py` | Extension allowlist in `load_files()` expanded to all 6 types | Previously `.txt`, `.md`, `.pptx`, `.epub` were rejected with "unsupported type" |
| `app.py` | File icon dict — each type gets its own emoji: 📄 PDF · 📝 DOCX · 📃 TXT · 📋 MD · 📊 PPTX · 📖 EPUB | Visual distinction in upload status messages |
| `requirements.txt` | Added `python-pptx`, `ebooklib`, `beautifulsoup4` | New dependencies for PPTX and EPUB extraction |

#### Chat UI Upgrade
| File | Change | Reason |
|---|---|---|
| `app.py` | CSS: added `@import` for Inter (400–800) and JetBrains Mono (400/500) from Google Fonts | Nicer reading experience in Q&A chat |
| `app.py` | CSS: scoped Inter to `#rk_chat_display`, JetBrains Mono to code/pre elements inside chat | Fonts apply only to chat area — no side-effects on other tabs |
| `app.py` | CSS: `@keyframes rk-dot-bounce` + `.rk-dot` class | 3-dot bounce animation for typing indicator |
| `app.py` | `format_ai_message()` — added fenced code block handler (` ``` `) rendering as `<pre><code>` with JetBrains Mono dark background | AI responses with code blocks now render properly |
| `app.py` | `format_ai_message()` — inline `` ` `` updated to JetBrains Mono | Consistent monospace font for all code |
| `app.py` | `render_chat_bubbles()` — user bubble: `max-width:70%`, deeper indigo gradient `#4338ca→#6366f1`, `border-radius:18px 18px 4px 18px`, Inter 500 | Cleaner, more distinct user bubble |
| `app.py` | `render_chat_bubbles()` — AI bubble: upgraded avatar (gradient bg, `border-radius:12px`, indigo glow), `border-radius:4px 18px 18px 18px`, `max-width:75%` | Avatar and bubble match modern chat app aesthetics |
| `app.py` | `render_chat_bubbles()` — source rendered as pill badge (📎 + filename) | Cleaner than old border-top divider |
| `app.py` | Timestamps added to every message (`datetime.now().strftime("%I:%M %p")`) | Each bubble shows when the message was sent |
| `app.py` | `chat_log` entries changed from 2-tuple to 3-tuple `(speaker, message, timestamp)` | Store timestamp alongside message |
| `app.py` | `THINKING_BUBBLE` replaced `⋯ Thinking...` text with three `.rk-dot` spans | Animated 3-dot bounce instead of static text |

#### Docs Updated
| File | Change | Reason |
|---|---|---|
| `README.md` | Updated Features, Tech Stack, Supported File Types table, Requirements, Important Notes, Changelog summary | Reflect all v1.1 additions |
| `CHANGELOG.md` | Reordered all entries newest-first, updated File Index | Consistent chronological ordering |

---

### [2026-04-02] — v1.1 Full Session — Bug Fixes, UI Overhaul, Reliability

#### Summary Feature Removed
| File | Change | Reason |
|---|---|---|
| `app.py` | Removed ✍️ Summary tab entirely | User requested removal — replaced by Q&A for ad-hoc summaries |
| `app.py` | Removed `do_quick_summary()`, `do_detailed_summary()` functions | No longer needed |
| `app.py` | Removed `from modules.summary import ...` import | Dead import after tab removal |

#### Cross-Tab Doc Selector Fix (Critical Bug)
| File | Change | Reason |
|---|---|---|
| `app.py` | Removed hidden dummy `fc_doc_selector` / `sum_doc_selector` components | They absorbed updates that never reached the real selectors in Flashcard/Summary tabs |
| `app.py` | Moved `upload_btn`, `delete_btn`, `refresh_btn` `.click()` wiring to after all tabs | Components in later tabs weren't defined yet when wiring was inside Library tab |
| `app.py` | Added `quiz_doc_selector`, `mm_doc_selector` CheckboxGroups to Quiz and Mindmap tabs | Quiz and Mindmap now use doc selector instead of active document |
| `app.py` | All 4 checkbox selectors (fc, quiz, mm + old sum) now synced on upload/delete/refresh | Ensures all tabs always reflect current library state |
| `app.py` | Removed "Active Document" textbox from Quiz, Mindmap, and Summary tabs | Replaced by per-tab document selector |
| `app.py` | Removed `mm_scope` radio (Active/All) from Mindmap tab | Replaced by explicit CheckboxGroup |

#### Stale Browser State Crash Fix
| File | Change | Reason |
|---|---|---|
| `app.py` | Added `sanitize_docs()` helper | Coerces stale browser values (str, list with deleted names, None) into clean list |
| `app.py` | Applied `sanitize_docs()` at top of `start_quiz()`, `make_flashcards()`, `make_mindmap_full()` | Prevents Gradio `CheckboxGroup` validation crash after app restart |
| `app.py` | All CheckboxGroup components initialized with `value=[]` | Startup library is always empty — avoids validation error on first render |

#### Delete Dropdown Stale Value Fix
| File | Change | Reason |
|---|---|---|
| `app.py` | `delete_doc()` now returns `gr.update(value=None)` for delete dropdown | Stale filename persisted after deletion, causing silent ghost-delete on next click |

#### vector_store.py Bare Except Fix
| File | Change | Reason |
|---|---|---|
| `modules/vector_store.py` | `except: pass` → `except Exception as e: print(...)` | Silent failures when clearing old ChromaDB index were masking duplicate chunk bugs |

#### doc_library.py Wrong Tab Name Fix
| File | Change | Reason |
|---|---|---|
| `modules/doc_library.py` | Empty library message changed from "PDF Reader tab" → "📚 Library tab" | Tab was renamed but message wasn't updated |

#### Home Tab v1.1 Redesign
| File | Change | Reason |
|---|---|---|
| `app.py` | Removed name input, welcome textbox, LM Studio check button | Replaced with clean stats-only dashboard |
| `app.py` | Hero banner: animated indigo gradient, gloss sweep, pulsing v1.1 badge | Visual upgrade |
| `app.py` | Library Stats row: Documents, Words Indexed, Vector Chunks, AI Engine status | Live stats on home page |
| `app.py` | Feature cards: static divs with `rk-feat-card` CSS class hover | No JS event handlers (Gradio sanitizes them — caused raw code leaking as text) |
| `app.py` | Single "🔄 Refresh Stats & Check AI" button | Replaces old name + launch + check flow |
| `app.py` | `load_files()` now also returns `render_home_stats()` | Stats update automatically when new doc is uploaded |
| `app.py` | Removed `feature_card` `onclick`/`onmouseover`/`onmouseout` JS handlers | Gradio HTML sanitizer strips these and dumps raw attribute strings as visible text |

#### Quiz Options Not Clickable Fix
| File | Change | Reason |
|---|---|---|
| `app.py` | Quiz hidden buttons changed from `visible=False` to `visible=True` | `display:none` elements don't reliably fire `.click()` events across browsers |
| `app.py` | Added CSS `.rk-hidden-btn` class — pushes buttons off-screen with `position:fixed;top:-9999px` | Visually hidden but present in DOM so JS `.click()` works |
| `app.py` | JS changed from `querySelectorAll('[id*=rk_quiz_btn_a]')[0].click()` to `getElementById('rk_quiz_btn_a').querySelector('button').click()` | Old selector found the container div, not the `<button>` element inside it |
| `app.py` | Same `getElementById` fix applied to Submit and Next buttons inside quiz card | Consistent approach across all hidden triggers |

#### Quiz Batch Generation (LLM Context Limit Workaround)
| File | Change | Reason |
|---|---|---|
| `modules/quiz.py` | `generate_quiz()` now calls `_generate_batch()` in a loop (BATCH_SIZE=3) | LLM forgets format instructions mid-generation for large counts |
| `modules/quiz.py` | Added `_generate_batch()` function | Isolated per-batch LLM call with avoid-duplicate block |
| `modules/quiz.py` | `seen` set deduplication across batches | Prevents same question appearing twice across multiple batches |
| `modules/quiz.py` | `consecutive_empty` counter — stops after 2 empty batches in a row | Prevents infinite loop when model is truly stuck |
| `modules/quiz.py` | Fallback prompt per batch if primary parse returns nothing | Each batch independently retries with a simpler prompt |

#### Quiz Slider Max Increased to 40
| File | Change | Reason |
|---|---|---|
| `app.py` | `num_q_slider` `maximum=10` → `maximum=40` | User requested parity with flashcards (which already support 40) |
| `modules/quiz.py` | Context window 4000 → 6000 words | Larger quizzes need more source material to draw from across many batches |
| `modules/quiz.py` | `max_attempts` formula made more generous: `(n // BATCH + 3) * 4` | 40 questions = ~14 batches; needs more headroom for retries |

#### SyntaxError Fix (Python < 3.12 f-string backslash)
| File | Change | Reason |
|---|---|---|
| `app.py` | `render_quiz_question()` explanation line: extracted `exp_text` variable before f-string | `f"Correct answer: {q[\"answer\"]}"` inside outer f-string = SyntaxError on Python < 3.12 |

#### LM Studio Offline Detection
| File | Change | Reason |
|---|---|---|
| `modules/ai_engine.py` | Added `is_lmstudio_online()` — fast 4s timeout boolean check | Separate from verbose `check_lmstudio_connection()` — used as pre-flight |
| `app.py` | `start_quiz()` checks `is_lmstudio_online()` first | Shows 🔴 message in Status instead of silent failure or Gradio Error popup |
| `app.py` | `make_flashcards()` checks `is_lmstudio_online()` first | Same — clear error before attempting generation |
| `app.py` | `make_mindmap_full()` checks `is_lmstudio_online()` first | Same for mindmap |
| `app.py` | `answer_question()` checks `is_lmstudio_online()` first | Shows 🔴 message as AI chat bubble |

---

### [2026-03-31] — Quiz Parser — Table Format Support

| File | Change | Reason |
|---|---|---|
| `modules/quiz.py` | Added `_parse_table()` strategy | Model returned markdown table format — old parser got 0 results |
| `modules/quiz.py` | Added `_parse_numbered()` strategy (refactored) | Cleaner numbered block parser |
| `modules/quiz.py` | Added `_parse_loose()` strategy | Last-resort fallback for any Q/A/ANSWER pattern |
| `modules/quiz.py` | Added `_clean_answer()` helper | Strips `**B**` bold markers before extracting letter |
| `modules/quiz.py` | Added `_build_question()` helper | Validates + pads missing options so UI never breaks |
| `modules/quiz.py` | Prompt now explicitly says "Do NOT use tables or markdown formatting" | Reduce likelihood of table output |
| `modules/quiz.py` | Context window increased from 3000 → 4000 words | Better coverage especially for short documents |
| `modules/quiz.py` | Accept questions with 2+ options (not strict 4) — pad missing to "—" | Partial output from small docs still usable |

---

### [2026-03-31] — Changelog Created

| File | Change | Reason |
|---|---|---|
| `CHANGELOG.md` | Created — full historical log of all changes | Developer reference — track what changed, when, and why |

---

### [2026-03-30] — Mindmap Inline Canvas (No iframe)

| File | Change | Reason |
|---|---|---|
| `modules/mindmap.py` | Replaced Markmap.js with custom HTML5 Canvas radial renderer | Markmap.js produced left/right tree — user wants radial layout |
| `modules/mindmap.py` | 8-color `PALETTE` — each branch gets unique color, leaves inherit | Match reference image style |
| `modules/mindmap.py` | `parse_tree()` — converts `#/##/###` markdown to nested dict | Feed structured data to canvas renderer |
| `modules/mindmap.py` | `mindmap_to_html()` — returns inline `<div>+<canvas>+<script>` snippet | No iframe needed — events work natively |
| `modules/mindmap.py` | Radial layout — center oval, branches fanned by angle, sub-nodes spread | Match reference mindmap image layout |
| `modules/mindmap.py` | Bezier curve edges between nodes | Curved arrows as shown in reference |
| `modules/mindmap.py` | Scroll-to-zoom, drag-to-pan, Reset/+/- buttons | All controls working natively (no iframe sandboxing) |
| `modules/mindmap.py` | `ResizeObserver` — canvas resizes with window | Responsive canvas |
| `modules/mindmap.py` | Unique `uid` counter per render — prevents JS variable collision | Multiple renders on same page work correctly |
| `app.py` | Removed iframe wrapper from `make_mindmap_full()` | Canvas HTML injected directly into `gr.HTML` |
| `app.py` | Fixed import — removed `extract_all_nodes`, `generate_cross_connections` (deleted functions) | ImportError fix |
| `app.py` | `make_mindmap_full()` simplified to single-step yield | No cross-connection step needed with new renderer |

---

### [2026-03-30] — Quiz Visual Overhaul

| File | Change | Reason |
|---|---|---|
| `app.py` | Quiz card: progress bar at top showing question N/total | Show progress through quiz |
| `app.py` | Quiz card: score pill showing running correct/total | Live score tracking visible during quiz |
| `app.py` | Quiz options: inline click handlers — no separate A/B/C/D buttons visible | Cleaner UX — click the option directly |
| `app.py` | Hidden quiz control buttons (CSS `rk-hidden-btn`) triggered by JS | Options fire Gradio state via hidden buttons |
| `app.py` | Submit/Next buttons embedded inside quiz card HTML | All controls in one place |
| `app.py` | `render_quiz_question()` accepts `score` parameter | Show running score during quiz |
| `app.py` | Added `render_quiz_status_html()` for styled status messages | Consistent styled status strip |

---

### [2026-03-30] — Q&A Chat Bubbles

| File | Change | Reason |
|---|---|---|
| `app.py` | Replaced `gr.Textbox` chat display with `gr.HTML` | Enable styled chat bubbles |
| `app.py` | User messages: right-aligned, indigo gradient bubble | Visual distinction between user/AI |
| `app.py` | AI responses: left-aligned, dark card with 🧠 avatar | Match modern chat UI patterns |
| `app.py` | Added source badge below AI responses (📎 Source: filename) | Show which document the answer came from |
| `app.py` | Added `format_ai_message()` — handles **bold**, *italic*, `code`, numbered lists, LaTeX | Render AI markdown/math properly in HTML |
| `app.py` | Added MathJax 3 CDN script injection | Render LaTeX math from AI responses |
| `app.py` | Added "thinking" animation (3-dot bounce bubble) | Show user AI is processing |
| `app.py` | Converted `answer_question` to generator (`yield`) | Show thinking state before answer arrives |
| `app.py` | Added `demo.queue()` call | Required for Gradio generator functions |
| `app.py` | Added timestamps to each message (e.g. "1:47 PM") | Context for conversation history |
| `app.py` | Added `SCROLL_JS` snippet | Auto-scroll to latest message after each response |

---

### [2026-03-30] — Home Page Redesign (v1.1 UI)

| File | Change | Reason |
|---|---|---|
| `app.py` | Hero section: animated gradient background (`gradientShimmer` keyframe, 7s loop) | Visual polish — animated home page |
| `app.py` | Hero section: glossy light sweep overlay (`glossMove` keyframe, 4s loop) | Glossy moving effect as requested |
| `app.py` | Hero section: pulsing v1.1 badge (`pulseBadge` keyframe) | Highlight version number |
| `app.py` | Feature cards: all 6 in a single `flex-wrap:nowrap` row | User requested single-line layout |
| `app.py` | Feature cards: `onclick` JS using `document.querySelectorAll('[role="tab"]')[N].click()` | Navigate to tabs on card click (by index — reliable, text matching was broken) |
| `app.py` | Added `STUDY_TIPS` list — random tip shown at bottom of Home | Suggested tip system to add value |
| `app.py` | Added Library Stats row — docs, words, vector chunks, AI engine status | Live stats on home page |
| `app.py` | Added `render_home_stats()` and `refresh_home()` | Refresh button re-checks AI connection and updates stats |

---

### [2026-03-29] — v1.0 Complete — Multi-Document Support

| File | Change | Reason |
|---|---|---|
| `app.py` | Replaced global "Active Document" concept with per-tab document selectors | User needs to select documents independently per feature |
| `app.py` | Quiz, Flashcards, Mindmap → `gr.CheckboxGroup` (multi-select) | Allow selecting multiple docs for cross-document generation |
| `app.py` | Summary → `gr.Dropdown` (single-select) | Summary operates on one document at a time |
| `app.py` | Library upload now syncs all selectors across all tabs automatically | Prevent stale selector state after uploading new docs |
| `app.py` | Added `get_text_from_selection()` helper | Combine text from multiple selected documents |
| `modules/flashcards.py` | Increased context window from 3000 → 4000 words | Better coverage for larger documents |

---

### [2026-03-29] — sentence-transformers Warning Suppression

| File | Change | Reason |
|---|---|---|
| `modules/vector_store.py` | Added `warnings.filterwarnings("ignore", message=".*position_ids.*")` and `logging.getLogger("sentence_transformers").setLevel(logging.ERROR)` | Suppress harmless `UNEXPECTED key: embeddings.position_ids` warning from terminal output |

---

### [2026-03-29] — Bug Fixes Batch #1

| File | Bug Fixed | Fix Applied |
|---|---|---|
| `modules/quiz.py` | `answer in "ABCD"` accepted empty strings (substring check) | Changed to `answer in ["A","B","C","D"]` list membership |
| `modules/flashcards.py` | Batches 2–4 repeated the same questions as batch 1 | Passed `existing_questions` list into each new batch prompt + `seen_questions` deduplication set |
| `modules/vector_store.py` | ChromaDB crashed on filenames with spaces/special chars | Added `sanitize_id()` — strips non-alphanumeric chars from IDs |
| `modules/doc_library.py` | Library lost all documents on app restart | Added JSON persistence to `data/library.json` via `_save_library()` |
| `modules/mindmap.py` | H1 detection missed `#Topic` (no space after #) | Changed check to `line.startswith("#") and not line.startswith("##")` |
| `app.py` | Summary tab missing — module existed but was never imported/wired | Re-imported `generate_quick_summary`, `generate_detailed_summary` and rebuilt Summary tab |

---

### [2026-03-29] — Initial Build (v0.1 → v1.0)

#### Project Setup
| File | Change | Reason |
|---|---|---|
| `app.py` | Created — main Gradio app with 5 tabs | Initial project scaffold |
| `requirements.txt` | Created — gradio, chromadb, PyMuPDF, sentence-transformers, requests, python-docx | Dependencies list |
| `push_to_github.bat` | Created — one-click GitHub push script | Automate git workflow |
| `.gitignore` | Created — excludes venv/, data/, uploads/, *.gguf, *.bin | Prevent large/sensitive files from being committed |

#### Modules Created
| File | What It Does |
|---|---|
| `modules/ai_engine.py` | LM Studio HTTP client — `ask_lmstudio()`, `check_lmstudio_connection()` |
| `modules/pdf_reader.py` | PDF + DOCX text extraction, chunking, page count |
| `modules/vector_store.py` | ChromaDB + sentence-transformers semantic search |
| `modules/doc_library.py` | In-memory document library dict management |
| `modules/flashcards.py` | Flashcard generation via LM Studio |
| `modules/quiz.py` | Multiple choice quiz generation + parsing |
| `modules/summary.py` | Quick (5 bullets) and detailed summary generation |
| `modules/mindmap.py` | Mindmap markdown generation + Markmap.js HTML renderer |

#### Initial Tabs Built
- 🏠 Home — basic welcome screen
- 📚 Library — upload PDF/DOCX
- 💬 Q&A — RAG-powered chat with active document
- 📝 Quiz — MCQ generation A/B/C/D
- ✍️ Summary — quick and detailed summaries
- 🃏 Flashcards — up to 40 cards with score tracking
- 🗺️ Mindmap — markdown outline + Markmap.js browser render

---

## File Index

| File | Purpose | Last Modified |
|---|---|---|
| `app.py` | Main Gradio UI — all tabs, wiring, splash screen, render functions | 2026-04-03 |
| `modules/ai_engine.py` | LM Studio HTTP client + `is_lmstudio_online()` pre-flight check | 2026-04-02 |
| `modules/pdf_reader.py` | PDF, DOCX, TXT, MD, PPTX, EPUB extraction + chunking | 2026-04-03 |
| `modules/vector_store.py` | ChromaDB semantic search with sanitized IDs, error logging | 2026-04-02 |
| `modules/doc_library.py` | Multi-document library with JSON persistence | 2026-04-02 |
| `modules/flashcards.py` | Batched flashcard generation with deduplication | 2026-03-30 |
| `modules/quiz.py` | MCQ generation — 3-strategy parser, batch loop, 40-question support | 2026-04-02 |
| `modules/mindmap.py` | Radial mindmap — Canvas renderer, no dependencies | 2026-03-31 |
| `README.md` | Project documentation | 2026-04-03 |
| `CHANGELOG.md` | This file | 2026-04-03 |
| `requirements.txt` | Python dependencies | 2026-04-03 |
| `push_to_github.bat` | One-click GitHub push (Windows) | 2026-03-30 |
| `.gitignore` | Excludes venv, data, uploads, model files | 2026-03-29 |

---

## How to Update This File

Add new entries at the **top** of the Session Log (after the `---` separator), newest first:

```
### [YYYY-MM-DD] — Short Description

| File | Change | Reason |
|---|---|---|
| `filename` | What you changed | Why you changed it |
```

Then update the **File Index** `Last Modified` column for any files touched.

---

*RK StudyMind — Built by RoniKid*
