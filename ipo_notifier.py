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

def get_live_gmp():
    """Extracts explicit percentage returns calculated via live Cap Prices."""
    gmp_map = {}
    url = "https://investorgain.com"
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
                # 1. Standardize string structures safely
                raw_name = cols[0].split("IPO")[0].strip().lower()
                clean_name = re.sub(r'[^a-z0-9]', '', raw_name)
                
                try:
                    # 2. Extract upper price band cap value
                    price_str = cols[1].replace('₹', '').split('-')[-1].strip()
                    cap_price = float(price_str) if price_str else 1.0
                    
                    # 3. Read raw cash market currency premium
                    raw_gmp_cash = cols[2].replace('₹', '').replace('▼', '').replace('▲', '').replace('─', '').strip()
                    gmp_cash = float(raw_gmp_cash) if raw_gmp_cash else 0.0
                    
                    # 4. Math compute true premium ratio yield %
                    calculated_percentage = (gmp_cash / cap_price) * 100
                    gmp_map[clean_name] = round(calculated_percentage, 2)
                    print(f"Parsed Market: {clean_name} -> Price: {cap_price}, Premium Cash: ₹{gmp_cash} ({round(calculated_percentage, 2)}%)")
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        print(f"InvestorGain extract error: {e}")
    return gmp_map

def check_ipos():
    chittorgarh_url = "https://chittorgarh.com"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(chittorgarh_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
    except Exception as e:
        print(f"Chittorgarh communication error: {e}")
        return
        
    if not table:
        print("Data interface altered on host portal.")
        return

    live_gmp_database = get_live_gmp()
    # Converts format matching '27-Jul-2026'
    today_stamp = datetime.today().strftime('%d-%b-%Y') 
    alert_triggered = False
    
    for row in table.find_all('tr')[1:]:
        cols = [td.text.strip() for td in row.find_all('td')]
        if len(cols) < 6:
            continue
            
        # Clean company text arrays explicitly
        ipo_name_raw = cols[0].split("IPO")[0].strip()
        search_name = re.sub(r'[^a-z0-9]', '', ipo_name_raw.lower())
        
        close_date = cols[2]
        sub_text = cols[5].lower().replace('x', '').strip()
        
        if today_stamp in close_date:
            try:
                subscription_multiple = float(sub_text)
                matched_gmp_value = 0.0
                
                # Loose structural name matrix matching loop
                for key_market_name, premium_percentage in live_gmp_database.items():
                    if key_market_name in search_name or search_name in key_market_name:
                        matched_gmp_value = premium_percentage
                        break
                
                print(f"Checking: {ipo_name_raw} | Sub: {subscription_multiple}x | Matched calculated GMP: {matched_gmp_value}%")
                
                # CORE THRESHOLD RULE: Subscriptions > 5X AND Yield Return > 12%
                if subscription_multiple >= 5.0 and matched_gmp_value >= 12.0:
                    message = (
                        f"🚨 *Alpha IPO Trade Triggered!* 🚨\n\n"
                        f"🏢 *Company:* {ipo_name_raw}\n"
                        f"📅 *Deadline:* TODAY ({close_date})\n"
                        f"🔥 *Bidding Volume:* {subscription_multiple}x (Target: >5x)\n"
                        f"📈 *Derived Premium:* {matched_gmp_value}% (Target: >12%)\n"
                    )
                    send_telegram_message(message)
                    alert_triggered = True
            except ValueError:
                continue

    if not alert_triggered:
        print("No running assets reached criteria boundaries inside today's cycle profile.")

if __name__ == "__main__":
    check_ipos()
