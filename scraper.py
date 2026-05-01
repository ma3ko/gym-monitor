"""
scraper.py — Fetches live busyness from Google Maps.
Uses Playwright with anti-bot settings and JS evaluation to read
Google's internal APP_INITIALIZATION_STATE data directly.
"""

import os
import re
import json
import logging
from typing import Optional
from datetime import datetime

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/render/project/src/.browsers")

import config

logger = logging.getLogger(__name__)

MAPS_URL = "https://www.google.com/maps/place/?q=place_id:{place_id}&hl=en&gl=us"


def _get_page_data(place_id: str) -> Optional[str]:
    """
    Launch stealth Chromium, load the Maps page, and return the full
    page HTML + any JS state data we can extract.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--single-process",
                ],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                timezone_id="Pacific/Honolulu",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )

            # Mask automation signals
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                window.chrome = { runtime: {} };
            """)

            page = ctx.new_page()
            url = MAPS_URL.format(place_id=place_id)
            logger.info(f"Loading: {url}")
            page.goto(url, wait_until="networkidle", timeout=45_000)

            # Wait extra for popular-times widget
            page.wait_for_timeout(4_000)

            # Strategy 1: Read APP_INITIALIZATION_STATE from JS context
            js_state = page.evaluate("""() => {
                try {
                    const s = window.APP_INITIALIZATION_STATE;
                    return s ? JSON.stringify(s) : null;
                } catch(e) { return null; }
            }""")

            # Strategy 2: Look for current_popularity in any window variable
            current_pop = page.evaluate("""() => {
                try {
                    const html = document.documentElement.innerHTML;
                    const m = html.match(/"current_popularity"\\s*:\\s*(\\d+)/);
                    return m ? parseInt(m[1]) : null;
                } catch(e) { return null; }
            }""")

            # Strategy 3: Check aria-labels on busyness bars
            aria_pop = page.evaluate("""() => {
                try {
                    const els = document.querySelectorAll('[aria-label*="busy"]');
                    for (const el of els) {
                        const m = el.getAttribute('aria-label').match(/(\\d+)%/);
                        if (m) return parseInt(m[1]);
                    }
                    return null;
                } catch(e) { return null; }
            }""")

            html = page.content()
            browser.close()

            # Log a snippet for debugging
            snip = html[:500].replace("\n", " ")
            logger.debug(f"Page snippet: {snip}")

            return {
                "html": html,
                "js_state": js_state,
                "current_pop": current_pop,
                "aria_pop": aria_pop,
            }

    except Exception as e:
        logger.error(f"Playwright fetch failed: {e}")
        return None


def get_live_busyness() -> Optional[int]:
    """Return current busyness % (0-100) or None if unavailable."""
    data = _get_page_data(config.PLACE_ID)
    if not data:
        return None

    # Priority 1: Direct JS extraction of current_popularity
    if data["current_pop"] is not None:
        logger.info(f"Live busyness (JS innerHTML): {data['current_pop']}%")
        return data["current_pop"]

    # Priority 2: aria-label on busyness bar elements
    if data["aria_pop"] is not None:
        logger.info(f"Live busyness (aria-label): {data['aria_pop']}%")
        return data["aria_pop"]

    # Priority 3: Parse APP_INITIALIZATION_STATE JSON blob
    if data["js_state"]:
        m = re.search(r'"current_popularity"\s*:\s*(\d+)', data["js_state"])
        if m:
            val = int(m.group(1))
            logger.info(f"Live busyness (APP_STATE): {val}%")
            return val

    # Priority 4: Regex fallbacks on raw HTML
    html = data["html"]
    for pattern in [
        r'"current_popularity"\s*:\s*(\d+)',
        r'(\d+)%\s*busy',
        r'aria-label="(\d+)%',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            logger.info(f"Live busyness (HTML regex): {val}%")
            return val

    logger.info("No busyness data found — gym may be closed or Google blocked the request.")
    return None


def get_todays_popular_times() -> list:
    """Return hourly historical popular times for today."""
    data = _get_page_data(config.PLACE_ID)
    if not data:
        return []

    html = data["html"]
    arrays = re.findall(r'\[(\d{1,3}(?:,\d{1,3}){23})\]', html)
    plausible = []
    for arr in arrays:
        vals = list(map(int, arr.split(",")))
        if all(0 <= v <= 100 for v in vals) and max(vals) > 10:
            plausible.append(vals)

    if not plausible and data["js_state"]:
        arrays = re.findall(r'\[(\d{1,3}(?:,\d{1,3}){23})\]', data["js_state"])
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
        for h, v in enumerate(day_data) if v > 0
    ]


def _fmt_hour(h: int) -> str:
    if h == 0:  return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h - 12} PM"
