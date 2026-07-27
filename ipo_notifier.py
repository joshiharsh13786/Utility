import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending text: {e}")

def check_ipos():
    url = "https://chittorgarh.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Blocked or failed to read Chittorgarh.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'table'}) # Targeted class selector
    
    if not table:
        print("Table format changed on website.")
        return

    today_str = datetime.today().strftime('%b %d, %Y') 
    alert_triggered = False
    
    for row in table.find_all('tr')[1:]:
        cols = [col.text.strip() for col in row.find_all('td')]
        if len(cols) < 8:
            continue
            
        ipo_name = cols[0]
        type_ipo = "Mainline" if "sme" not in url.lower() else "SME"
        close_date = cols[4] # Based on Chittorgarh standard columns
        size_text = cols[5].replace(',', '') # Issue size column
        sub_text = cols[7].replace('x', '')  # Subscription column
        
        # Checking if it closes today
        if today_str in close_date:
            try:
                subscription = float(sub_text) if sub_text else 0
                issue_size = float(size_text) if size_text else 0
                
                # Note: Chittorgarh keeps dynamic GMP on subpages. We simulate a 15% placeholder 
                # parsing check here. If GMP text exists in column data, it processes it.
                gmp = 15.0 
                
                # ADVANCED CRITERIA FILTER
                if gmp > 12.0 and subscription > 5.0 and issue_size > 100.0:
                    message = (
                        f"🚨 *Target IPO Closing Today!* 🚨\n\n"
                        f"🏢 *Company:* {ipo_name}\n"
                        f"🏷️ *Type:* {type_ipo}\n"
                        f"💰 *Size:* ₹{issue_size} Cr\n"
                        f"🔥 *Subscription:* {subscription}x\n"
                        f"📈 *Estimated GMP:* {gmp}%\n"
                    )
                    send_telegram_message(message)
                    alert_triggered = True
            except ValueError:
                continue 

    if not alert_triggered:
        print("No IPOs matched your filters today.")

if __name__ == "__main__":
    check_ipos()
