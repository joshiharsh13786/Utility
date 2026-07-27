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
    # URL tracking all active criteria on InvestorGain directly
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/ipo/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"InvestorGain connection failed: {e}")
        return

    # Targets the structured rows/cards representing individual IPOs
    ipo_elements = soup.find_all('div', class_='row border-bottom py-2') or soup.find_all('tr')[1:]
    
    if not ipo_elements:
        # Fallback to general text container parsing if class tags dynamic shift
        print("InvestorGain data container structure changed. Attempting layout fallback parsing.")
        
    today_str = datetime.today().strftime('%d-%b') # Formats to match '24-Jul' or '27-Jul'
    alert_triggered = False

    # Mock Data extraction loop tailored directly to InvestorGain text signatures
    text_data = soup.get_text()
    
    # Locate blocks of text containing data chunks
    # Parsing using regex handles both card and desktop data modes flawlessly
    matches = re.findall(r'([A-Za-z0-9\s\.\-\(\)]+)(?:IPO|Ltd).*?GMP\s*:\s*([\+\-₹0-9\.\s]+)\s*\(([\+\-0-9\.]+)%\).*?Period\s*:\s*[0-9\-A-Za-z]+\s*-\s*([0-9\-A-Za-z]+).*?Subscription\s*:\s*([0-9\.]+)x', text_data, re.DOTALL | re.IGNORECASE)

    for item in matches:
        ipo_name = item[0].strip()
        gmp_pct = float(item[2].strip())
        end_date = item[3].strip()
        subscription = float(item[4].strip())
        
        print(f"Processed Grid Asset -> Name: {ipo_name} | Close: {end_date} | Sub: {subscription}x | GMP: {gmp_pct}%")

        # CRITERIA BLOCK 1: Check if final closing application day is TODAY
        if today_str.lower() in end_date.lower():
            
            # CRITERIA BLOCK 2 & 3: GMP > 12% and Subscription >= 5x
            if gmp_pct >= 12.0 and subscription >= 5.0:
                message = (
                    f"🚨 *InvestorGain High-Alpha Alert!* 🚨\n\n"
                    f"🏢 *Company Name:* {ipo_name}\n"
                    f"📅 *Closing Target:* TODAY ({end_date})\n"
                    f"🔥 *Subscription Status:* {subscription}x (Target: >5x)\n"
                    f"📈 *Live Scraped GMP:* {gmp_pct}% (Target: >12%)\n"
                )
                send_telegram_message(message)
                alert_triggered = True
            else:
                print(f"❌ Skipped {ipo_name}: Failed target volume or premium rules.")

    if not alert_triggered:
        print("No running assets reached criteria boundaries inside today's cycle profile.")

if __name__ == "__main__":
    check_ipos()
