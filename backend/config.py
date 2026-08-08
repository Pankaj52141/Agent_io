"""
Configuration module for the Financial Data AI Agent.
Central place for all settings, paths, and constants.
"""
import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # Agentio/
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = BASE_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"
UNDERSTANDING_DIR = PROCESSED_DIR / "understanding"
EMBEDDINGS_DIR = PROCESSED_DIR / "embeddings"
FEEDBACK_DIR = PROCESSED_DIR / "feedback"

# Create directories
for d in [CHUNKS_DIR, UNDERSTANDING_DIR, EMBEDDINGS_DIR, FEEDBACK_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── OpenAI ──────────────────────────────────────────────
# Required: set in environment or via a .env file when running locally
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"
EMBEDDING_DIM = 1536

# ─── Auth / JWT ──────────────────────────────────────────
# For production, set `JWT_SECRET` in the environment. A default placeholder
# is kept to avoid hard crashes during local development, but you should
# provide a strong secret when deploying to Render.
JWT_SECRET = os.environ.get("JWT_SECRET", "your-jwt-secret-key-here")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8

# ─── Chunking ────────────────────────────────────────────
CHUNK_SIZE = 800       # target tokens per chunk
CHUNK_OVERLAP = 100    # overlap tokens between chunks

# ─── RBAC Data Categories ──────
DATA_CATEGORIES = [
    "revenue",
    "expenses",
    "assets_liabilities",
    "cash_flow",
    "earnings",
    "segments",
    "compensation",
    "headcount",
    "executive_comp",
    "strategy",
    "r_and_d",
    "product_roadmap",
    "legal",
    "risk_factors",
    "general",
    "market_data",
    "shareholder_equity",
    "debt_financing",
    "tax",
    "operations",
]

#Role Permissions
ROLE_RESTRICTIONS: dict[str, set[str]] = {
    "ceo": set(),  # CEO sees everything
    "cto": {"headcount", "compensation", "executive_comp"},
    "cfo": {"strategy", "r_and_d", "product_roadmap", "legal"},
}


USERS = {
    "ceo@apple.com": {
        "name": "CEO_Name",
        "role": "ceo",
        "password_hash": None, 
        "plain": "ceo123",
    },
    "cto@apple.com": {
        "name": "CTO_Name",
        "role": "cto",
        "password_hash": None,
        "plain": "cto123",
    },
    "cfo@apple.com": {
        "name": "CFO_Name",
        "role": "cfo",
        "password_hash": None,
        "plain": "cfo123",
    },
}

# Hash passwords at import time
import hashlib
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

for _email, _u in USERS.items():
    _u["password_hash"] = _hash_password(_u["plain"])

