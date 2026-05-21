# Phase 2 diagnostic — tests Gradio UI construction step by step
import sys, traceback, os
sys.path.append(os.path.dirname(__file__))

print("--- Phase 2: UI Construction Diagnostic ---\n", flush=True)

# Imports (all known good)
from modules.pdf_reader import read_file, get_page_count, get_page_label, chunk_text
from modules.ai_engine import ask_lmstudio, check_lmstudio_connection, is_lmstudio_online
from modules.vector_store import index_chunks, search_similar_chunks, preload_model_background, is_model_ready, clear_index, drop_session, get_embed_backend
from modules.engine_manager import get_active_mode, get_theme, set_theme, ask, get_engine_status
from modules.flashcards import generate_flashcards
from modules.mindmap import generate_mindmap_markdown, mindmap_to_html, save_mindmap_file
from modules.quiz import generate_quiz
from modules.doc_library import render_library_html, save_library_snapshot, load_library_snapshot
from modules.exporters import export_flashcards_csv, export_quiz_report
from modules.study_context import build_balanced_context
from modules.study_history import record_flashcard_result, record_quiz_session, get_quiz_analytics, get_hard_flashcards
from modules.math_renderer import render_math, render_math_html, render_plain_math_html
import gradio as gr

print("  OK  all imports", flush=True)

# Now import app itself to trigger UI build, capturing any error
try:
    import app as _app
    print("  OK  app.py loaded — no crash in UI build", flush=True)
except SystemExit as e:
    print(f"  FAIL  sys.exit() called with code: {e.code}", flush=True)
    traceback.print_exc()
except Exception as e:
    print(f"  FAIL  Exception during UI build:", flush=True)
    traceback.print_exc()

print("\n--- Done ---", flush=True)
