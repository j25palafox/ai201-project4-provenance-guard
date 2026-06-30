import os
from dotenv import load_dotenv

load_dotenv()

# Groq / LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"

# File paths
DATA_DIR = "data"
LOG_DIR = "logs"

SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.jsonl")
APPEALS_FILE = os.path.join(DATA_DIR, "appeals.jsonl")
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit_log.jsonl")

# Attribution labels
ATTRIBUTION_RESULTS = {
    "likely_ai",
    "likely_human",
    "uncertain",
}

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.25

# Rate limiting
ANALYZE_RATE_LIMIT = "10 per minute"
APPEALS_RATE_LIMIT = "5 per minute"
LOG_RATE_LIMIT = "30 per minute"