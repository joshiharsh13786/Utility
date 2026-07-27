import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Dispatches formatted message strings directly to the target Telegram bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram Configuration Secrets.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"Telegram API Gateway Code: {res.status_code}")
    except Exception as e:
        print(f"Network error pushing text data: {e}")

def get_live_gmp():
    """Extracts real-time calculated numeric GMP values mapped by lowercase asset string identifiers."""
    gmp_map = {}
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if not table:
            return gmp_map
            
        for row in table.find_all('tr')[1:]:
            cols = [td.text.strip() for td in row.find_all('td')]
            if len(cols) >= 7:
                # Normalizes complex company tracking name keys
                raw_name = cols[0].split("IPO")[0].strip().lower()
                clean_name = re.sub(r'[^a-z0-9 ]', '', raw_name)
                
                # Grabs the explicit premium percentage column
                gmp_pct_str = cols[2].replace('%', '').strip()
                try:
                    gmp_map[clean_name] = float(gmp_pct_str)
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error fetching production GMP records: {e}")
    return gmp_map

def check_ipos():
    """Parses closing tracks from Chittorgarh and enforces filters against production thresholds."""
    chittorgarh_url = "https://www.chittorgarh.com/report/ipo-subscription-status-live-bidding-data-bse-nse/21/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(chittorgarh_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
    except Exception as e:
        print(f"Chittorgarh connection failed: {e}")
        return
        
    if not table:
        print("Chittorgarh data layout mismatch detected.")
        return

    live_gmp_database = get_live_gmp()
    today_stamp = datetime.today().strftime('%d-%b-%Y') # Standard structural format match
    alert_triggered = False
    
    for row in table.find_all('tr')[1:]:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) < 7:
            continue
            
        ipo_name = cols[0]
        close_date = cols[1]
        
        # Pulls overall composite bidding multiples
        sub_text = cols[6].lower().replace('x', '').strip()
        
        if today_stamp in close_date:
            try:
                subscription_multiple = float(sub_text)
                
                # Normalizes raw name string for cross-checking dictionary records
                search_name = re.sub(r'[^a-z0-9 ]', '', ipo_name.lower())
                matched_gmp_value = 0.0
                
                for key_market_name, premium_value in live_gmp_database.items():
                    if key_market_name in search_name or search_name in key_market_name:
                        matched_gmp_value = premium_value
                        break
                
                # STRATEGY MATCH FILTER: Subscription > 30X AND Dynamic Premium Percentage > 15%
                if subscription_multiple >= 30.0 and matched_gmp_value >= 15.0:
                    message = (
                        f"🚨 *IPO High-Alpha Alert!* 🚨\n\n"
                        f"🏢 *Company:* {ipo_name}\n"
                        f"📅 *Deadline:* TODAY ({close_date})\n"
                        f"🔥 *Subscription Status:* {subscription_multiple}x (Target: >30x)\n"
                        f"📈 *Dynamic Market GMP:* {matched_gmp_value}% (Target: >15%)\n"
                    )
                    send_telegram_message(message)
                    alert_triggered = True
            except ValueError:
                continue

    if not alert_triggered:
        print("No open IPOs satisfied threshold criteria metrics during today's scan.")

if __name__ == "__main__":
    check_ipos()
