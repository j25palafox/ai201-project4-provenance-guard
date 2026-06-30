import json
import re
from statistics import mean

from groq import Groq

from config import GROQ_API_KEY, LLM_MODEL
from scoring import clamp_score, score_attribution


def analyze_with_llm(content: str) -> dict:
    """
    Signal 1: Use a Groq-hosted LLM as an attribution judge.

    Returns:
    {
        "score": float,
        "explanation": str
    }

    The score represents AI likelihood:
    - 0.0 = strongly human-like
    - 1.0 = strongly AI-like
    - 0.5 = uncertain
    """
    if not GROQ_API_KEY:
        return {
            "score": 0.5,
            "explanation": "Groq API key was not configured, so the LLM signal returned neutral uncertainty.",
        }

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """
You are an attribution analysis assistant for a creative writing platform.

Your job is not to prove authorship. Your job is to estimate whether a submitted text
appears more likely to be AI-generated/AI-shaped or primarily human-written.

Return ONLY valid JSON in this exact format:
{
  "score": 0.0,
  "explanation": "brief explanation"
}

Rules:
- score must be a number between 0 and 1.
- score means AI likelihood.
- Use values near 0.5 when evidence is mixed or weak.
- Do not claim certainty.
- Do not accuse the creator of misconduct.
- Focus on observable writing features.
"""

    user_prompt = f"""
Analyze this submitted creative text:

\"\"\"
{content}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        raw_text = response.choices[0].message.content.strip()
        parsed = json.loads(raw_text)

        return {
            "score": clamp_score(float(parsed.get("score", 0.5))),
            "explanation": parsed.get("explanation", "No explanation provided."),
        }

    except Exception as error:
        return {
            "score": 0.5,
            "explanation": f"LLM signal failed and returned neutral uncertainty: {str(error)}",
        }


def split_sentences(content: str) -> list[str]:
    """
    Basic sentence splitter for stylometric analysis.
    """
    sentences = re.split(r"[.!?]+", content)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def split_words(content: str) -> list[str]:
    """
    Basic word tokenizer.
    """
    return re.findall(r"\b[a-zA-Z']+\b", content.lower())


def analyze_with_stylometry(content: str) -> dict:
    """
    Signal 2: Analyze surface-level writing patterns.

    This simple heuristic signal looks at:
    - sentence length consistency
    - vocabulary variety
    - punctuation density
    - formulaic transition language

    Returns:
    {
        "score": float,
        "explanation": str
    }
    """
    sentences = split_sentences(content)
    words = split_words(content)

    if not words or not sentences:
        return {
            "score": 0.5,
            "explanation": "Not enough text to calculate meaningful stylometric features.",
        }

    sentence_lengths = [len(split_words(sentence)) for sentence in sentences]
    avg_sentence_length = mean(sentence_lengths)

    sentence_length_variance = mean(
        [(length - avg_sentence_length) ** 2 for length in sentence_lengths]
    )

    unique_words = set(words)
    vocabulary_variety = len(unique_words) / len(words)

    punctuation_marks = re.findall(r"[,;:!?-]", content)
    punctuation_density = len(punctuation_marks) / max(len(words), 1)

    transition_words = {
        "furthermore",
        "moreover",
        "therefore",
        "however",
        "additionally",
        "ultimately",
        "overall",
        "in conclusion",
    }

    lowered_content = content.lower()
    transition_count = sum(
        lowered_content.count(transition)
        for transition in transition_words
    )

    transition_density = transition_count / max(len(sentences), 1)

    score = 0.5
    reasons = []

    if avg_sentence_length > 22:
        score += 0.10
        reasons.append("long average sentence length")

    if sentence_length_variance < 20 and len(sentences) >= 4:
        score += 0.10
        reasons.append("highly consistent sentence lengths")

    if vocabulary_variety < 0.45 and len(words) >= 80:
        score += 0.10
        reasons.append("lower vocabulary variety")

    if punctuation_density < 0.08 and len(words) >= 80:
        score += 0.05
        reasons.append("low punctuation density")

    if transition_density > 0.35:
        score += 0.10
        reasons.append("frequent formulaic transition language")

    if vocabulary_variety > 0.65 and sentence_length_variance > 40:
        score -= 0.10
        reasons.append("varied vocabulary and sentence rhythm")

    score = clamp_score(score)

    if reasons:
        explanation = "Stylometric signal noticed: " + ", ".join(reasons) + "."
    else:
        explanation = "Stylometric signal found mixed or weak indicators."

    return {
        "score": score,
        "explanation": explanation,
    }


def analyze_content(content: str) -> dict:
    """
    Run the full multi-signal detection pipeline.

    This is the main function app.py should call from POST /submit.
    """
    llm_signal = analyze_with_llm(content)
    stylometric_signal = analyze_with_stylometry(content)

    return score_attribution(llm_signal, stylometric_signal)