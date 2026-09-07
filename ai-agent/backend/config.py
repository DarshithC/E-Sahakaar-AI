import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from this file's directory, not CWD
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "ai_agent_reader")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourStrongPassword")
DB_NAME = os.getenv("DB_NAME", "esahakara_demo")

AGENT_API_KEY = os.getenv(
    "AGENT_API_KEY",
    "E-Sahakara-Agent-2026"
)

# ============================================================
# CUSTOM AI MODEL SETTINGS
# ============================================================

VALIDATION_CONFIDENCE_THRESHOLD = int(
    os.getenv("VALIDATION_CONFIDENCE_THRESHOLD", "70")
)

ANOMALY_SENSITIVITY = os.getenv(
    "ANOMALY_SENSITIVITY",
    "medium"
).lower()