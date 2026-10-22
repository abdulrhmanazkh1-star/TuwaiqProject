import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "compatibilitymatch-dev-key")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///compatibilitymatch.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LLM_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
    ).rstrip("/")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    # Standard paid-tier estimate for gemini-3.5-flash-lite; override as needed.
    LLM_INPUT_COST_PER_1M = float(os.getenv("LLM_INPUT_COST_PER_1M", "0.30"))
    LLM_OUTPUT_COST_PER_1M = float(os.getenv("LLM_OUTPUT_COST_PER_1M", "2.50"))
    SCORING_VERSION = "cm-score-v2"
    ALERT_ON_TRACK = 0.90
    ALERT_NEEDS_ATTENTION = 0.70
    LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
    LLM_RETRY_ATTEMPTS = int(os.getenv("LLM_RETRY_ATTEMPTS", "2"))
