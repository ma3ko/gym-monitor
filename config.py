"""
config.py — Loads environment variables and exposes typed settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Missing required environment variable: {key}\n"
            f"Copy .env.example to .env and fill in your values."
        )
    return val


# ── Telegram ──────────────────────────────────────────
BOT_TOKEN: str = _require("BOT_TOKEN")
CHAT_ID: str = _require("CHAT_ID")

# ── BestTime API ──────────────────────────────────────
BESTTIME_API_KEY: str = _require("BESTTIME_API_KEY")

# ── Thresholds ────────────────────────────────────────
QUIET_THRESHOLD: int = int(os.getenv("QUIET_THRESHOLD", "35"))
BUSY_THRESHOLD: int = int(os.getenv("BUSY_THRESHOLD", "65"))

# ── Schedule ──────────────────────────────────────────
CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
DAILY_DIGEST_TIME: str = os.getenv("DAILY_DIGEST_TIME", "08:00")


def status_from_busyness(busyness: int) -> str:
    """Map a busyness percentage to a status label."""
    if busyness <= QUIET_THRESHOLD:
        return "quiet"
    elif busyness >= BUSY_THRESHOLD:
        return "busy"
    else:
        return "moderate"
