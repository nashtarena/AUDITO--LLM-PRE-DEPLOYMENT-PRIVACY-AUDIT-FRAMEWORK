"""
Semantic Similarity Engine
- Embeds texts with sentence-transformers (all-mpnet-base-v2)
- Builds FAISS index from reference texts
- Finds nearest neighbors for each generated text
"""
from typing import List, Tuple
import numpy as np

# Lazy imports to avoid slow startup
_model = None
_faiss = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-mpnet-base-v2")
    return _model


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss
        _faiss = faiss
    return _faiss


def _embed(texts: List[str]) -> np.ndarray:
    model = _get_model()
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.astype("float32")


def run_semantic_similarity(
    reference_texts: List[str],
    generated_texts: List[str],
    top_k: int = 3,
    similarity_threshold: float = 0.80,
) -> dict:
    faiss = _get_faiss()

    # Embed
    ref_embeddings = _embed(reference_texts)
    gen_embeddings = _embed(generated_texts)

    # Build FAISS index (inner product = cosine similarity since normalized)
    dim = ref_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(ref_embeddings)

    # Search
    distances, indices = index.search(gen_embeddings, min(top_k, len(reference_texts)))

    top_matches = []
    all_scores = []

    for i, (gen_text, dists, idxs) in enumerate(zip(generated_texts, distances, indices)):
        best_score = float(dists[0]) if len(dists) > 0 else 0.0
        all_scores.append(best_score)

        if best_score >= similarity_threshold:
            top_matches.append({
                "generated": gen_text[:300],
                "reference": reference_texts[idxs[0]][:300],
                "similarity_score": round(best_score, 4),
                "top_k_matches": [
                    {
                        "reference": reference_texts[idx][:200],
                        "score": round(float(dist), 4),
                    }
                    for dist, idx in zip(dists, idxs)
                    if idx < len(reference_texts)
                ],
            })

    avg_score = float(np.mean(all_scores)) if all_scores else 0.0

    return {
        "semantic_similarity_score": round(avg_score, 4),
        "top_matches": top_matches[:30],  # cap at 30
        "high_similarity_count": len(top_matches),
    }


def save_faiss_index(reference_texts: List[str], index_path: str):
    """Save FAISS index to disk for reuse."""
    import faiss, os
    embeddings = _embed(reference_texts)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
