# monitor.py
import os
import time
import json
import re
import asyncio
import requests
import telegram
from telegram.error import TelegramError

# --- Configuration ---
WEBSITE_URL = "https://trouverunlogement.lescrous.fr/tools/41/search"
API_SEARCH_URL = "https://trouverunlogement.lescrous.fr/api/fr/search/41"

CITY_CONFIGS = {
    "Marseille": {
        "location": [
            {"lon": 5.2286902, "lat": 43.3910329},
            {"lon": 5.5324758, "lat": 43.1696205}
        ],
        "pageSize": 24, "name": "Marseille"
    }
}

CURRENT_SEARCH_CITY = "Marseille"
SEARCH_KEYWORD = CITY_CONFIGS[CURRENT_SEARCH_CITY]["name"]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DATA_FILE = f"previous_listings_{SEARCH_KEYWORD.lower()}.json"
ALL_LISTING_DETAILS = {}

def get_listings_http():
    # ... (This function is the same as the last full version) ...
    global ALL_LISTING_DETAILS
    ALL_LISTING_DETAILS = {}
    current_listing_ids = set()
    city_config = CITY_CONFIGS[CURRENT_SEARCH_CITY]
    print(f"Attempting to fetch data for {SEARCH_KEYWORD}...")
    try:
        headers = {"User-Agent": "Mozilla/5.0...", "Accept": "application/ld+json...", "Content-Type": "application/json", "Origin": "...", "Referer": WEBSITE_URL}
        json_payload = {"idTool": 41, "need_aggregation": True, "page": 1, "pageSize": city_config["pageSize"], "location": city_config["location"]}
        response = requests.post(API_SEARCH_URL, headers=headers, json=json_payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        listings_data = data.get('results', {}).get('items', [])
        for item in listings_data:
            listing_id = str(item.get('id', 'NO_ID'))
            listing_title = f"{item.get('label', 'N/A')} - {item.get('residence', {}).get('label', 'N/A')}"
            listing_link = f"https://trouverunlogement.lescrous.fr/tools/41/accommodations/{listing_id}"
            amount = item.get('bookingData', {}).get('amount')
            listing_price = f"{amount / 100:.2f}€" if isinstance(amount, int) else "N/A"
            if listing_id != 'NO_ID':
                current_listing_ids.add(listing_id)
                ALL_LISTING_DETAILS[listing_id] = {'title': listing_title, 'price': listing_price, 'link': listing_link}
        print(f"Found {len(current_listing_ids)} listings for {SEARCH_KEYWORD}.")
        return current_listing_ids
    except Exception as e:
        print(f"An error occurred in get_listings_http: {e}")
        return set()

async def send_telegram_message(message):
    # ... (This function is the same as the last full version) ...
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set.")
        return
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        print("Telegram notification sent successfully!")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def load_previous_listings():
    # ... (This function is the same as the last full version, BUT WE WILL NOT USE IT FOR NOW) ...
    # For simplicity, GitHub Actions won't save state between runs.
    # Every run will report all found listings.
    return set()

def save_current_listings(listings):
    # ... (This function is the same as the last full version, BUT WE WILL NOT USE IT) ...
    print("State saving is disabled for GitHub Actions.")
    pass

async def main():
    # ... (This is the logic from your check_and_notify function) ...
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting new check...")
    current_listings = get_listings_http()
    timestamp = f"\n\nLast check: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    if not current_listings:
        message = f"ℹ️ No Crous listings are currently available for {SEARCH_KEYWORD}." + timestamp
    else:
        message_parts = [f"✅ Crous Listings Found for {SEARCH_KEYWORD} ({len(current_listings)} total):\n\n"]
        for lid in list(current_listings)[:10]: # List up to 10
            details = ALL_LISTING_DETAILS.get(lid, {})
            message_parts.append(f"- <a href=\"{details.get('link')}\">{details.get('title')}</a> ({details.get('price')})\n")
        if len(current_listings) > 10:
            message_parts.append(f"...and {len(current_listings) - 10} more.\n")
        message_parts.append(timestamp)
        message = "".join(message_parts)
    await send_telegram_message(message)
    print("Check complete.")

if __name__ == "__main__":
    asyncio.run(main())