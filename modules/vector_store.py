import chromadb
import os
from sentence_transformers import SentenceTransformer

# =============================================
# 🔍 Vector Store Module — Semantic Search
# Uses ChromaDB + sentence-transformers
# Finds relevant chunks from ANYWHERE in doc
# =============================================

# Load embedding model once (runs locally, no internet needed)
print("🔄 Loading embedding model... (first time may take a minute)")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅ Embedding model loaded!")

# ChromaDB client — stores vectors in the data/ folder
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
chroma_client = chromadb.PersistentClient(path=DB_PATH)

COLLECTION_NAME = "studymind_docs"


def get_or_create_collection():
    """Gets existing collection or creates a new one."""
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # cosine similarity for meaning-based search
    )


def index_chunks(chunks: list, filename: str):
    """
    Takes all chunks from a PDF and stores them as vectors in ChromaDB.
    This is called once after uploading a PDF.
    """
    collection = get_or_create_collection()

    # Clear old documents for this file so we don't get duplicates
    try:
        existing = collection.get(where={"source": filename})
        if existing["ids"]:
            collection.delete(where={"source": filename})
    except:
        pass

    if not chunks:
        return 0

    print(f"🔄 Indexing {len(chunks)} chunks from '{filename}'...")

    # Convert all chunks to vectors in one batch (fast)
    embeddings = embedding_model.encode(chunks, show_progress_bar=False).tolist()

    # Store in ChromaDB with unique IDs
    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    print(f"✅ Indexed {len(chunks)} chunks successfully!")
    return len(chunks)


def search_similar_chunks(question: str, filename: str, top_k: int = 3) -> list:
    """
    Converts the question to a vector and finds the top_k most
    semantically similar chunks from the document — from ANYWHERE in it.
    
    Returns a list of the most relevant text chunks.
    """
    collection = get_or_create_collection()

    # Check if we have any documents indexed
    count = collection.count()
    if count == 0:
        return []

    # Convert question to vector
    question_embedding = embedding_model.encode([question]).tolist()

    # Search ChromaDB for similar chunks
    results = collection.query(
        query_embeddings=question_embedding,
        n_results=min(top_k, count),
        where={"source": filename}
    )

    if results and results["documents"]:
        return results["documents"][0]  # list of top matching chunks
    return []


def clear_index(filename: str = None):
    """Clears all indexed chunks for a file, or the entire collection."""
    collection = get_or_create_collection()
    if filename:
        collection.delete(where={"source": filename})
    else:
        chroma_client.delete_collection(COLLECTION_NAME)
