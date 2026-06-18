"""
Risk Scoring Engine
Combines scores from all modules into a single 0-100 risk score.
"""


WEIGHTS = {
    "exact_match": 0.25,
    "semantic_similarity": 0.25,
    "membership_probability": 0.20,
    "canary_exposure": 0.15,
    "sensitive_data": 0.15,
}


def _determine_level(score: float) -> str:
    if score <= 25:
        return "Low"
    elif score <= 50:
        return "Medium"
    elif score <= 75:
        return "High"
    else:
        return "Critical"


def compute_risk_score(
    exact_match_score: float,       # 0-1
    semantic_similarity_score: float,  # 0-1
    membership_probability: float,     # 0-1
    canary_exposure_score: float,      # 0-100
    sensitive_data_detected: bool,
    total_sensitive_findings: int = 0,
) -> dict:
    # Normalize canary score to 0-1
    canary_normalized = canary_exposure_score / 100.0

    # Sensitive data: binary + volume boost
    sensitive_score = 0.0
    if sensitive_data_detected:
        # Base 0.5 + up to 0.5 more based on finding count (capped at 20)
        sensitive_score = min(1.0, 0.5 + (total_sensitive_findings / 20) * 0.5)

    weighted = (
        WEIGHTS["exact_match"] * exact_match_score
        + WEIGHTS["semantic_similarity"] * semantic_similarity_score
        + WEIGHTS["membership_probability"] * membership_probability
        + WEIGHTS["canary_exposure"] * canary_normalized
        + WEIGHTS["sensitive_data"] * sensitive_score
    )

    risk_score = round(weighted * 100, 1)
    risk_level = _determine_level(risk_score)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "component_scores": {
            "exact_match": round(exact_match_score * 100, 1),
            "semantic_similarity": round(semantic_similarity_score * 100, 1),
            "membership_probability": round(membership_probability * 100, 1),
            "canary_exposure": round(canary_exposure_score, 1),
            "sensitive_data": round(sensitive_score * 100, 1),
        },
    }
