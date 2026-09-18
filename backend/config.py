"""Backend configuration settings."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "clinsafe.db"
DOSSIERS_DIR = DATA_DIR / "dossiers"
UPLOADS_DIR = DATA_DIR / "uploads"

# Ensure runtime directories exist
DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Environment settings
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Security / API keys
LYZR_API_KEY = os.getenv("LYZR_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HITL_WEBHOOK_URL = os.getenv("HITL_WEBHOOK_URL", f"http://127.0.0.1:{PORT}/api/webhook/hitl")
