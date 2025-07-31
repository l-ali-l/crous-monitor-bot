import os
import time
import json
import re
import asyncio
import requests
import telegram
from telegram.error import TelegramError

# --- Configuration ---
API_SEARCH_URL = "https://trouverunlogement.lescrous.fr/api/fr/search/41"

# --- MODIFIED: Using the original secret names ---
# These will now match the secrets you already have in your GitHub repository settings.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Add the keywords you want to search for (in lowercase)
ALERT_KEYWORDS = ["marseille", "luminy", "madagascar", "grenoble", "nimes"]

async def send_instant_alert(message):
    """Sends the consolidated alert message to the bot."""
    # --- MODIFIED: Check for the original secret names ---
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set in repository secrets. Cannot send alert.")
        return
    try:
        # --- MODIFIED: Use the original secret names ---
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        
        if len(message) > 4096:
            for part in [message[i:i+4096] for i in range(0, len(message), 4096)]:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=part, parse_mode='HTML')
                await asyncio.sleep(0.5)
        else:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        print("Successfully sent consolidated keyword alert.")
    except Exception as e:
        print(f"Failed to send instant alert: {e}")

def get_all_listings():
    """Fetches all listings and returns a list of keyword alert data."""
    alerts_to_send = []
    page = 1
    print("Starting to fetch all listings and check for keywords...")
    address_pattern = re.compile(r'\b(\d{5})\b\s+([A-ZÀ-Ÿ\s\'-]+)')

    while True:
        print(f"Fetching page {page}...")
        try:
            json_payload = {"idTool": 41, "page": page, "pageSize": 50, "location": None}
            headers = {"User-Agent": "Crous-Monitor/2.0", "Referer": "https://trouverunlogement.lescrous.fr/"}
            response = requests.post(API_SEARCH_URL, headers=headers, json=json_payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            listings_on_page = data.get('results', {}).get('items', [])

            if not listings_on_page:
                print("Found an empty page. All listings have been fetched.")
                break

            for item in listings_on_page:
                try:
                    residence_info = item.get('residence', {})
                    full_address = residence_info.get('address', '')
                    residence_name = residence_info.get('label', 'N/A')
                    listing_label = item.get('label', 'N/A')
                    listing_title = f"{listing_label} - {residence_name}"
                    text_to_search = (residence_name + " " + full_address).lower()

                    for keyword in ALERT_KEYWORDS:
                        if keyword in text_to_search:
                            listing_id = str(item.get('id', 'NO_ID'))
                            listing_link = f"https://trouverunlogement.lescrous.fr/tools/41/accommodations/{listing_id}"
                            alert_data = {
                                "keyword": keyword, "title": listing_title,
                                "link": listing_link, "address": full_address
                            }
                            alerts_to_send.append(alert_data)
                            break
                except Exception as e:
                    print(f"Could not process an item: {e}")

            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"An error occurred during fetch: {e}. Stopping.")
            break

    print(f"\nFinished fetching. Found {len(alerts_to_send)} keyword alerts.")
    return alerts_to_send

async def main():
    alerts = get_all_listings()

    if alerts:
        print(f"Consolidating {len(alerts)} keyword alerts into one message...")
        message_parts = [f"🚨 <b>{len(alerts)} Keyword Alert(s) Found!</b>\n"]
        for alert in alerts:
            message_parts.append("\n" + "─" * 15 + "\n")
            message_parts.append(f"<b>Keyword: '{alert['keyword'].title()}'</b>\n")
            message_parts.append(f"• <a href='{alert['link']}'>{alert['title']}</a>\n")
            message_parts.append(f"📍 {alert['address']}\n")
        
        final_alert_message = "".join(message_parts)
        await send_instant_alert(final_alert_message)
    else:
        print("No keyword matches found during this run.")

if __name__ == "__main__":
    asyncio.run(main())
