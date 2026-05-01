"""
scraper.py — Fetches live and historical busyness from Google Maps.
Uses Playwright (headless Chromium) to execute JavaScript and extract
the current_popularity data that Google loads dynamically.
"""

import re
import logging
from typing import Optional
from datetime import datetime

import config

logger = logging.getLogger(__name__)

MAPS_URL = "https://www.google.com/maps/place/?q=place_id:{place_id}&hl=en"


def _get_rendered_html(place_id: str) -> Optional[str]:
    """Launch headless Chromium, load the Maps page, return fully-rendered HTML."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--single-process",       # saves RAM on Render free tier
                ],
            )
            ctx = browser.new_context(
                locale="en-US",
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = ctx.new_page()
            url = MAPS_URL.format(place_id=place_id)
            page.goto(url, wait_until="networkidle", timeout=45_000)
            # Give extra time for popular-times widget to load
            page.wait_for_timeout(3_000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright fetch failed: {e}")
        return None


def _parse_busyness(html: str) -> Optional[int]:
    """Extract current busyness % from rendered Maps HTML using multiple patterns."""

    # Pattern 1: JSON key directly in rendered source
    m = re.search(r'"current_popularity"\s*:\s*(\d+)', html)
    if m:
        return int(m.group(1))

    # Pattern 2: "X% busy right now" text
    m = re.search(r'(\d+)%\s*busy', html, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Pattern 3: aria-label on the live bar, e.g. aria-label="52% busy"
    m = re.search(r'aria-label="(\d+)%\s*busy"', html, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


def get_live_busyness() -> Optional[int]:
    """
    Return current live busyness % (0-100).
    Returns None if gym is closed or data unavailable.
    """
    html = _get_rendered_html(config.PLACE_ID)
    if not html:
        return None

    val = _parse_busyness(html)
    if val is not None:
        logger.info(f"Live busyness: {val}%")
    else:
        logger.info("No busyness data in rendered page — gym may be closed.")
    return val


def get_todays_popular_times() -> list:
    """
    Return hourly historical popular times for today.
    Each item: {"hour": int, "busyness": int, "label": str}
    """
    html = _get_rendered_html(config.PLACE_ID)
    if not html:
        return []

    # Find all 24-element arrays of plausible busyness values
    arrays = re.findall(r'\[(\d{1,3}(?:,\d{1,3}){23})\]', html)
    plausible = []
    for arr in arrays:
        vals = list(map(int, arr.split(",")))
        if all(0 <= v <= 100 for v in vals) and max(vals) > 10:
            plausible.append(vals)

    if not plausible:
        return []

    # Pick today's day array (populartimes: Sun=0 … Sat=6)
    today_idx = datetime.now().weekday()  # Mon=0
    pt_idx = (today_idx + 1) % 7
    day_data = plausible[pt_idx] if len(plausible) > pt_idx else plausible[0]

    return [
        {"hour": h, "busyness": v, "label": _fmt_hour(h)}
        for h, v in enumerate(day_data)
        if v > 0
    ]


def _fmt_hour(h: int) -> str:
    if h == 0:  return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h - 12} PM"
