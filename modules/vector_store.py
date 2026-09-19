import json
import logging
import queue
import re
import threading
import warnings
from collections import OrderedDict

import chromadb
import requests

from modules.ai_engine import resolve_embedding_model_id
from modules.runtime_paths import log

warnings.filterwarnings("ignore", message=".*position_ids.*")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)


def _log(message):
    """Backwards-compatible alias; the shared implementation lives in runtime_paths."""
    log(message)


# =============================================
# 🔍 Vector Store Module — Semantic Search
#
# Embedding backend — dual-mode:
#
#   Priority 1: LM Studio (localhost:1234/v1/embeddings)
#   Priority 2: sentence-transformers (local cache, then download)
#
# The two backends produce DIFFERENT vector dimensionalities (e.g. 768 for
# nomic-embed vs 384 for all-MiniLM-L6-v2). A collection built with one and
# queried with the other returns meaningless nearest neighbours rather than an
# error, so the active backend + dimension is recorded per session and any
# mismatch raises EmbeddingMismatchError instead of degrading silently.
# =============================================

COLLECTION_NAME     = "studymind_docs"
EMBED_MODEL_NAME    = "all-MiniLM-L6-v2"
LM_STUDIO_EMBED_URL = "http://localhost:1234/v1/embeddings"
MAX_SESSION_CLIENTS = 8

# LM Studio embeds the whole list in one request. 500 chunks in a single POST
# reliably blows past the timeout; 64 keeps each request comfortably inside it.
EMBED_BATCH_SIZE = 64
EMBED_REQUEST_TIMEOUT = 60

# Upper bound on a single index_chunks() call. Without this the caller blocks
# on result_q.get() forever if the worker thread dies.
INDEX_TIMEOUT_SECONDS = 900

# "lmstudio" | "sentence_transformers" | None (still loading)
_embed_backend   = None
_embedding_model = None          # only populated when backend == "sentence_transformers"
_model_ready_evt = threading.Event()
_preload_thread  = None
_session_clients = OrderedDict()  # session_id -> chromadb client (LRU ordered)
_session_embed   = {}             # session_id -> {"backend": str, "dim": int}
_model_error     = None
# RLock allows re-entry when drop_session is called from within get_or_create_collection
_session_lock    = threading.RLock()


class EmbeddingMismatchError(RuntimeError):
    """
    Raised when the active embedding backend produces vectors of a different
    dimensionality than the ones already stored for this session. Surfacing
    this is the whole point — the previous behaviour was to return nonsense
    neighbours or an empty list with no signal to the user.
    """


# ── ChromaDB helpers ─────────────────────────────────────────────

def _create_client():
    if hasattr(chromadb, "EphemeralClient"):
        return chromadb.EphemeralClient()
    raise RuntimeError(
        "This ChromaDB build does not expose EphemeralClient. "
        "Install a compatible chromadb version."
    )


# ── LM Studio embedding helpers ──────────────────────────────────

def _lmstudio_embed_batch(texts: list, model_id: str) -> list | None:
    """One /v1/embeddings request. Returns vectors, or None on any failure."""
    try:
        r = requests.post(
            LM_STUDIO_EMBED_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"input": texts, "model": model_id}),
            timeout=EMBED_REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            vectors = [item["embedding"] for item in data.get("data", [])]
            if len(vectors) != len(texts):
                _log(
                    f"⚠️ LM Studio returned {len(vectors)} embeddings for "
                    f"{len(texts)} inputs — treating as failure"
                )
                return None
            return vectors
        # Previously a bare `except: pass` hid this entirely, so a rejected
        # model id looked identical to "LM Studio has no embedding model".
        _log(f"⚠️ LM Studio embeddings HTTP {r.status_code}: {(r.text or '')[:200]}")
    except requests.exceptions.Timeout:
        _log(f"⚠️ LM Studio embeddings timed out after {EMBED_REQUEST_TIMEOUT}s")
    except requests.exceptions.ConnectionError:
        _log("⚠️ LM Studio embeddings: connection refused")
    except Exception as exc:
        _log(f"⚠️ LM Studio embeddings failed: {exc}")
    return None


def _lmstudio_embed(texts: list) -> list | None:
    """
    Embed `texts` through LM Studio, batched. Returns None if any batch fails,
    so callers never get a partially-embedded list.
    """
    model_id = resolve_embedding_model_id()
    if not model_id:
        # Sending the literal "local-model" is rejected by LM Studio's strict
        # model validation, which is why this path had never once succeeded.
        _log("ℹ️ No embedding model is loaded in LM Studio")
        return None

    vectors = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        result = _lmstudio_embed_batch(batch, model_id)
        if result is None:
            return None
        vectors.extend(result)
    return vectors


def _lmstudio_embedding_available() -> bool:
    """Quick probe — returns True if LM Studio answers an embedding request."""
    result = _lmstudio_embed(["ping"])
    return result is not None and len(result) > 0


# ── sentence-transformers helpers ────────────────────────────────

