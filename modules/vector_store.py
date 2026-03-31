import chromadb
import os
import re
import logging
import warnings

# Suppress the harmless "UNEXPECTED key" warning from sentence-transformers
warnings.filterwarnings("ignore", message=".*position_ids.*")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from sentence_transformers import SentenceTransformer

# =============================================
# 🔍 Vector Store Module — Semantic Search
# Fix #3: sanitize ChromaDB IDs from filenames
# =============================================

print("🔄 Loading embedding model... (first time may take a minute)")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded!")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
chroma_client = chromadb.PersistentClient(path=DB_PATH)
COLLECTION_NAME = "studymind_docs"


def sanitize_id(text: str) -> str:
    """Sanitizes a string for safe use as a ChromaDB ID."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', text)


def get_or_create_collection():
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def index_chunks(chunks: list, filename: str):
    collection = get_or_create_collection()
    safe_source = sanitize_id(filename)

    try:
        existing = collection.get(where={"source": safe_source})
        if existing["ids"]:
            collection.delete(where={"source": safe_source})
    except Exception as e:
        print(f"⚠️ Could not clear old index for '{filename}': {e}")

    if not chunks:
        return 0

    print(f"🔄 Indexing {len(chunks)} chunks from '{filename}'...")
    embeddings = embedding_model.encode(chunks, show_progress_bar=False).tolist()

    ids = [f"{safe_source}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": safe_source, "original_filename": filename, "chunk_index": i}
                 for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    print(f"✅ Indexed {len(chunks)} chunks successfully!")
    return len(chunks)


def search_similar_chunks(question: str, filename: str, top_k: int = 3) -> list:
    collection = get_or_create_collection()
    count = collection.count()
    if count == 0:
        return []

    safe_source = sanitize_id(filename)
    question_embedding = embedding_model.encode([question]).tolist()

    try:
        results = collection.query(
            query_embeddings=question_embedding,
            n_results=min(top_k, count),
            where={"source": safe_source}
        )
        if results and results["documents"]:
            return results["documents"][0]
    except Exception as e:
        print(f"⚠️ Search error for '{filename}': {e}")
    return []


def clear_index(filename: str = None):
    collection = get_or_create_collection()
    if filename:
        safe_source = sanitize_id(filename)
        collection.delete(where={"source": safe_source})
    else:
        chroma_client.delete_collection(COLLECTION_NAME)
