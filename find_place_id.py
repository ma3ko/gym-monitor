"""
find_place_id.py — Helper script to find your gym's Google Maps Place ID.

Usage:
  python find_place_id.py "24 Hour Fitness, Honolulu, HI"

Requirements:
  - Set GOOGLE_API_KEY in your .env (free key from console.cloud.google.com)
  - OR use the manual method below (no API key needed)

Manual method (no API key):
  1. Go to https://maps.google.com
  2. Search for your gym and open its listing
  3. Look at the URL — it contains something like:
        place/24+Hour+Fitness/@21.3069,157.8583,17z/data=...
  4. OR right-click the pin → "What's here?" → copy the Place ID shown

API method (automated):
  Requires Google Places API enabled + billing (but free tier is generous).
"""

import sys
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def find_place_id_via_api(query: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ No GOOGLE_API_KEY found in .env")
        print("   Use the manual method described in the docstring above.")
        return

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "name,place_id,formatted_address",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        print(f"❌ No results found for: '{query}'")
        return

    print(f"\n✅ Found {len(candidates)} result(s):\n")
    for c in candidates:
        print(f"  Name    : {c.get('name')}")
        print(f"  Address : {c.get('formatted_address')}")
        print(f"  Place ID: {c.get('place_id')}")
        print()

    print("👉 Copy the Place ID above and paste it as PLACE_ID= in your .env file.")


def find_place_id_manual_url(maps_url: str):
    """
    Extract Place ID from a Google Maps URL if it's embedded.
    Works on URLs like: https://www.google.com/maps/place/...+data=!3m1!4b1!4m6!3m5!1s<PLACE_ID>!...
    """
    import re
    # Look for ChI... pattern (Place IDs start with ChI)
    match = re.search(r'(ChI[a-zA-Z0-9_-]+)', maps_url)
    if match:
        print(f"\n✅ Extracted Place ID: {match.group(1)}")
        print("👉 Paste this as PLACE_ID= in your .env file.")
    else:
        print("❌ Could not extract Place ID from that URL.")
        print("   Try the search method: python find_place_id.py \"Gym name, City, State\"")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg.startswith("http"):
        find_place_id_manual_url(arg)
    else:
        find_place_id_via_api(arg)
