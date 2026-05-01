"""
scraper.py — Fetches live busyness for a Google Maps place.

Approach:
  1. Try Google Search (less bot-protected than Maps)
  2. Fall back to Google Maps with Playwright stealth
  3. Multiple extraction patterns for maximum reliability
"""

import os
import re
import logging
from typing import Optional
from datetime import datetime

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/render/project/src/.browsers")

import config

logger = logging.getLogger(__name__)

# ── Approach 1: Google Search (preferred — less bot-protected) ──────────────

SEARCH_URL = "https://www.google.com/search?q={query}&hl=en&gl=us"


def _search_busyness() -> Optional[int]:
    """
    Scrape the Google Search Knowledge Panel for live busyness.
    Google Search is far less aggressive about blocking bots than Maps.
    """
    try:
        from playwright.sync_api import sync_playwright

        # Build a search query that will trigger the Knowledge Panel
        query = "24+Hour+Fitness+Kapiolani+Honolulu+popular+times"
        url = SEARCH_URL.format(query=query)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--single-process",
                ],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-US",
                timezone_id="Pacific/Honolulu",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            page = ctx.new_page()
            logger.info(f"Search approach: loading {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(3_000)

            # Try to click "Accept all" on Google consent
            try:
                accept_btn = page.locator('button:has-text("Accept all")')
                if accept_btn.count() > 0:
                    accept_btn.first.click()
                    page.wait_for_timeout(2_000)
                    logger.info("Clicked Google consent 'Accept all' button")
            except Exception:
                pass

            # Extract busyness from the Knowledge Panel
            # Method 1: aria-label with "% busy"
            val = page.evaluate("""() => {
                const els = document.querySelectorAll('[aria-label]');
                for (const el of els) {
                    const label = el.getAttribute('aria-label') || '';
                    const m = label.match(/(\\d+)\\s*%\\s*busy/i);
                    if (m) return parseInt(m[1]);
                }
                return null;
            }""")

            if val is not None:
                browser.close()
                return val

            # Method 2: Text content with "% busy"
            val = page.evaluate("""() => {
                const text = document.body.innerText;
                const m = text.match(/(\\d+)%\\s*busy/i);
                return m ? parseInt(m[1]) : null;
            }""")

            if val is not None:
                browser.close()
                return val

            # Method 3: Regex on raw HTML
            html = page.content()
            title = page.title()
            logger.info(f"Search page title: {title}")
            logger.info(f"Search HTML length: {len(html)} chars")
            # Log a useful snippet for debugging
            logger.info(f"Search HTML snippet: {html[:1500]}")

            browser.close()

            for pattern in [
                r'"current_popularity"\s*:\s*(\d+)',
                r'(\d+)%\s*busy',
                r'aria-label="[^"]*?(\d+)%[^"]*busy',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    return int(m.group(1))

            return None

    except Exception as e:
        logger.error(f"Search approach failed: {e}")
        return None


# ── Approach 2: Google Maps page (fallback) ─────────────────────────────────

MAPS_URL = "https://www.google.com/maps/place/?q=place_id:{place_id}&hl=en&gl=us"


def _maps_busyness() -> Optional[int]:
    """Load the Maps place page with Playwright and try to extract busyness."""
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
                    "--single-process",
                ],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-US",
                timezone_id="Pacific/Honolulu",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            page = ctx.new_page()
            url = MAPS_URL.format(place_id=config.PLACE_ID)
            logger.info(f"Maps approach: loading {url}")
            page.goto(url, wait_until="networkidle", timeout=45_000)

            # Handle consent
            try:
                accept_btn = page.locator('button:has-text("Accept all")')
                if accept_btn.count() > 0:
                    accept_btn.first.click()
                    page.wait_for_timeout(2_000)
            except Exception:
                pass

            page.wait_for_timeout(4_000)

            # Try JS extraction
            val = page.evaluate("""() => {
                const html = document.documentElement.innerHTML;
                // current_popularity
                let m = html.match(/"current_popularity"\\s*:\\s*(\\d+)/);
                if (m) return parseInt(m[1]);
                // % busy
                m = html.match(/(\\d+)%\\s*busy/i);
                if (m) return parseInt(m[1]);
                // aria-label
                const els = document.querySelectorAll('[aria-label*="busy"]');
                for (const el of els) {
                    m = el.getAttribute('aria-label').match(/(\\d+)%/);
                    if (m) return parseInt(m[1]);
                }
                return null;
            }""")

            html = page.content()
            title = page.title()
            logger.info(f"Maps page title: {title}")
            logger.info(f"Maps HTML length: {len(html)} chars")
            logger.info(f"Maps HTML snippet: {html[:1500]}")

            browser.close()

            if val is not None:
                return val

            # Regex fallback on raw HTML
            for pattern in [
                r'"current_popularity"\s*:\s*(\d+)',
                r'(\d+)%\s*busy',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    return int(m.group(1))

            return None

    except Exception as e:
        logger.error(f"Maps approach failed: {e}")
        return None


# ── Public API ──────────────────────────────────────────────────────────────

def get_live_busyness() -> Optional[int]:
    """Try all approaches to get live busyness."""

    # Try Google Search first (less blocked)
    val = _search_busyness()
    if val is not None:
        logger.info(f"Live busyness (Search): {val}%")
        return val

    # Fall back to Maps
    val = _maps_busyness()
    if val is not None:
        logger.info(f"Live busyness (Maps): {val}%")
        return val

    logger.info("No busyness data from any source.")
    return None


def get_todays_popular_times() -> list:
    """Return hourly popular times for today (from the Maps page)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--single-process"],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="en-US",
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = ctx.new_page()
            url = MAPS_URL.format(place_id=config.PLACE_ID)
            page.goto(url, wait_until="networkidle", timeout=45_000)
            page.wait_for_timeout(4_000)
            html = page.content()
            browser.close()
    except Exception as e:
        logger.error(f"Popular times fetch failed: {e}")
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
        for h, v in enumerate(day_data) if v > 0
    ]


def _fmt_hour(h: int) -> str:
    if h == 0:  return "12 AM"
    if h < 12:  return f"{h} AM"
    if h == 12: return "12 PM"
    return f"{h - 12} PM"
