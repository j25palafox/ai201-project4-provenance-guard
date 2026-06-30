import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from audit import log_appeal
from config import APPEALS_FILE, SUBMISSIONS_FILE


def current_timestamp() -> str:
    """
    Return a UTC timestamp in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


def ensure_file_exists(file_path: str) -> None:
    """
    Make sure the parent directory and target JSONL file exist.
    """
    directory = os.path.dirname(file_path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8"):
            pass


def read_jsonl(file_path: str) -> list[dict[str, Any]]:
    """
    Read a JSONL file into a list of dictionaries.
    """
    ensure_file_exists(file_path)

    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            records.append(json.loads(line))

    return records


def write_jsonl(file_path: str, records: list[dict[str, Any]]) -> None:
    """
    Rewrite a JSONL file with a list of dictionaries.

    This is useful when updating submission status.
    """
    ensure_file_exists(file_path)

    with open(file_path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


def append_jsonl(file_path: str, record: dict[str, Any]) -> None:
    """
    Append one dictionary as one JSON object line.
    """
    ensure_file_exists(file_path)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def find_submission(submission_id: str) -> dict[str, Any] | None:
    """
    Find a submission by ID.
    """
    submissions = read_jsonl(SUBMISSIONS_FILE)

    for submission in submissions:
        if submission.get("submission_id") == submission_id:
            return submission

    return None


def update_submission_status(submission_id: str, new_status: str) -> dict[str, Any] | None:
    """
    Update a submission's status in the submissions JSONL file.
    """
    submissions = read_jsonl(SUBMISSIONS_FILE)
    updated_submission = None

    for submission in submissions:
        if submission.get("submission_id") == submission_id:
            submission["status"] = new_status
            submission["updated_at"] = current_timestamp()
            updated_submission = submission
            break

    if updated_submission is None:
        return None

    write_jsonl(SUBMISSIONS_FILE, submissions)

    return updated_submission


def submit_appeal(submission_id: str, creator_reasoning: str) -> dict[str, Any]:
    """
    Submit an appeal for a classification decision.

    The appeal:
    - stores the creator's reasoning
    - updates the submission status to under_review
    - logs the appeal in the audit log
    """
    creator_reasoning = creator_reasoning.strip()

    if not creator_reasoning:
        raise ValueError("Appeal reasoning is required.")

    original_submission = find_submission(submission_id)

    if original_submission is None:
        raise ValueError("Submission not found.")

    appeal_id = str(uuid.uuid4())

    updated_submission = update_submission_status(
        submission_id=submission_id,
        new_status="under_review",
    )

    appeal_record = {
        "appeal_id": appeal_id,
        "submission_id": submission_id,
        "creator_reasoning": creator_reasoning,
        "status": "under_review",
        "created_at": current_timestamp(),
        "original_result":original_submission.get("result", "unknown"),
        "original_confidence":original_submission.get("confidence", 0.0),
    }

    append_jsonl(APPEALS_FILE, appeal_record)

    audit_entry = log_appeal(
        appeal_id=appeal_id,
        submission_id=submission_id,
        creator_reasoning=creator_reasoning,
        original_result=original_submission.get("result", "unknown"),
        original_confidence=original_submission.get("confidence", 0.0),
        updated_status="under_review",
    )

    return {
        "appeal": appeal_record,
        "submission": updated_submission,
        "audit_entry": audit_entry,
    }