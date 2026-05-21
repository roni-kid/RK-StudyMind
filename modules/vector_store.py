import chromadb
import re
import logging
import warnings
import threading
import requests
import json
import sys

warnings.filterwarnings("ignore", message=".*position_ids.*")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)


def _log(message):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = str(message).encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe)

# =============================================
# 🔍 Vector Store Module — Semantic Search
#
# Embedding backend — dual-mode:
#
#   Priority 1: LM Studio (localhost:1234/v1/embeddings)
#               Used automatically if LM Studio has an
#               embedding model loaded at startup.
#               No Python ML deps, instant ready signal.
#
#   Priority 2: sentence-transformers (local cache)
#               Tries local_files_only=True first so
#               the app NEVER pings the internet if the
#               model is already cached.
#               Downloads only on first-ever launch.
#
# Active backend is stored in _embed_backend and exposed
# via get_embed_backend() for the Home tab status card.
# =============================================

COLLECTION_NAME     = "studymind_docs"
EMBED_MODEL_NAME    = "all-MiniLM-L6-v2"
LM_STUDIO_EMBED_URL = "http://localhost:1234/v1/embeddings"
MAX_SESSION_CLIENTS = 8

# "lmstudio" | "sentence_transformers" | None (still loading)
_embed_backend   = None
_embedding_model = None          # only populated when backend == "sentence_transformers"
_model_ready_evt = threading.Event()
_preload_thread  = None
_session_clients = {}
_model_error     = None
_session_lock    = threading.Lock()  # guards _session_clients for concurrent index calls


# ── ChromaDB helpers ─────────────────────────────────────────────

def _create_client():
    if hasattr(chromadb, "EphemeralClient"):
        return chromadb.EphemeralClient()
    raise RuntimeError(
        "This ChromaDB build does not expose EphemeralClient. "
        "Install a compatible chromadb version."
    )


# ── LM Studio embedding helpers ──────────────────────────────────

def _lmstudio_embed(texts: list) -> list | None:
    """
    Calls LM Studio /v1/embeddings.
    Returns a list of embedding vectors, or None on any failure.
    """
    try:
        r = requests.post(
            LM_STUDIO_EMBED_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"input": texts, "model": "local-model"}),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return [item["embedding"] for item in data.get("data", [])]
    except Exception:
        pass
    return None


def _lmstudio_embedding_available() -> bool:
    """Quick probe — returns True if LM Studio answers an embedding request."""
    result = _lmstudio_embed(["ping"])
    return result is not None and len(result) > 0


# ── sentence-transformers helpers ────────────────────────────────

def _load_st_model(allow_download: bool = False):
    from sentence_transformers import SentenceTransformer
    if allow_download:
        return SentenceTransformer(EMBED_MODEL_NAME)
    else:
        # local_files_only=True — never pings the internet
        return SentenceTransformer(EMBED_MODEL_NAME, local_files_only=True)


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
        # LM Studio went offline — switch to ST fallback live
        _log("⚠️ LM Studio embedding unavailable mid-session, switching to sentence-transformers")
        _embed_backend = "sentence_transformers"
        if _embedding_model is None:
            try:
                _embedding_model = _load_st_model(allow_download=False)
            except Exception:
                _embedding_model = _load_st_model(allow_download=True)

    # sentence-transformers path
    if _embedding_model is None:
        _model_ready_evt.wait(timeout=60)
    if _embedding_model is None:
        raise RuntimeError(
            _model_error or
            "Embedding model unavailable. Start LM Studio with an embedding model "
            "or ensure all-MiniLM-L6-v2 is cached locally."
        )
    return _embedding_model.encode(texts, show_progress_bar=False).tolist()


# ── Startup / preload ────────────────────────────────────────────

def _preload_worker():
    """
    Background thread that picks the best embedding backend:
      1. LM Studio (if available) — instant, no downloads
      2. sentence-transformers local cache — offline, no internet
      3. sentence-transformers download — first-ever launch only
    """
    global _embed_backend, _embedding_model, _model_error

    # ── Try LM Studio first ──
    _log("🔍 Checking LM Studio for embedding model…")
    if _lmstudio_embedding_available():
        _embed_backend = "lmstudio"
        _log("✅ Embedding backend: LM Studio (localhost:1234)")
        _model_ready_evt.set()
        return

    # ── Fall back to sentence-transformers ──
    _log("🔄 LM Studio embedding not available — loading sentence-transformers…")
    try:
        # Try local cache first — avoids ANY internet request
        _embedding_model = _load_st_model(allow_download=False)
        _embed_backend = "sentence_transformers"
        _log("✅ Embedding backend: sentence-transformers (local cache, offline)")
    except Exception:
        # Cache miss — download once
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


def is_model_ready() -> bool:
    """True once an embedding backend is confirmed ready."""
    return _model_ready_evt.is_set()


def get_embed_backend() -> str:
    """
    Returns a human-readable string for the Home tab status card.
    e.g. "LM Studio"  or  "sentence-transformers (local)"
    """
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
                oldest_session_id = next(iter(_session_clients))
                drop_session(oldest_session_id)
            client = _create_client()
            _session_clients[session_id] = client
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


# ── Public API ───────────────────────────────────────────────────

def index_chunks(chunks: list, doc_id: str, filename: str, session_id: str):
    """
    Index chunks into the vector store.
    Runs in a background thread to avoid blocking the Gradio main thread
    (embedding can take several seconds on large documents or slow hardware).
    Blocks the caller until indexing is done and re-raises any exception.
    """
    import queue as _queue
    import threading as _threading

    result_q: _queue.Queue = _queue.Queue()

    def _worker():
        try:
            n = _index_chunks_impl(chunks, doc_id, filename, session_id)
            result_q.put(("ok", n))
        except Exception as exc:
            result_q.put(("err", exc))

    t = _threading.Thread(target=_worker, daemon=True)
    t.start()
    status, value = result_q.get()   # blocks until worker finishes
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
    embeddings = _embed_texts(chunks)

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
    collection = get_or_create_collection(session_id)
    count = collection.count()
    if count == 0:
        return []

    safe_source = sanitize_id(doc_id)
    question_embedding = _embed_texts([question])

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
        collection.delete(where={"source": safe_source})
    else:
        client = _session_clients.get(session_id)
        if client is not None:
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass


def drop_session(session_id: str):
    with _session_lock:
        client = _session_clients.pop(session_id, None)
    if client is None:
        return
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