def _load_st_model(allow_download: bool = False):
    from sentence_transformers import SentenceTransformer
    if allow_download:
        return SentenceTransformer(EMBED_MODEL_NAME)
    # local_files_only=True — never pings the internet
    return SentenceTransformer(EMBED_MODEL_NAME, local_files_only=True)


def _ensure_st_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = _load_st_model(allow_download=False)
        except Exception:
            _embedding_model = _load_st_model(allow_download=True)
    return _embedding_model


# ── Unified embed router ─────────────────────────────────────────

def _embed_texts(texts: list) -> list:
    """
    Embeds a list of strings using the active backend.
    Falls back automatically if LM Studio goes offline mid-session.
    """
    global _embed_backend, _embedding_model

    if _embed_backend == "lmstudio":
        result = _lmstudio_embed(texts)
        if result is not None:
            return result
        _log("⚠️ LM Studio embedding unavailable mid-session, switching to sentence-transformers")
        _embed_backend = "sentence_transformers"

    # Backend not yet resolved (preload still running) — wait, then re-dispatch
    # rather than assuming sentence-transformers is the target.
    if _embed_backend is None:
        _model_ready_evt.wait(timeout=60)

    if _embed_backend == "lmstudio" and _embedding_model is None:
        result = _lmstudio_embed(texts)
        if result is not None:
            return result
        _log("⚠️ LM Studio embedding unavailable, switching to sentence-transformers")
        _embed_backend = "sentence_transformers"

    model = _ensure_st_model()
    if model is None:
        raise RuntimeError(
            _model_error or
            "Embedding model unavailable. Start LM Studio with an embedding model "
            "or ensure all-MiniLM-L6-v2 is cached locally."
        )
    return model.encode(texts, show_progress_bar=False).tolist()


def _embed_with_guard(texts: list, session_id: str, allow_register: bool) -> list:
    """
    Embed and enforce backend/dimension consistency for the session.

    allow_register=True  (indexing)  — first call for a session records the
                                       backend and dimension.
    allow_register=False (querying)  — a mismatch always raises.
    """
    vectors = _embed_texts(texts)
    if not vectors:
        return vectors

    dim = len(vectors[0])
    backend = _embed_backend or "unknown"

    with _session_lock:
        known = _session_embed.get(session_id)
        if known is None:
            if allow_register:
                _session_embed[session_id] = {"backend": backend, "dim": dim}
            return vectors

        if known["dim"] != dim:
            raise EmbeddingMismatchError(
                f"Embedding backend changed mid-session "
                f"({known['backend']} / {known['dim']}-d → {backend} / {dim}-d). "
                "Stored vectors are no longer comparable — re-index your library "
                "(Library tab → 🔄 Refresh) to restore semantic search."
            )
        if known["backend"] != backend:
            # Same dimensionality, different producer: still worth recording.
            _log(f"ℹ️ Embedding backend changed to {backend} at matching {dim}-d")
            known["backend"] = backend
    return vectors


def get_session_embed_info(session_id: str) -> dict:
    with _session_lock:
        return dict(_session_embed.get(session_id) or {})


# ── Startup / preload ────────────────────────────────────────────

def _preload_worker():
    """
    Background thread that picks the best embedding backend:
      1. LM Studio (if an embedding model is loaded) — instant, no downloads
      2. sentence-transformers local cache — offline, no internet
      3. sentence-transformers download — first-ever launch only
    """
    global _embed_backend, _embedding_model, _model_error

    _log("🔍 Checking LM Studio for an embedding model…")
    if _lmstudio_embedding_available():
        _embed_backend = "lmstudio"
        _log("✅ Embedding backend: LM Studio (localhost:1234)")
        _model_ready_evt.set()
        return

    _log("🔄 LM Studio embedding not available — loading sentence-transformers…")
    try:
        _embedding_model = _load_st_model(allow_download=False)
        _embed_backend = "sentence_transformers"
        _log("✅ Embedding backend: sentence-transformers (local cache, offline)")
    except Exception:
        try:
            _log("⬇️  Downloading all-MiniLM-L6-v2 (first-time setup)…")
            _embedding_model = _load_st_model(allow_download=True)
            _embed_backend = "sentence_transformers"
            _log("✅ Embedding backend: sentence-transformers (downloaded)")
        except Exception as e:
            _model_error = (
                "Embedding model could not be loaded. "
                "Either start LM Studio with an embedding model, "
                "or connect to the internet once to download all-MiniLM-L6-v2."
            )
            _log(f"❌ Embedding model load failed: {e}")
    finally:
        _model_ready_evt.set()


def preload_model_background():
    """Call once at app startup to detect and warm the embedding backend."""
    global _preload_thread
    if _preload_thread is None or not _preload_thread.is_alive():
        _preload_thread = threading.Thread(target=_preload_worker, daemon=True)
        _preload_thread.start()


def get_embed_backend() -> str:
    """Human-readable backend name for the Home tab status card."""
    if _embed_backend == "lmstudio":
        return "LM Studio"
    if _embed_backend == "sentence_transformers":
        return "sentence-transformers (local)"
    return "Loading…"


