import chromadb
import re
import logging
import warnings
import threading

warnings.filterwarnings("ignore", message=".*position_ids.*")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

# =============================================
# 🔍 Vector Store Module — Semantic Search
# Uses per-session in-memory collections so
# uploaded document chunks do not persist on disk.
# The embedding model is preloaded in a background
# thread at startup so it's ready immediately.
# =============================================

COLLECTION_NAME = "studymind_docs"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
MAX_SESSION_CLIENTS = 8

_embedding_model  = None          # set by background thread
_model_ready_evt  = threading.Event()   # signals when model is loaded
_preload_thread   = None
_session_clients  = {}
_model_error      = None


def _create_client():
    if hasattr(chromadb, "EphemeralClient"):
        return chromadb.EphemeralClient()
    raise RuntimeError(
        "This ChromaDB build does not expose EphemeralClient. "
        "Install a compatible chromadb version."
    )


def _load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL_NAME)


def _get_model():
    """Returns the embedding model, waiting if it's still loading."""
    global _embedding_model
    if _embedding_model is None:
        # If background preload hasn't started yet, load inline
        if not _preload_thread or not _preload_thread.is_alive():
            print("🔄 Loading embedding model…")
            _embedding_model = _load_model()
            print("✅ Embedding model loaded!")
            _model_ready_evt.set()
        else:
            # Wait for background thread to finish (max 60 s)
            _model_ready_evt.wait(timeout=60)
    if _embedding_model is None:
        raise RuntimeError(
            _model_error or
            "Embedding model is unavailable. Download 'all-MiniLM-L6-v2' locally before starting the app."
        )
    return _embedding_model


def _preload_worker():
    """Background thread: loads the model so it's warm before first use."""
    global _embedding_model, _model_error
    try:
        print("🔄 Loading embedding model in background…")
        _embedding_model = _load_model()
        print("✅ Embedding model ready!")
    except Exception as e:
        _model_error = (
            "Embedding model preload failed. Ensure internet is available on first launch "
            "or that 'all-MiniLM-L6-v2' is already cached locally."
        )
        print(f"⚠️ Background model load failed: {e}")
    finally:
        _model_ready_evt.set()   # always unblock waiters


def preload_model_background():
    """Call once at app startup to begin loading the model in the background."""
    global _preload_thread
    if _preload_thread is None or not _preload_thread.is_alive():
        _preload_thread = threading.Thread(target=_preload_worker, daemon=True)
        _preload_thread.start()


def is_model_ready() -> bool:
    """Returns True once the embedding model has finished loading."""
    return _model_ready_evt.is_set()


def sanitize_id(text: str) -> str:
    """Sanitizes a string for safe use as a ChromaDB ID."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)


def get_or_create_collection(session_id: str):
    if not session_id:
        raise ValueError("session_id is required")
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


def index_chunks(chunks: list, doc_id: str, filename: str, session_id: str):
    collection = get_or_create_collection(session_id)
    safe_source = sanitize_id(doc_id)

    try:
        existing = collection.get(where={"source": safe_source})
        if existing["ids"]:
            collection.delete(where={"source": safe_source})
    except Exception as e:
        print(f"⚠️ Could not clear old index for '{filename}': {e}")

    if not chunks:
        return 0

    print(f"🔄 Indexing {len(chunks)} chunks from '{filename}'…")
    model = _get_model()
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    ids       = [f"{safe_source}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": safe_source, "original_filename": filename, "chunk_index": i}
                 for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    print(f"✅ Indexed {len(chunks)} chunks!")
    return len(chunks)


def search_similar_chunks(question: str, doc_id: str, session_id: str, top_k: int = 3,
                          include_metadata: bool = False) -> list:
    collection = get_or_create_collection(session_id)
    count = collection.count()
    if count == 0:
        return []

    safe_source = sanitize_id(doc_id)
    model = _get_model()
    question_embedding = model.encode([question]).tolist()

    try:
        results = collection.query(
            query_embeddings=question_embedding,
            n_results=min(top_k, count),
            where={"source": safe_source}
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
        print(f"⚠️ Search error for '{doc_id}': {e}")
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
    client = _session_clients.pop(session_id, None)
    if client is None:
        return
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
