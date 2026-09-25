import os
import pandas as pd
import requests
import yfinance as yf

# GitHub Secrets se Telegram Token aur Chat ID uthana
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    """Telegram par alert message bhejne ka function."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token ya Chat ID missing hai!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram message bhejne mein error: {e}")

def run_daily_scan():
    """Daily market data scan karke breakout/breakdown check karna."""
    try:
        print("CSV file read kar rahe hain...")
        # 1. Apna exact CSV filename yahan rakhein
        df = pd.read_csv("BVVBBVBV (7)_2.csv")
        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
        symbols = df["Symbol"].tolist()
        
        # Yahoo finance ke liye .NS lagana
        yf_symbols = [f"{sym}.NS" for sym in symbols]
        
        print(f"{len(yf_symbols)} stocks ka 3 saal ka data download ho raha hai...")
        # 2. 3 saal (3y) ka data taaki long term trend aur transitions identify ho sakein
        hist = yf.download(yf_symbols, period="3y", interval="1d", progress=False)
        
        if "Close" in hist:
            closes = hist["Close"]
        else:
            closes = hist
            
        closes = closes.ffill().bfill()
        
        print("Daily Returns aur 250-Day Momentum calculate ho raha hai...")
        # 3. Daily returns calculate karna
        daily_returns = closes.pct_change() * 100
        
        # 4. 250-Day Rolling Momentum (Pichle 250 dino ka sum)
        rolling_rs = daily_returns.rolling(window=250).sum()
        
        # 5. Har din ki cross-sectional ranking (Top 35% vs Bottom 35%)
        # ascending=False ka matlab hai sabse highest momentum ko rank 1 (0.0 percentile) milega
        daily_ranks = rolling_rs.rank(axis=1, pct=True, ascending=False)
        
        alerts = []
        
        print("Har stock ki life cycle check ho rahi hai...")
        # 6. Har stock ki past history (Zones) check karna
        for sym, yf_sym in zip(symbols, yf_symbols):
            if yf_sym not in daily_ranks.columns:
                continue
                
            # NaNs hata kar stock ki rank history nikalna
            stock_ranks = daily_ranks[yf_sym].dropna().tolist()
            if len(stock_ranks) < 2:
                continue
                
            # Ranks ko Colors/Zones mein convert karna: G (Green), R (Red), Y (Grey)
            zones = []
            for rank in stock_ranks:
                if rank <= 0.35:
                    zones.append('G')  # Top 35% (Green)
                elif rank >= 0.65:
                    zones.append('R')  # Bottom 35% (Red)
                else:
                    zones.append('Y')  # Middle 30% (Grey)
                    
            curr_zone = zones[-1]   # Aaj ka zone
            prev_zone = zones[-2]   # 1 din pehle ka zone
            
            # Stock ka current price (Alert message mein dikhane ke liye)
            current_price = closes[yf_sym].dropna().iloc[-1]
            
            # =========================================================
            # LOGIC 1: BREAKOUT (Pichla zone Red tha, aur aaj Green hua)
            # =========================================================
            if curr_zone == 'G' and prev_zone != 'G':
                # Aaj pehla din hai jab yeh wapas Green mein enter hua hai.
                # Ab reverse mein check karo ki last solid zone kaunsa tha (Grey skip karke)
                last_main_zone = None
                for past_z in reversed(zones[:-1]):
                    if past_z in ['G', 'R']:
                        last_main_zone = past_z
                        break
                        
                # Agar pichla main zone Red tha, toh ye Confirm Breakout hai!
                if last_main_zone == 'R':
                    alerts.append(f"🚀 *Red-to-Green Breakout:* *{sym}* (₹{current_price:.2f})")
                    
            # =========================================================
            # LOGIC 2: BREAKDOWN (Pichla zone Green tha, aur aaj Red hua)
            # =========================================================
            elif curr_zone == 'R' and prev_zone != 'R':
                # Aaj pehla din hai jab yeh wapas Red mein gira hai.
                # Ab reverse mein check karo ki last solid zone kaunsa tha (Grey skip karke)
                last_main_zone = None
                for past_z in reversed(zones[:-1]):
                    if past_z in ['G', 'R']:
                        last_main_zone = past_z
                        break
                        
                # Agar pichla main zone Green tha, toh ye Confirm Breakdown hai!
                if last_main_zone == 'G':
                    alerts.append(f"🔻 *Green-to-Red Breakdown:* *{sym}* (₹{current_price:.2f})")

        # 7. Final Alerts Telegram par bhejna
        if alerts:
            msg = "📊 *True Cycle Zone Alerts*\n\n" + "\n".join(alerts)
            print("Alerts mil gaye! Telegram par bhej rahe hain...")
            send_telegram_alert(msg)
            print("Telegram alert successfully sent!")
        else:
            print("Aaj kisi bhi stock ne Red-to-Green ya Green-to-Red true transition complete nahi kiya. No alerts today.")
            
    except Exception as e:
        print(f"Error during scan: {e}")

if __name__ == "__main__":
    print("Bot start ho raha hai...")
    run_daily_scan()
    print("Scan complete.")
