"""
Membership Inference Engine
Estimates whether generated samples were in the training data.

Approach: threshold scoring based on:
1. Token frequency in reference corpus (common tokens = higher probability)
2. Perplexity-proxy: average word log-frequency
3. Unique phrase overlap ratio
"""
from typing import List
import math
from collections import Counter


def _build_token_freq(texts: List[str]) -> Counter:
    tokens = []
    for t in texts:
        tokens.extend(t.lower().split())
    return Counter(tokens)


def _log_freq_score(text: str, token_freq: Counter, total_tokens: int) -> float:
    """Higher score = more likely to be from training data."""
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    scores = []
    for token in tokens:
        freq = token_freq.get(token, 0)
        # Probability with add-1 smoothing
        prob = (freq + 1) / (total_tokens + len(token_freq))
        scores.append(-math.log(prob))  # negative log-likelihood
    # Lower perplexity-proxy = more likely memorized
    avg_nll = sum(scores) / len(scores)
    # Normalize to 0-1: lower NLL → higher membership probability
    # Typical NLL range: [3, 12]. We invert and normalize.
    normalized = max(0.0, min(1.0, 1.0 - (avg_nll - 3) / 9))
    return normalized


def _unique_phrase_overlap(text: str, ref_phrases: set, n: int = 4) -> float:
    tokens = text.lower().split()
    if len(tokens) < n:
        return 0.0
    gen_phrases = {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}
    if not gen_phrases:
        return 0.0
    overlap = gen_phrases & ref_phrases
    return len(overlap) / len(gen_phrases)


def run_membership_inference(
    reference_texts: List[str],
    generated_texts: List[str],
) -> dict:
    token_freq = _build_token_freq(reference_texts)
    total_tokens = sum(token_freq.values())

    # Build 4-gram phrase set from reference
    ref_phrases = set()
    for text in reference_texts:
        tokens = text.lower().split()
        for i in range(len(tokens) - 3):
            ref_phrases.add(" ".join(tokens[i:i+4]))

    member_scores = []

    for gen in generated_texts:
        freq_score = _log_freq_score(gen, token_freq, total_tokens)
        phrase_score = _unique_phrase_overlap(gen, ref_phrases)
        # Weighted combination
        combined = 0.5 * freq_score + 0.5 * phrase_score
        member_scores.append(combined)

    avg_prob = sum(member_scores) / len(member_scores) if member_scores else 0.0

    return {
        "membership_probability": round(avg_prob, 4),
        "high_membership_count": sum(1 for s in member_scores if s > 0.7),
        "score_distribution": {
            "low": sum(1 for s in member_scores if s <= 0.4),
            "medium": sum(1 for s in member_scores if 0.4 < s <= 0.7),
            "high": sum(1 for s in member_scores if s > 0.7),
        },
    }
