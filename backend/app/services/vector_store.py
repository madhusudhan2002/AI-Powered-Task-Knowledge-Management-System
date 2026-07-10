import os
import threading
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.config import settings

_INDEX_PATH = os.path.join(settings.VECTOR_STORE_DIR, "index.faiss")
_EMBEDDING_DIM = 384  # matches all-MiniLM-L6-v2

_lock = threading.Lock()
_model = None
_index = None


def get_model() -> SentenceTransformer:
    """Lazy-load the embedding model once (converts text -> vectors)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_index() -> faiss.Index:
    """Lazy-load (or create) the FAISS index, persisted to disk."""
    global _index
    if _index is None:
        if os.path.exists(_INDEX_PATH):
            _index = faiss.read_index(_INDEX_PATH)
        else:
            # Inner-product index over L2-normalized vectors == cosine similarity
            _index = faiss.IndexFlatIP(_EMBEDDING_DIM)
    return _index


def _save_index():
    faiss.write_index(_index, _INDEX_PATH)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Convert a list of text chunks into L2-normalized embedding vectors."""
    model = get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    # Normalize so inner product == cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    return (vectors / norms).astype("float32")


def add_chunks(chunks: list[str]) -> list[int]:
    """
    Embed and add chunks to the FAISS index.
    Returns the vector_index (position) assigned to each chunk, so callers
    can persist the mapping back to SQL (DocumentChunk.vector_index).
    """
    if not chunks:
        return []
    with _lock:
        index = get_index()
        vectors = embed_texts(chunks)
        start_id = index.ntotal
        index.add(vectors)
        _save_index()
        return list(range(start_id, start_id + len(chunks)))


def search(query: str, top_k: int = 5) -> list[tuple[int, float]]:
    """
    Embed the query and retrieve the top_k most similar chunks by cosine
    similarity. Returns list of (vector_index, score).
    """
    with _lock:
        index = get_index()
        if index.ntotal == 0:
            return []
        query_vec = embed_texts([query])
        k = min(top_k, index.ntotal)
        scores, ids = index.search(query_vec, k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            results.append((int(idx), float(score)))
        return results
