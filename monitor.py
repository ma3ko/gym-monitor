"""
monitor.py — Main entrypoint for the 24hr Gym Monitor.

Usage:
  python monitor.py           # Start the live monitoring loop
  python monitor.py --test    # Send a test Telegram message and exit
  python monitor.py --check   # Run one busyness check immediately and exit
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

import config
import scraper
import telegram_bot

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── State persistence ──────────────────────────────────────────────────────────
STATE_FILE = Path("state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_status": None, "last_busyness": None, "last_alert_at": None}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Core check ────────────────────────────────────────────────────────────────

def check_gym():
    """
    Fetch live busyness and send a Telegram alert if the status has changed.
    """
    state = load_state()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"Checking gym busyness... ({now})")
    busyness = scraper.get_live_busyness()

    if busyness is None:
        logger.info("No busyness data returned (gym may be closed). Skipping.")
        return

    current_status = config.status_from_busyness(busyness)
    last_status = state.get("last_status")

    logger.info(f"Status: {current_status} ({busyness}%) | Previous: {last_status}")

    if current_status != last_status:
        logger.info(f"Status changed: {last_status} → {current_status}. Sending alert.")
        telegram_bot.send_status_alert(busyness, current_status)
        state["last_status"] = current_status
        state["last_busyness"] = busyness
        state["last_alert_at"] = now
        save_state(state)
    else:
        logger.info("No status change. No alert sent.")


def send_daily_digest():
    """Fetch today's popular times and send a morning digest to Telegram."""
    logger.info("Sending daily digest...")
    hours = scraper.get_todays_popular_times()
    telegram_bot.send_daily_digest(hours)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="24hr Gym Monitor")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test Telegram message to verify configuration, then exit.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run a single busyness check immediately, then exit.",
    )
    args = parser.parse_args()

    if args.test:
        logger.info("Sending test message to Telegram...")
        ok = telegram_bot.send_test_message()
        if ok:
            print("\n✅ Test message sent! Check your Telegram.")
        else:
            print("\n❌ Failed to send test message. Check your BOT_TOKEN and CHAT_ID in .env")
        sys.exit(0 if ok else 1)

    if args.check:
        check_gym()
        sys.exit(0)

    # ── Full monitoring loop ──
    logger.info("=" * 60)
    logger.info("  24hr Gym Monitor starting up")
    logger.info(f"  BestTime API : {'Set' if config.BESTTIME_API_KEY else 'Missing'}")
    logger.info(f"  Check every  : {config.CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"  Quiet below  : {config.QUIET_THRESHOLD}%")
    logger.info(f"  Busy above   : {config.BUSY_THRESHOLD}%")
    logger.info(f"  Daily digest : {config.DAILY_DIGEST_TIME}")
    logger.info("=" * 60)

    # Send startup test message
    telegram_bot.send_test_message()

    # Run a check immediately on startup
    check_gym()

    # Schedule recurring checks
    schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(check_gym)

    # Schedule daily digest
    schedule.every().day.at(config.DAILY_DIGEST_TIME).do(send_daily_digest)

    logger.info(f"Monitoring started. Checking every {config.CHECK_INTERVAL_MINUTES} min.")

    while True:
        schedule.run_pending()
        time.sleep(30)  # Check schedule every 30 seconds


if __name__ == "__main__":
    main()
