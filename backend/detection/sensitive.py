"""
Sensitive Data Detection Engine
Uses regex patterns to find PII and secrets in generated outputs.
"""
from typing import List
import re

PATTERNS = {
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone_us": r"\b(\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b",
    "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "api_key": r"\b(?:sk|pk|api|key|token)[-_]?[A-Za-z0-9]{20,}\b",
    "aws_key": r"\bAKIA[0-9A-Z]{16}\b",
    "password_like": r"(?i)(?:password|passwd|pwd)\s*[:=]\s*\S+",
    "jwt_token": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "private_key": r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
}


def _mask(value: str) -> str:
    """Partially mask sensitive value for display."""
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-3:]


def run_sensitive_data_detection(generated_texts: List[str]) -> dict:
    findings = []
    type_counts = {k: 0 for k in PATTERNS}

    for i, text in enumerate(generated_texts):
        for data_type, pattern in PATTERNS.items():
            for match in re.finditer(pattern, text):
                value = match.group()
                context_start = max(0, match.start() - 40)
                context_end = min(len(text), match.end() + 40)
                findings.append({
                    "type": data_type,
                    "masked_value": _mask(value),
                    "context": text[context_start:context_end],
                    "text_index": i,
                })
                type_counts[data_type] += 1

    detected = len(findings) > 0

    return {
        "sensitive_data_detected": detected,
        "total_findings": len(findings),
        "type_breakdown": {k: v for k, v in type_counts.items() if v > 0},
        "sensitive_findings": findings[:100],  # cap at 100
    }
