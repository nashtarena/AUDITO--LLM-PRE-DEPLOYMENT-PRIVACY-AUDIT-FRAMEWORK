"""
Exact Match Detection Engine
- Exact string matching
- N-gram overlap (BLEU-style)
- Levenshtein similarity
"""
from typing import List, Tuple
import Levenshtein
from collections import Counter


def _ngrams(text: str, n: int) -> List[str]:
    tokens = text.lower().split()
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def _ngram_overlap(ref: str, gen: str, n: int = 3) -> float:
    ref_grams = Counter(_ngrams(ref, n))
    gen_grams = Counter(_ngrams(gen, n))
    if not gen_grams:
        return 0.0
    overlap = sum((ref_grams & gen_grams).values())
    return overlap / max(sum(gen_grams.values()), 1)


def _levenshtein_similarity(a: str, b: str) -> float:
    dist = Levenshtein.distance(a.lower(), b.lower())
    max_len = max(len(a), len(b), 1)
    return 1.0 - dist / max_len


def run_exact_match(
    reference_texts: List[str],
    generated_texts: List[str],
) -> dict:
    ref_set = {t.strip().lower() for t in reference_texts}

    exact_matches = 0
    ngram_scores = []
    levenshtein_scores = []
    matched_pairs = []

    for gen in generated_texts:
        gen_clean = gen.strip()
        gen_lower = gen_clean.lower()

        # Exact match
        is_exact = gen_lower in ref_set
        if is_exact:
            exact_matches += 1

        # N-gram overlap against all refs (take max)
        best_ngram = max((_ngram_overlap(ref, gen_clean) for ref in reference_texts), default=0.0)
        ngram_scores.append(best_ngram)

        # Levenshtein against all refs (take max)
        best_lev = max((_levenshtein_similarity(ref, gen_clean) for ref in reference_texts), default=0.0)
        levenshtein_scores.append(best_lev)

        if is_exact or best_lev > 0.85:
            matched_pairs.append({
                "generated": gen_clean[:200],
                "exact": is_exact,
                "levenshtein_score": round(best_lev, 4),
                "ngram_score": round(best_ngram, 4),
            })

    total = len(generated_texts) or 1
    exact_match_score = exact_matches / total
    avg_ngram = sum(ngram_scores) / len(ngram_scores) if ngram_scores else 0.0

    return {
        "exact_match_score": round(exact_match_score, 4),
        "matched_records": exact_matches,
        "ngram_overlap_score": round(avg_ngram, 4),
        "matched_pairs": matched_pairs[:50],  # cap at 50 for storage
    }
