import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration from Github Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def check_ipos():
    # Chittorgarh main IPO list page
    url = "https://chittorgarh.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch data from Chittorgarh")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table') # Locates the primary IPO list table
    
    if not table:
        return

    today_str = datetime.today().strftime('%b %d, %Y') # Matches Chittorgarh date format like 'Jul 27, 2026'
    alert_triggered = False
    
    for row in table.find_all('tr')[1:]: # Skip header row
        cols = row.find_all('td')
        if len(cols) < 6:
            continue
            
        ipo_name = cols[0].text.strip()
        close_date = cols[2].text.strip()  # Last application date
        
        # Condition 1: Check if today is the last application date
        if today_str in close_date:
            try:
                # Note: Chittorgarh places GMP and Subscriptions on specific sub-pages. 
                # This logic parses the text strings. Adjust indices based on active page columns.
                subscription = float(cols[4].text.replace('x', '').strip()) 
                gmp_text = cols[5].text.replace('%', '').strip()
                gmp = float(gmp_text) if gmp_text else 0
                
                # Condition 2 & 3: GMP > 12% and Subscription > 5X
                if gmp > 12.0 and subscription > 5.0:
                    message = (
                        f"🚨 *High Priority IPO Alert!* 🚨\n\n"
                        f"📌 *Name:* {ipo_name}\n"
                        f"📅 *Closing Today:* {close_date}\n"
                        f"📈 *GMP:* {gmp}%\n"
                        f"🔥 *Subscription:* {subscription}x\n"
                    )
                    send_telegram_message(message)
                    alert_triggered = True
            except ValueError:
                continue # Safely skip rows with missing/unformatted data

    if not alert_triggered:
        print("No IPOs matched your target filters today.")

if __name__ == "__main__":
    check_ipos()
