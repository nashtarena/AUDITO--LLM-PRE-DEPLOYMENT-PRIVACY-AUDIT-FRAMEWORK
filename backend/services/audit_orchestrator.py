"""
Audit Orchestrator
Runs all 6 analysis engines and returns combined results.
"""
from typing import List
from utils.logger import logger

import detection.exact_match
import detection.sensitive
import exposure.engine
import membership.engine
import scoring.engine
import similarity.engine


def run_full_audit(
    reference_texts: List[str],
    generated_texts: List[str],
    user_canaries: List[str] = None,
    progress_callback=None,  # callable(percent: int)
) -> dict:
    """
    Runs the full audit pipeline.
    Returns a dict matching the AuditResult model fields.
    """
    def _progress(pct: int, label: str):
        logger.info(f"Audit progress {pct}% - {label}")
        if progress_callback:
            progress_callback(pct)

    # --- 1. Exact Match ---
    _progress(10, "Running exact match detection")
    from detection.exact_match import run_exact_match
    exact_result = run_exact_match(reference_texts, generated_texts)

    # --- 2. Semantic Similarity ---
    _progress(30, "Running semantic similarity (FAISS)")
    from similarity.engine import run_semantic_similarity
    semantic_result = run_semantic_similarity(reference_texts, generated_texts)

    # --- 3. Membership Inference ---
    _progress(55, "Running membership inference")
    from membership.engine import run_membership_inference
    membership_result = run_membership_inference(reference_texts, generated_texts)

    # --- 4. Canary Exposure ---
    _progress(70, "Running canary exposure testing")
    from exposure.engine import run_canary_exposure
    canary_result = run_canary_exposure(generated_texts, user_canaries)

    # --- 5. Sensitive Data Detection ---
    _progress(82, "Running sensitive data detection")
    from detection.sensitive import run_sensitive_data_detection
    sensitive_result = run_sensitive_data_detection(generated_texts)

    # --- 6. Risk Scoring ---
    _progress(93, "Computing risk score")
    from scoring.engine import compute_risk_score
    risk_result = compute_risk_score(
        exact_match_score=exact_result["exact_match_score"],
        semantic_similarity_score=semantic_result["semantic_similarity_score"],
        membership_probability=membership_result["membership_probability"],
        canary_exposure_score=canary_result["canary_exposure_score"],
        sensitive_data_detected=sensitive_result["sensitive_data_detected"],
        total_sensitive_findings=sensitive_result["total_findings"],
    )

    _progress(100, "Audit complete")

    return {
        # Exact match
        "exact_match_score": exact_result["exact_match_score"],
        "matched_records": exact_result["matched_records"],
        "ngram_overlap_score": exact_result["ngram_overlap_score"],

        # Semantic
        "semantic_similarity_score": semantic_result["semantic_similarity_score"],
        "top_matches": semantic_result["top_matches"],

        # Membership
        "membership_probability": membership_result["membership_probability"],

        # Canary
        "canary_exposure_score": canary_result["canary_exposure_score"],
        "canary_hits": canary_result["canary_hits"],

        # Sensitive data
        "sensitive_data_detected": sensitive_result["sensitive_data_detected"],
        "sensitive_findings": sensitive_result["sensitive_findings"],

        # Risk
        "risk_score": risk_result["risk_score"],
        "risk_level": risk_result["risk_level"],
    }
