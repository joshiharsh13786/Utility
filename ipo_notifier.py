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
    # Direct tabular source containing all fields natively on InvestorGain
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
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
    print(f"Successfully located grid. Processing {len(rows) - 1} IPO records...")

    today_str = datetime.today().strftime('%d-%b')  # Matches format: '27-Jul'
    alert_triggered = False

    for row in rows[1:]:  # Skip header row
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) < 7:
            continue

        # Column structure extraction mapping based on structural desktop index tracking
        raw_name = cols[0].replace('IPO', '').replace('Ltd', '').strip()
        gmp_text = cols[1]  # Contains both cash premium and percentage inside string structure
        sub_text = cols[2].lower().replace('x', '').strip()
        close_date = cols[5]  # Contains absolute end application timeline tracking data

        # 1. Parse Subscription Volume accurately
        try:
            subscription = float(sub_text) if sub_text and sub_text != '-' else 0.0
        except ValueError:
            subscription = 0.0

        # 2. Extract cleanly nested percentage values from string maps using regular expressions
        # Captures values out of patterns like "+₹168 (+44.02%)"
        gmp_pct = 0.0
        pct_match = re.search(r'\(([\+\-0-9\.]+)%\)', gmp_text)
        if pct_match:
            try:
                gmp_pct = float(pct_match.group(1))
            except ValueError:
                gmp_pct = 0.0
        else:
            # Secondary raw string float converter backup fallback
            clean_gmp_text = gmp_text.replace('%', '').replace('+', '').strip()
            try:
                gmp_pct = float(clean_gmp_text) if clean_gmp_text and clean_gmp_text != '-' else 0.0
            except ValueError:
                gmp_pct = 0.0

        # Diagnostic log printouts to monitor real-time compilation paths inside GitHub Workflow
        print(f"📊 Evaluated Asset: {raw_name} | Close Date: {close_date} | Sub: {subscription}x | GMP: {gmp_pct}%")

        # CRITERIA STEP 1: Verify if deadline matching rule triggers absolute end date TODAY
        if today_str.lower() in close_date.lower():
            
            # CRITERIA STEP 2 & 3: Evaluate numeric volume limits matching threshold bounds
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
                print(f"   ↳ ❌ Dropped: Below target metrics (Needed: >5x Sub, >12% GMP).")

    if not alert_triggered:
        print("🏁 Scan Completed. No running IPOs satisfied all filtering constraints today.")

if __name__ == "__main__":
    check_ipos()
