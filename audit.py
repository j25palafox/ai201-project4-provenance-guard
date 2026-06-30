import json
import os
from datetime import datetime, timezone
from typing import Any

from config import AUDIT_LOG_FILE


def current_timestamp() -> str:
    """
    Return the current UTC time in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_log_file_exists() -> None:
    """
    Make sure the log directory and audit log file exist.
    """
    log_dir = os.path.dirname(AUDIT_LOG_FILE)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    if not os.path.exists(AUDIT_LOG_FILE):
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8"):
            pass


def append_audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Append one structured audit entry to the JSONL audit log.

    JSONL means:
    - one JSON object per line
    - easy to append
    - easy to inspect with tail
    - easy to parse later
    """
    ensure_log_file_exists()

    entry_with_timestamp = {
        "timestamp": current_timestamp(),
        **entry,
    }

    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry_with_timestamp, ensure_ascii=False) + "\n")

    return entry_with_timestamp


def log_attribution_decision(
    content_id: str,
    content_preview: str,
    result: str,
    confidence: float,
    label_type: str,
    label_text: str,
    signals: dict[str, Any],
    status: str = "classified",
) -> dict[str, Any]:
    """
    Log an attribution decision from the analysis pipeline.
    """
    entry = {
        "event_type": "content_classified",
        "content_id": content_id,
        "content_preview": content_preview[:200],
        "result": result,
        "confidence": confidence,
        "label_type": label_type,
        "label_text": label_text,
        "signals": signals,
        "status": status,
    }

    return append_audit_entry(entry)


def log_appeal(
    appeal_id: str,
    content_id: str,
    creator_reasoning: str,
    original_result: str,
    original_confidence: float,
    updated_status: str = "under_review",
) -> dict[str, Any]:
    """
    Log a creator appeal connected to an original attribution decision.
    """
    entry = {
        "event_type": "appeal_submitted",
        "appeal_id": appeal_id,
        "content_id": content_id,
        "creator_reasoning": creator_reasoning,
        "original_result": original_result,
        "original_confidence": original_confidence,
        "updated_status": updated_status,
    }

    return append_audit_entry(entry)


def read_audit_log(limit: int = 20) -> list[dict[str, Any]]:
    """
    Read the most recent audit log entries.

    This will be useful for GET /log later.
    """
    ensure_log_file_exists()

    entries = []

    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            entries.append(json.loads(line))

    return entries[-limit:]