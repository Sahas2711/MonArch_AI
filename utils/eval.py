import json
import os
from datetime import datetime
from utils.logger import log


def run_eval(query: str, expected_answer: str, actual_answer: str, context: str = "") -> dict:
    """
    Run a basic evaluation comparing expected vs actual answers.

    Returns:
        dict with score, matches, and details
    """
    score = 0.0
    details = []

    # Exact match check
    if expected_answer.lower().strip() == actual_answer.lower().strip():
        score += 1.0
        details.append("Exact match found.")
    else:
        # Partial word overlap
        expected_words = set(expected_answer.lower().split())
        actual_words = set(actual_answer.lower().split())
        if expected_words:
            overlap = len(expected_words & actual_words) / len(expected_words)
            score += overlap
            details.append(f"Word overlap: {overlap:.2%}")

    # Length similarity check
    len_ratio = min(len(actual_answer), len(expected_answer)) / max(len(actual_answer), len(expected_answer), 1)
    score = (score + len_ratio) / 2

    result = {
        "query": query,
        "score": round(score, 3),
        "passed": score >= 0.5,
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
    }

    log.info("Eval result for query '%s': score=%.3f, passed=%s", query[:50], score, result["passed"])
    return result
