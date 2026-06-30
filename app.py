from flask import Flask, jsonify, request

import uuid

from appeals import append_jsonl, submit_appeal
from audit import read_audit_log, log_attribution_decision
from config import (
    APPEALS_RATE_LIMIT,
    LOG_RATE_LIMIT,
    ANALYZE_RATE_LIMIT,
    SUBMISSIONS_FILE,
)
from labels import get_transparency_label
from detector import analyze_content
from rate_limit import limiter


app = Flask(__name__)

# Attach Flask-Limiter to this Flask app.
limiter.init_app(app)


@app.route("/health", methods=["GET"])
def health():
    """
    Simple health check endpoint.

    This lets us confirm the API is running.
    """
    return jsonify(
        {
            "status": "ok",
            "service": "Provenance Guard",
        }
    ), 200


@app.route("/submit", methods=["POST"])
@limiter.limit(ANALYZE_RATE_LIMIT)
def submit():
    """
    Analyze submitted text for attribution.

    Expected JSON body:
    {
        "text": "Text to analyze...",
        "creator_id": "test-user-1"
    }

    Returns:
    {
        "content_id": "...",
        "creator_id": "...",
        "result": "likely_ai | likely_human | uncertain",
        "confidence": 0.87,
        "label_type": "...",
        "transparency_label": "...",
        "signals": {...},
        "status": "classified"
    }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    text = data.get("text", "")
    creator_id = data.get("creator_id", "")

    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "text is required and must be a non-empty string."}), 400

    if not isinstance(creator_id, str) or not creator_id.strip():
        return jsonify({"error": "creator_id is required."}), 400

    try:
        result = analyze_content(text)
        content_id = str(uuid.uuid4())

        response = {
            "content_id": content_id,
            "creator_id": creator_id,
            "result": result["result"],
            "confidence": result["confidence"],
            "label_type": result["label_type"],
            "transparency_label": get_transparency_label(result["result"]),
            "ai_probability": result["ai_probability"],
            "signals": result["signals"],
            "status": "classified",
        }

        append_jsonl(SUBMISSIONS_FILE, response)

        log_attribution_decision(
            content_id=content_id,
            content_preview=text,
            result=response["result"],
            confidence=response["confidence"],
            label_type=response["label_type"],
            label_text=response["transparency_label"],
            signals=response["signals"],
            status=response["status"],
        )

        return jsonify(response), 200

    except Exception as error:
        return jsonify(
            {
                "error": "Analysis failed.",
                "details": str(error),
            }
        ), 500


@app.route("/appeal", methods=["POST"])
@limiter.limit(APPEALS_RATE_LIMIT)
def appeals():
    """
    Submit an appeal for a previous classification.

    Expected JSON body:
    {
        "content_id": "...",
        "creator_reasoning": "I wrote this myself because..."
    }

    Returns:
    {
        "appeal_id": "...",
        "content_id": "...",
        "status": "under_review",
        ...
    }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    content_id = data.get("content_id", "")
    creator_reasoning = data.get("creator_reasoning", "")

    if not isinstance(content_id, str) or not content_id.strip():
        return jsonify({"error": "content_id is required."}), 400

    if not isinstance(creator_reasoning, str) or not creator_reasoning.strip():
        return jsonify({"error": "creator_reasoning is required."}), 400

    try:
        appeal_result = submit_appeal(
            content_id=content_id,
            creator_reasoning=creator_reasoning,
        )

        return jsonify(appeal_result["appeal"]), 201

    except ValueError as error:
        return jsonify({"error": str(error)}), 404

    except Exception as error:
        return jsonify(
            {
                "error": "Appeal submission failed.",
                "details": str(error),
            }
        ), 500


@app.route("/log", methods=["GET"])
@limiter.limit(LOG_RATE_LIMIT)
def get_log():
    """
    Return structured audit log entries.

    This is useful for demoing that decisions and appeals are recorded.
    """
    try:
        entries = read_audit_log()
        return jsonify(
            {
                "count": len(entries),
                "entries": entries,
            }
        ), 200

    except Exception as error:
        return jsonify(
            {
                "error": "Could not read audit log.",
                "details": str(error),
            }
        ), 500


if __name__ == "__main__":
    app.run(debug=True)