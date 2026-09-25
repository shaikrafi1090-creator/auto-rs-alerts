import pandas as pd
import yfinance as yf
import requests
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def run_daily_scan():
    try:
        df = pd.read_csv("BVVBBVBV (7)_2.csv")
        df['Symbol'] = df['Symbol'].astype(str).str.strip().str.upper()
        symbols = df['Symbol'].tolist()
        
        yf_symbols = [f"{sym}.NS" for sym in symbols]
        hist = yf.download(yf_symbols, period="2y", interval="1d", progress=False)
        
        if "Close" in hist:
            closes = hist["Close"]
        else:
            closes = hist
            
        closes = closes.ffill().bfill()
        data = []
        
        for sym, yf_sym in zip(symbols, yf_symbols):
            if yf_sym in closes.columns:
                series = closes[yf_sym].dropna()
                
                if len(series) >= 255:
                    current_price = series.iloc[-1]
                    daily_returns = series.pct_change() * 100
                    
                    sum_20 = daily_returns.iloc[-20:].sum()
                    sum_60 = daily_returns.iloc[-80:-20].sum()
                    sum_80 = daily_returns.iloc[-160:-80].sum()
                    sum_90 = daily_returns.iloc[-250:-160].sum()
                    composite_today = sum_20 + sum_60 + sum_80 + sum_90
                    
                    prev_20 = daily_returns.iloc[-25:-5].sum()
                    prev_60 = daily_returns.iloc[-85:-25].sum()
                    prev_80 = daily_returns.iloc[-165:-85].sum()
                    prev_90 = daily_returns.iloc[-255:-165].sum()
                    composite_prev = prev_20 + prev_60 + prev_80 + prev_90
                    
                    data.append({
                        "Symbol": sym, 
                        "Price": round(current_price, 2),
                        "RS_Today": composite_today,
                        "RS_Prev": composite_prev
                    })
                    
        res_df = pd.DataFrame(data)
        
        if not res_df.empty:
            res_df["Today Pct"] = res_df["RS_Today"].rank(pct=True, ascending=False)
            res_df["Prev Pct"] = res_df["RS_Prev"].rank(pct=True, ascending=False)
            
            breakouts = []
            for _, row in res_df.iterrows():
                if row["Prev Pct"] >= 0.65 and row["Today Pct"] <= 0.35:
                    breakouts.append(f"🚀 Epic Breakout: *{row['Symbol']}* (₹{row['Price']})")
                elif row["Prev Pct"] > 0.35 and row["Today Pct"] <= 0.35:
                    breakouts.append(f"🔥 Entered Green: *{row['Symbol']}* (₹{row['Price']})")
            
            if breakouts:
                msg = "📊 *Daily RS Breakout Alerts*\n\n" + "\n".join(breakouts)
                send_telegram_alert(msg)
                
    except Exception as e:
        print(f"Error during scan: {e}")

if __name__ == "__main__":
    run_daily_scan()
