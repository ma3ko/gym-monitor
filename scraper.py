"""
scraper.py — Fetches live and historical busyness directly from Google Maps HTML.
No API key required.
"""

import re
import logging
import requests
from typing import Optional
from datetime import datetime

import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def _fetch_maps_html(place_id: str) -> Optional[str]:
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.error(f"Failed to fetch Google Maps page: {e}")
        return None


def get_live_busyness() -> Optional[int]:
    """
    Returns the current live busyness % (0-100) scraped from Google Maps HTML.
    Returns None if gym is closed or data isn't available.
    """
    html = _fetch_maps_html(config.PLACE_ID)
    if not html:
        return None

    # Pattern 1: current_popularity embedded in JSON blob
    match = re.search(r'"current_popularity":(\d+)', html)
    if match:
        val = int(match.group(1))
        logger.info(f"Live busyness (pattern 1): {val}%")
        return val

    # Pattern 2: percentage in "X% busy" text
    match = re.search(r'(\d+)%\s*busy', html, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        logger.info(f"Live busyness (pattern 2): {val}%")
        return val

    # Pattern 3: look for the popular times data array and find current hour
    # Google embeds 24-value arrays (0-100) per day in the page JS
    arrays = re.findall(r'\[(\d{1,3}(?:,\d{1,3}){23})\]', html)
    plausible = []
    for arr in arrays:
        vals = list(map(int, arr.split(",")))
        if all(0 <= v <= 100 for v in vals) and max(vals) > 10:
            plausible.append(vals)

    if plausible:
        today_idx = datetime.now().weekday()  # Mon=0 Sun=6 → maps to Sun=0 in populartimes
        pt_idx = (today_idx + 1) % 7
        if len(plausible) > pt_idx:
            current_hour = datetime.now().hour
            val = plausible[pt_idx][current_hour]
            logger.info(f"Live busyness (pattern 3, historical fallback): {val}%")
            return val
        # Use first plausible array
        current_hour = datetime.now().hour
        val = plausible[0][current_hour]
        logger.info(f"Live busyness (pattern 3, first array): {val}%")
        return val

    logger.info("No busyness data found — gym may be closed or Google structure changed.")
    return None


def get_todays_popular_times() -> list:
    """
    Returns hourly historical popular times for today.
    Each item: {"hour": int, "busyness": int, "label": str}
    """
    html = _fetch_maps_html(config.PLACE_ID)
    if not html:
        return []

    arrays = re.findall(r'\[(\d{1,3}(?:,\d{1,3}){23})\]', html)
    plausible = []
    for arr in arrays:
        vals = list(map(int, arr.split(",")))
        if all(0 <= v <= 100 for v in vals) and max(vals) > 10:
            plausible.append(vals)

    if not plausible:
        return []

    today_idx = datetime.now().weekday()
    pt_idx = (today_idx + 1) % 7
    day_data = plausible[pt_idx] if len(plausible) > pt_idx else plausible[0]

    return [
        {"hour": h, "busyness": v, "label": _fmt_hour(h)}
        for h, v in enumerate(day_data)
        if v > 0
    ]


def _fmt_hour(h: int) -> str:
    if h == 0:   return "12 AM"
    if h < 12:   return f"{h} AM"
    if h == 12:  return "12 PM"
    return f"{h - 12} PM"
