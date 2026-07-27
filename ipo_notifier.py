import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing API configuration secrets.")
        return
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=15)
        print(f"Telegram Delivery Code: {res.status_code}")
    except Exception as e:
        print(f"Network error pushing text alert: {e}")

def check_ipos():
    url = "https://investorgain.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"InvestorGain connection failed: {e}")
        return

    table = soup.find('table')
    if not table:
        print("🚨 Error: Unable to locate the tabular grid structure on InvestorGain.")
        return

    rows = table.find_all('tr')
    today_str = datetime.today().strftime('%d-%b')  # Generates '27-Jul'
    alert_triggered = False

    for row in rows[1:]:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) < 7:
            continue

        raw_name = cols[0].replace('IPO', '').replace('Ltd', '').strip()
        gmp_text = cols[1]  
        sub_text = cols[2].lower().replace('x', '').strip()
        close_date = cols[6]  

        try:
            subscription = float(sub_text) if sub_text and sub_text != '-' else 0.0
        except ValueError:
            subscription = 0.0

        gmp_pct = 0.0
        pct_match = re.search(r'\(([\+\-0-9\.]+)%\)', gmp_text)
        if pct_match:
            try:
                gmp_pct = float(pct_match.group(1))
            except ValueError:
                gmp_pct = 0.0

        # GLOBAL DIAGNOSTIC LOG (Prints every asset found)
        print(f"📊 Tracking Asset: {raw_name} | Close Date: {close_date} | Sub: {subscription}x | GMP: {gmp_pct}%")

        # CRITERIA STEP 1: Verify if the deadline matches today
        if today_str.lower() in close_date.lower():
            # CRITERIA STEP 2 & 3: Evaluate subscription volumes and GMP thresholds
            if gmp_pct >= 12.0 and subscription >= 5.0:
                message = (
                    f"🚨 *InvestorGain Alpha Trigger!* 🚨\n\n"
                    f"🏢 *Company Name:* {raw_name}\n"
                    f"📅 *Deadline:* TODAY ({close_date})\n"
                    f"🔥 *Subscription Status:* {subscription}x (Target: >5x)\n"
                    f"📈 *Live Scraped GMP:* {gmp_pct}% (Target: >12%)\n"
                )
                send_telegram_message(message)
                alert_triggered = True
            else:
                print(f"   ↳ ❌ Dropped: Below target metrics (Needed: >5x Sub, >12% GMP). Current Sub: {subscription}x")
        else:
            print(f"   ↳ ⏳ Skipped: Final application deadline ({close_date}) is not today.")

    if not alert_triggered:
        print("🏁 Scan Completed. No running IPOs satisfied all filtering constraints today.")

if __name__ == "__main__":
    check_ipos()
