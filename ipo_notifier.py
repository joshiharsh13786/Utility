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
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
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
        # Fallback to direct page text string parsing if Cloudflare strips table tags
        parse_via_text_fallback(soup.get_text())
        return

    rows = table.find_all('tr')
    print(f"Located grid layout. Processing {len(rows) - 1} raw items...")

    today_str = datetime.today().strftime('%d-%b')  # Generates current date format e.g. '27-Jul'
    alert_triggered = False

    for index, row in enumerate(rows[1:], start=1):
        cols = [td.text.strip() for td in row.find_all('td')]
        
        # VISUAL DEBUG ANCHOR: See exactly what array length is extracted
        print(f"--- Row #{index} Row-Length Checked: {len(cols)} columns found ---")
        if len(cols) == 0:
            continue
        print(f"Raw Row Content Elements: {cols[:4]}") # Prints first few fields for debugging

        if len(cols) < 5: 
            # Relaxed constraint to capture tables that pass responsive layouts
            continue

        raw_name = cols[0].replace('IPO', '').replace('Ltd', '').replace('.', '').strip()
        gmp_text = cols[1] if len(cols) > 1 else ""
        sub_text = cols[2].lower().replace('x', '').strip() if len(cols) > 2 else "0"
        close_date = cols[3] if len(cols) > 3 else ""

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

        print(f"📊 Extracted -> Name: {raw_name} | Close: {close_date} | Sub: {subscription}x | GMP: {gmp_pct}%")

        # CRITERIA STEP 1: Deadline match check
        if today_str.lower() in close_date.lower():
            # CRITERIA STEP 2 & 3: Match alpha criteria limits
            if gmp_pct >= 12.0 and subscription >= 5.0:
                message = (
                    f"🚨 *InvestorGain Production Trigger!* 🚨\n\n"
                    f"🏢 *Company Name:* {raw_name}\n"
                    f"📅 *Deadline:* TODAY ({close_date})\n"
                    f"🔥 *Subscription Status:* {subscription}x (Target: >5x)\n"
                    f"📈 *Live Scraped GMP:* {gmp_pct}% (Target: >12%)\n"
                )
                send_telegram_message(message)
                alert_triggered = True
            else:
                print(f"   ↳ ❌ Dropped: Under alpha targets. Present metrics: {subscription}x Sub, {gmp_pct}% GMP.")
        else:
            print(f"   ↳ ⏳ Skipped: Target end date ({close_date}) is not today ({today_str}).")

    if not alert_triggered and len(rows) > 1:
        print("🏁 Table loop complete. No active items matched your exact metric threshold settings.")

def parse_via_text_fallback(raw_html_text):
    """Fallback block tracking explicitly engineered to clean unstructured text arrays."""
    print("Executing fallback pattern analyzer...")
    today_str = datetime.today().strftime('%d-%b')
    # Scans text block for patterns like: "Indo MIM IPO GMP +15% Close 27-Jul Sub 58.2x"
    matches = re.findall(r'([A-Za-z0-9\s]+?)\s*IPO.*?GMP.*?([\d\.]+)\%.*?Close.*?([\d\-A-Za-z]+).*?Sub.*?([\d\.]+)x', raw_html_text, re.DOTALL | re.IGNORECASE)
    
    for item in matches:
        print(f"Fallback Item Discovered: {item}")

if __name__ == "__main__":
    check_ipos()
