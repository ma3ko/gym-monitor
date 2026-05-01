"""
scraper.py — Fetches foot traffic data via the BestTime.app API.

Uses the forecast + live endpoints to get both historical popular
times and real-time busyness data without any browser scraping.

BestTime.app provides foot traffic data for 150+ countries using
aggregated anonymous phone signals. No Google scraping needed.
"""

import logging
from typing import Optional
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)

BASE_URL = "https://besttime.app/api/v1"

VENUE_NAME = "24 Hour Fitness"
VENUE_ADDRESS = "1680 Kapiolani Blvd, Honolulu, HI 96814"


def _get_api_key() -> str:
    """Get the BestTime private API key from config."""
    return config.BESTTIME_API_KEY


def _get_venue_id() -> Optional[str]:
    """Get the cached venue_id, or create a forecast to obtain one."""
    venue_id = getattr(config, "BESTTIME_VENUE_ID", None)
    if venue_id:
        return venue_id

    # Create a new forecast to get the venue_id
    logger.info("No venue_id cached — creating initial BestTime forecast...")
    try:
        resp = requests.post(
            f"{BASE_URL}/forecasts",
            params={
                "api_key_private": _get_api_key(),
                "venue_name": VENUE_NAME,
                "venue_address": VENUE_ADDRESS,
            },
            timeout=30,
        )
        data = resp.json()

        if data.get("status") == "OK":
            vid = data["venue_info"]["venue_id"]
            logger.info(f"BestTime venue_id: {vid}")
            logger.info(f"Venue: {data['venue_info'].get('venue_name')}")
            logger.info(f"Address: {data['venue_info'].get('venue_address')}")
            # Cache it on the config module for subsequent calls
            config.BESTTIME_VENUE_ID = vid
            return vid
        else:
            logger.error(f"BestTime forecast failed: {data}")
            return None
    except Exception as e:
        logger.error(f"BestTime forecast request failed: {e}")
        return None


def get_live_busyness() -> Optional[int]:
    """
    Return current busyness % (0-100) from BestTime live endpoint.
    Falls back to the forecasted busyness for the current hour if
    live data is unavailable.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("BESTTIME_API_KEY not set!")
        return None

    venue_id = _get_venue_id()
    if not venue_id:
        return None

    # Try the live endpoint first
    try:
        resp = requests.post(
            f"{BASE_URL}/forecasts/live",
            params={
                "api_key_private": api_key,
                "venue_id": venue_id,
            },
            timeout=20,
        )
        data = resp.json()

        if data.get("status") == "OK":
            analysis = data.get("analysis", {})

            # Live busyness (real-time)
            live_val = analysis.get("venue_live_busyness")
            if live_val is not None and analysis.get("venue_live_busyness_available"):
                logger.info(f"Live busyness (real-time): {live_val}%")
                return int(live_val)

            # Forecasted busyness for current hour (fallback)
            forecast_val = analysis.get("venue_forecasted_busyness")
            if forecast_val is not None:
                logger.info(f"Forecasted busyness (current hour): {forecast_val}%")
                return int(forecast_val)

        logger.warning(f"BestTime live response: {data.get('message', data.get('status', 'unknown'))}")
    except Exception as e:
        logger.error(f"BestTime live request failed: {e}")

    # Fallback: query the forecast for the current hour
    return _forecast_current_hour(api_key, venue_id)


def _forecast_current_hour(api_key: str, venue_id: str) -> Optional[int]:
    """Query the forecast for the current hour as a fallback."""
    try:
        resp = requests.get(
            f"{BASE_URL}/forecasts/now",
            params={
                "api_key_public": api_key.replace("pri_", "pub_"),
                "venue_id": venue_id,
            },
            timeout=20,
        )
        data = resp.json()

        if data.get("status") == "OK":
            analysis = data.get("analysis", {})
            raw = analysis.get("now_raw")
            if raw is not None:
                logger.info(f"Forecast now busyness: {raw}%")
                return int(raw)
    except Exception as e:
        logger.error(f"BestTime now query failed: {e}")
    return None


def get_todays_popular_times() -> list:
    """
    Return hourly popular times for today from BestTime forecast.
    Each item: {"hour": int, "busyness": int, "label": str}
    """
    api_key = _get_api_key()
    venue_id = _get_venue_id()
    if not api_key or not venue_id:
        return []

    try:
        # Map Python weekday (Mon=0) to BestTime day_int (Mon=0)
        today_int = datetime.now().weekday()

        resp = requests.get(
            f"{BASE_URL}/forecasts/day/raw",
            params={
                "api_key_public": api_key.replace("pri_", "pub_"),
                "venue_id": venue_id,
                "day_int": today_int,
            },
            timeout=20,
        )
        data = resp.json()

        if data.get("status") == "OK":
            analysis = data.get("analysis", {})
            day_raw = analysis.get("day_raw", [])

            if day_raw and len(day_raw) == 24:
                return [
                    {"hour": h, "busyness": v, "label": _fmt_hour(h)}
                    for h, v in enumerate(day_raw) if v > 0
                ]
    except Exception as e:
        logger.error(f"BestTime day query failed: {e}")

    return []


def _fmt_hour(h: int) -> str:
    if h == 0:  return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h - 12} PM"
