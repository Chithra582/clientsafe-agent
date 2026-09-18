"""Enterprise Backend configuration settings.

Integrates:
- Structured Pydantic validation
- Multi-tier secrets management (Vault, Docker secrets, Environment)
- Configurable database connection (PostgreSQL / SQLite)
- Enterprise event bus options (RabbitMQ / Redis / Memory)
"""

import os
from pathlib import Path
from typing import Optional
from backend.secrets_manager import secrets_manager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOSSIERS_DIR = DATA_DIR / "dossiers"
UPLOADS_DIR = DATA_DIR / "uploads"

# Runtime directories
DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Server Settings
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Database Configuration (supports PostgreSQL, MySQL, SQLite)
DEFAULT_SQLITE_URL = f"sqlite:///{DATA_DIR / 'clinsafe.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
DB_PATH = DATA_DIR / "clinsafe.db"

# Message Broker / Event Bus Configuration
EVENT_BROKER_URL = os.getenv("EVENT_BROKER_URL", "memory://")  # Supports amqp:// or redis://
USE_EXTERNAL_BROKER = os.getenv("USE_EXTERNAL_BROKER", "false").lower() == "true"

# Security & External AI API Secrets (Resolved via SecretsManager)
LYZR_API_KEY = secrets_manager.get("LYZR_API_KEY", "")
LYZR_AGENT_ID = secrets_manager.get("LYZR_AGENT_ID", "default-protocol-agent")
LYZR_AGENT_ENDPOINT = secrets_manager.get("LYZR_AGENT_ENDPOINT", "https://agent-prod.lyzr.app/v2/chat")

OPENAI_API_KEY = secrets_manager.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = secrets_manager.get("ANTHROPIC_API_KEY", "")

# Webhook & Governance Configuration
HITL_WEBHOOK_URL = os.getenv("HITL_WEBHOOK_URL", f"http://127.0.0.1:{PORT}/api/webhook/hitl")
HITL_CONFIDENCE_THRESHOLD = float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "90.0"))