# ── ChromaDB helpers ─────────────────────────────────────────────

def sanitize_id(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)


def get_or_create_collection(session_id: str):
    if not session_id:
        raise ValueError("session_id is required")
    with _session_lock:
        client = _session_clients.get(session_id)
        if client is None:
            if len(_session_clients) >= MAX_SESSION_CLIENTS:
                # next(iter(...)) is INSERTION order, so this used to evict the
                # oldest-created session — very often the tab the user has had
                # open all day. OrderedDict + move_to_end below makes it a true
                # least-recently-USED eviction.
                evicted_id = next(iter(_session_clients))
                _log(f"ℹ️ Session cap reached ({MAX_SESSION_CLIENTS}) — evicting least-recently-used session {evicted_id[:8]}")
                drop_session(evicted_id)
            client = _create_client()
            _session_clients[session_id] = client
        else:
            _session_clients.move_to_end(session_id)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


# ── Public API ───────────────────────────────────────────────────

def index_chunks(chunks: list, doc_id: str, filename: str, session_id: str,
                 timeout: float = INDEX_TIMEOUT_SECONDS):
    """
    Index chunks into the vector store.
    Runs in a background thread to avoid blocking the Gradio main thread
    (embedding can take several seconds on large documents or slow hardware).
    Blocks the caller until indexing is done and re-raises any exception.
    """
    result_q: queue.Queue = queue.Queue()

    def _worker():
        try:
            n = _index_chunks_impl(chunks, doc_id, filename, session_id)
            result_q.put(("ok", n))
        except BaseException as exc:      # noqa: BLE001 - must not lose the signal
            result_q.put(("err", exc))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    try:
        status, value = result_q.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError(
            f"Indexing '{filename}' exceeded {int(timeout)}s. "
            "The embedding backend may be unresponsive."
        )
    if status == "err":
        raise value
    return value


def _index_chunks_impl(chunks: list, doc_id: str, filename: str, session_id: str):
    collection = get_or_create_collection(session_id)
    safe_source = sanitize_id(doc_id)

    try:
        existing = collection.get(where={"source": safe_source})
        if existing["ids"]:
            collection.delete(where={"source": safe_source})
    except Exception as e:
        _log(f"⚠️ Could not clear old index for '{filename}': {e}")

    if not chunks:
        return 0

    _log(f"🔄 Indexing {len(chunks)} chunks from '{filename}'… (backend: {_embed_backend})")
    embeddings = _embed_with_guard(chunks, session_id, allow_register=True)

    ids       = [f"{safe_source}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": safe_source, "original_filename": filename, "chunk_index": i}
                 for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    _log(f"✅ Indexed {len(chunks)} chunks!")
    return len(chunks)


def search_similar_chunks(question: str, doc_id: str, session_id: str, top_k: int = 3,
                          include_metadata: bool = False) -> list:
    """
    Semantic search within one document.

    Raises EmbeddingMismatchError if the embedding backend changed since the
    collection was built — callers must surface that rather than silently
    dropping to a keyword-free fallback.
    """
    collection = get_or_create_collection(session_id)
    count = collection.count()
    if count == 0:
        return []

    safe_source = sanitize_id(doc_id)
    question_embedding = _embed_with_guard([question], session_id, allow_register=False)

    try:
        results = collection.query(
            query_embeddings=question_embedding,
            n_results=min(top_k, count),
            where={"source": safe_source},
        )
        if results and results["documents"]:
            if include_metadata:
                documents = results["documents"][0]
                metadatas = results.get("metadatas", [[]])[0]
                packed = []
                for doc, meta in zip(documents, metadatas):
                    packed.append({
                        "text": doc,
                        "chunk_index": (meta or {}).get("chunk_index", 0),
                        "filename": (meta or {}).get("original_filename", ""),
                    })
                return packed
            return results["documents"][0]
    except Exception as e:
        _log(f"⚠️ Search error for '{doc_id}': {e}")
    return []


def clear_index(session_id: str, doc_id: str = None):
    collection = get_or_create_collection(session_id)
    if doc_id:
        safe_source = sanitize_id(doc_id)
        try:
            collection.delete(where={"source": safe_source})
        except Exception as exc:
            _log(f"⚠️ Could not delete index entries for '{doc_id}': {exc}")
        return

    with _session_lock:
        client = _session_clients.get(session_id)
    if client is not None:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception as exc:
            _log(f"⚠️ Could not delete collection for session {session_id[:8]}: {exc}")
    with _session_lock:
        _session_embed.pop(session_id, None)


def reset_session_index(session_id: str) -> None:
    """
    Drop everything indexed for a session so it can be rebuilt from scratch.
    Used to recover from EmbeddingMismatchError.
    """
    clear_index(session_id)


def drop_session(session_id: str):
    with _session_lock:
        client = _session_clients.pop(session_id, None)
        _session_embed.pop(session_id, None)
    if client is None:
        return
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception as exc:
        _log(f"⚠️ Could not delete collection while dropping session {session_id[:8]}: {exc}")
