# 24hr Gym Monitor 🏋️

A Python bot that monitors your gym's live busyness via the BestTime.app API and sends you Telegram alerts when it changes — so you can go when it's empty.

## What It Does

- Checks your gym's live busyness every 15 minutes (configurable)
- Sends a **Telegram alert only when the status changes** (no spam):
  - 🟢 **Quiet** (<35%) — "Gym is quiet — go now!"
  - 🟡 **Moderate** (35–65%) — optional alert
  - 🔴 **Busy** (>65%) — "Gym is packed — wait a bit"
- Sends a **daily 8 AM digest** with today's predicted best/worst times

---

## Setup (one-time, ~10 minutes)

### 1. Install Python dependencies

```bash
cd "24hr gym monitor"
pip install -r requirements.txt
```

### 2. Create a Telegram bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **API Token** it gives you (looks like `123456789:ABCdef...`)
4. **Get your Chat ID:**
   - Message your new bot anything (e.g., "hello")
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id": 123456789}` — that number is your Chat ID

### 3. Get a BestTime.app API Key

This project uses BestTime.app to get foot traffic data without needing to scrape Google.
1. Go to [BestTime.app](https://besttime.app/) and sign up for a free account.
2. Go to the API Keys management page.
3. Copy your **Private API Key** (starts with `pri_...`).

### 4. Configure your `.env` file

```bash
copy .env.example .env
```

Then open `.env` and fill in:
```
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
BESTTIME_API_KEY=pri_...
```

### 5. Test everything

```bash
python monitor.py --test
```

You should receive a message in Telegram within a few seconds. ✅

---

## Running the Monitor

```bash
# Start the full monitoring loop
python monitor.py

# Run one check immediately (useful for testing)
python monitor.py --check
```

---

## Running 24/7 on Render.com (free, recommended)

So you get alerts even when your PC is off:

1. Push this folder to a GitHub repo
2. Go to [render.com](https://render.com) → New → **Background Worker**
3. Connect your GitHub repo
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `python monitor.py`
6. Add your environment variables (BOT_TOKEN, CHAT_ID, BESTTIME_API_KEY) in the Render dashboard → Environment tab
7. Deploy!

> **Note:** Render's free tier may spin down after inactivity. Use the `schedule` keep-alive or upgrade to paid ($7/mo) for always-on monitoring.

---

## Running on Windows (Task Scheduler — local only)

If you prefer to run on your own PC:

1. Open **Task Scheduler** → Create Basic Task
2. **Trigger:** At startup (or daily)
3. **Action:** Start a program
   - Program: `python`
   - Arguments: `monitor.py`
   - Start in: `C:\Users\MA3K\Projects\24hr gym monitor`

---

## Configuration

All settings are in `.env`:

| Variable | Default | Description |
|---|---|---|
| `QUIET_THRESHOLD` | `35` | Below this % → 🟢 Quiet alert |
| `BUSY_THRESHOLD` | `65` | Above this % → 🔴 Busy alert |
| `CHECK_INTERVAL_MINUTES` | `15` | How often to poll (minutes) |
| `DAILY_DIGEST_TIME` | `08:00` | Time for morning digest (24hr) |

---

## File Structure

```
24hr gym monitor/
├── monitor.py          # Main loop & scheduler
├── scraper.py          # Google Maps busyness fetcher
├── telegram_bot.py     # Telegram message sender
├── config.py           # Environment variable loader
├── state.json          # Auto-created: persists last known status
├── monitor.log         # Auto-created: rolling log file
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (never commit this!)
└── .env.example        # Template
```
