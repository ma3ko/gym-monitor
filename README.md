# 24hr Gym Monitor 🏋️

A Python bot that monitors your gym's live busyness via Google Maps and sends you Telegram alerts when it changes — so you can go when it's empty.

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

### 3. Find your gym's Google Maps Place ID

**Option A — From a Google Maps URL (easiest, no API key needed):**
```bash
python find_place_id.py "https://www.google.com/maps/place/24+Hour+Fitness+..."
```
Paste your gym's full Google Maps URL as the argument.

**Option B — Search by name (requires a free Google API key):**
```bash
python find_place_id.py "24 Hour Fitness, Honolulu, HI"
```
Get a free API key at [console.cloud.google.com](https://console.cloud.google.com) → Enable Places API.

**Option C — Manual:**
1. Go to [Google Maps](https://maps.google.com) → find your gym
2. Right-click the map pin → "What's here?"
3. The Place ID appears at the bottom of the info card

### 4. Configure your `.env` file

```bash
copy .env.example .env
```

Then open `.env` and fill in:
```
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
PLACE_ID=your_gym_place_id
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
6. Add your environment variables (BOT_TOKEN, CHAT_ID, PLACE_ID) in the Render dashboard → Environment tab
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
├── find_place_id.py    # Helper to find your gym's Place ID
├── state.json          # Auto-created: persists last known status
├── monitor.log         # Auto-created: rolling log file
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (never commit this!)
└── .env.example        # Template
```
