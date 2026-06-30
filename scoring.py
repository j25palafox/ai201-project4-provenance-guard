from config import HIGH_CONFIDENCE_THRESHOLD, LOW_CONFIDENCE_THRESHOLD


def clamp_score(score: float) -> float:
    """
    Keep confidence values inside the valid 0.0 to 1.0 range.
    """
    return max(0.0, min(1.0, score))

        
def weighted_average(scores: list[float], weights: list[float]) -> float:
    """
    Return the weighted average of multiple signal scores.
    """
    if len(scores) != len(weights):
        raise ValueError("Scores and weights must have the same length.")

    total_weight = sum(weights)

    if total_weight == 0:
        raise ValueError("Total weight cannot be zero.")

    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    return clamp_score(weighted_sum / total_weight)


def classify_from_ai_probability(ai_probability: float) -> dict:
    """
    Convert an AI-likelihood score into a final attribution result.

    ai_probability means:
    - close to 1.0: likely AI-generated or AI-shaped
    - close to 0.0: likely human-written
    - near the middle: uncertain
    """
    ai_probability = clamp_score(ai_probability)

    if ai_probability >= HIGH_CONFIDENCE_THRESHOLD:
        return {
            "result": "likely_ai",
            "confidence": round(ai_probability, 2),
            "label_type": "high_confidence_ai",
        }

    if ai_probability <= LOW_CONFIDENCE_THRESHOLD:
        human_confidence = 1 - ai_probability

        return {
            "result": "likely_human",
            "confidence": round(human_confidence, 2),
            "label_type": "high_confidence_human",
        }

    return {
        "result": "uncertain",
        "confidence": round(max(ai_probability, 1 - ai_probability), 2),
        "label_type": "uncertain",
    }


def score_attribution(llm_signal: dict, stylometric_signal: dict) -> dict:
    """
    Combine the LLM signal and stylometric signal into one final attribution decision.

    Expected signal format:
    {
        "score": 0.72,
        "explanation": "..."
    }

    The score should represent AI likelihood:
    - 0.0 = strongly human-like
    - 1.0 = strongly AI-like
    """

    llm_score = clamp_score(float(llm_signal.get("score", 0.5)))
    stylometric_score = clamp_score(float(stylometric_signal.get("score", 0.5)))

    combined_ai_probability = weighted_average(
        scores=[llm_score, stylometric_score],
        weights=[0.65, 0.35],
    )

    classification = classify_from_ai_probability(combined_ai_probability)

    return {
        "result": classification["result"],
        "confidence": classification["confidence"],
        "label_type": classification["label_type"],
        "ai_probability": round(combined_ai_probability, 2),
        "signals": {
            "llm_signal": {
                "score": round(llm_score, 2),
                "explanation": llm_signal.get("explanation", ""),
            },
            "stylometric_signal": {
                "score": round(stylometric_score, 2),
                "explanation": stylometric_signal.get("explanation", ""),
            },
        },
    }