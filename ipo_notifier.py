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
        res = requests.post(url, json=payload, timeout=10)
        print(f"Telegram Delivery Code: {res.status_code}")
    except Exception as e:
        print(f"Network error pushing text alert: {e}")

def check_ipos():
    # Direct tabular tracking path on InvestorGain
    url = "https://www.investorgain.com/report/ipo-gmp-live/331/ipo/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"InvestorGain connection failed: {e}")
        return

    table = soup.find('table')
    if not table:
        print("🚨 Error: Unable to locate structural table layout on target route.")
        return

    rows = table.find_all('tr')
    print(f"Successfully loaded data register. Processing {len(rows) - 1} live entries...")

    today_str = datetime.today().strftime('%d-%b')  # Generates string matching target formats like '27-Jul'
    alert_triggered = False

    for row in rows[1:]:  # Skip header row
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) < 6:
            continue

        # Positional coordinate data mapping across standard columns
        raw_name = cols[0].replace('IPO', '').replace('Ltd', '').strip()
        sub_text = cols[2].lower().replace('x', '').strip() if cols[2] else "0.0"
        gmp_text = cols[1] if cols[1] else ""
        close_date = cols[5] if cols[5] else ""

        # 1. Parse Subscription count
        try:
            subscription = float(sub_text) if sub_text and sub_text != '-' else 0.0
        except ValueError:
            subscription = 0.0

        # 2. Extract GMP percentage using clean, isolated regex markers
        gmp_pct = 0.0
        pct_match = re.search(r'\(([\+\-0-9\.]+)%\)', gmp_text)
        if pct_match:
            try:
                gmp_pct = float(pct_match.group(1))
            except ValueError:
                gmp_pct = 0.0

        print(f"📊 Evaluated Asset: {raw_name} | Close Date: {close_date} | Sub: {subscription}x | GMP: {gmp_pct}%")

        # CRITERIA STEP 1: Deadline match check verifying final day is TODAY
        if today_str.lower() in close_date.lower():
            # CRITERIA STEP 2 & 3: Match numeric bounds against user targets
            if gmp_pct >= 12.0 and subscription >= 5.0:
                message = (
                    f"🚨 *InvestorGain Action Trigger!* 🚨\n\n"
                    f"🏢 *Company Name:* {raw_name}\n"
                    f"📅 *Deadline:* TODAY ({close_date})\n"
                    f"🔥 *Subscription Status:* {subscription}x (Target: >5x)\n"
                    f"📈 *Live Scraped GMP:* {gmp_pct}% (Target: >12%)\n"
                )
                send_telegram_message(message)
                alert_triggered = True
            else:
                print(f"   ↳ ❌ Dropped: Below alpha targets. Present metrics: {subscription}x Sub, {gmp_pct}% GMP.")
        else:
            print(f"   ↳ ⏳ Skipped: Target end date ({close_date}) is not today ({today_str}).")

    if not alert_triggered:
        print("🏁 Scan Completed. No running IPOs satisfied all metrics filtering constraints today.")

if __name__ == "__main__":
    check_ipos()
