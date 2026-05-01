"""
telegram_bot.py — Sends messages to a Telegram chat via the Bot API.
"""

import logging
import requests
import config

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Send a message to the configured chat. Returns True on success.
    """
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": config.CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram message sent successfully.")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def send_status_alert(busyness: int, status: str) -> bool:
    """
    Send a busyness status change alert.
    """
    if status == "quiet":
        emoji = "🟢"
        headline = "Gym is <b>quiet</b> — great time to go!"
        tip = "Busyness is low. Head over now while it's empty. 💪"
    elif status == "busy":
        emoji = "🔴"
        headline = "Gym is <b>packed</b> — maybe wait."
        tip = "It's crowded right now. Check back in 30–60 min."
    else:
        emoji = "🟡"
        headline = "Gym is <b>moderately busy</b>."
        tip = "Not packed, not empty. Probably fine to go."

    bar = _busyness_bar(busyness)
    text = (
        f"{emoji} <b>GYM UPDATE</b>\n\n"
        f"{headline}\n\n"
        f"📊 Live busyness: <code>{busyness}%</code>\n"
        f"{bar}\n\n"
        f"💡 {tip}"
    )
    return send_message(text)


def send_daily_digest(hours: list[dict]) -> bool:
    """
    Send a morning digest with today's projected best/worst times.
    hours: list of {"hour": int, "busyness": int, "label": str}
    """
    if not hours:
        return send_message(
            "🏋️ <b>Daily Gym Digest</b>\n\n"
            "⚠️ Couldn't load today's popular times data.\n"
            "I'll still alert you when busyness changes!"
        )

    # Find quietest windows (bottom 3 by busyness)
    open_hours = [h for h in hours if h["busyness"] > 0]
    quiet_windows = sorted(open_hours, key=lambda x: x["busyness"])[:3]
    busy_windows = sorted(open_hours, key=lambda x: x["busyness"], reverse=True)[:2]

    quiet_lines = "\n".join(
        f"  • {h['label']} — {h['busyness']}% {_busyness_bar(h['busyness'], length=8)}"
        for h in sorted(quiet_windows, key=lambda x: x["hour"])
    )
    busy_lines = "\n".join(
        f"  • {h['label']} — {h['busyness']}% {_busyness_bar(h['busyness'], length=8)}"
        for h in sorted(busy_windows, key=lambda x: x["hour"])
    )

    text = (
        "🏋️ <b>Daily Gym Digest</b>\n\n"
        "🟢 <b>Best times to go today:</b>\n"
        f"{quiet_lines}\n\n"
        "🔴 <b>Avoid these times:</b>\n"
        f"{busy_lines}\n\n"
        "I'll ping you whenever the gym status changes. Have a great workout! 💪"
    )
    return send_message(text)


def send_test_message() -> bool:
    """Send a test message to verify the bot is configured correctly."""
    return send_message(
        "✅ <b>24hr Gym Monitor is online!</b>\n\n"
        "I'll alert you when your gym goes from busy → quiet (or vice versa).\n\n"
        "🟢 Quiet (&lt;35%) = Go now!\n"
        "🟡 Moderate (35–65%) = Up to you\n"
        "🔴 Busy (&gt;65%) = Skip it\n\n"
        "Monitoring started. 🏋️"
    )


def _busyness_bar(busyness: int, length: int = 10) -> str:
    """Render a simple ASCII progress bar for busyness."""
    filled = round((busyness / 100) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"
