"""
scraper.py — Fetches live and historical busyness from Google Maps via populartimes.

populartimes docs: https://github.com/m-wrzr/populartimes
"""

import logging
from datetime import datetime
from typing import Optional

try:
    import populartimes
except ImportError:
    raise ImportError("Run: pip install populartimes")

import config

logger = logging.getLogger(__name__)


def get_live_busyness() -> Optional[int]:
    """
    Return the current live busyness percentage (0–100) for the configured gym.

    Returns None if:
    - The gym is currently closed
    - Google isn't reporting live data right now
    - A network/scraping error occurred
    """
    try:
        data = populartimes.get_id(config.PLACE_ID)
        current = data.get("current_popularity")
        if current is None:
            logger.info("No live busyness data available (gym may be closed or data not reported).")
        else:
            logger.info(f"Live busyness: {current}%")
        return current
    except Exception as e:
        logger.error(f"Failed to fetch busyness data: {e}")
        return None


def get_todays_popular_times() -> list[dict]:
    """
    Return the hourly historical popular times for today (as a list of dicts).

    Each dict has: {"hour": 9, "busyness": 45, "label": "9 AM"}
    Returns an empty list on failure.
    """
    try:
        data = populartimes.get_id(config.PLACE_ID)
        today_index = datetime.now().weekday()  # Monday=0, Sunday=6
        # populartimes uses Sunday=0 ... Saturday=6
        pt_index = (today_index + 1) % 7

        popular_times = data.get("populartimes", [])
        if not popular_times or len(popular_times) <= pt_index:
            return []

        day_data = popular_times[pt_index]
        hours = []
        for i, val in enumerate(day_data.get("data", [])):
            if val is not None and val > 0:
                hours.append({
                    "hour": i,
                    "busyness": val,
                    "label": _format_hour(i),
                })
        return hours

    except Exception as e:
        logger.error(f"Failed to fetch popular times: {e}")
        return []


def _format_hour(h: int) -> str:
    """Convert 0–23 hour to '6 AM' / '2 PM' style label."""
    if h == 0:
        return "12 AM"
    elif h < 12:
        return f"{h} AM"
    elif h == 12:
        return "12 PM"
    else:
        return f"{h - 12} PM"
