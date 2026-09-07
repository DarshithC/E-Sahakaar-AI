import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "eshakara_readonly")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "eshakara")

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