import os
import time
import pandas as pd
import pyotp
from datetime import datetime
from dotenv import load_dotenv
from SmartApi import SmartConnect

# ---------------- LOAD ENV ---------------- #
load_dotenv()

API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# ---------------- LOGIN ---------------- #
totp = pyotp.TOTP(TOTP_SECRET).now()
smartApi = SmartConnect(API_KEY)
smartApi.generateSession(CLIENT_ID, PASSWORD, totp)

print("✅ Login Successful")
print("🚀 Ultra Fast Pressure Engine (3 sec)\n")

# ---------------- SYMBOLS ---------------- #
symbols = {
    "IDEA": "14366",
    "YESBANK": "11915"
}

previous_data = {}

# ---------------- FILE ---------------- #
today = datetime.now().strftime("%Y-%m-%d")
os.makedirs("data", exist_ok=True)
file_path = f"data/live_data_{today}.csv"

# Create header if not exists
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Time",
        "Symbol",
        "LTP",
        "Buy_Qty",
        "Sell_Qty",
        "Diff",
        "Prev_Buy",
        "Buy_Diff",
        "Buy_%_Change",
        "Signal"
    ]).to_csv(file_path, index=False)

# ---------------- LOOP ---------------- #
while True:
    try:
          # clear terminal (Windows)

        print("="*80)
        print("📊 LIVE MARKET DASHBOARD  |", datetime.now().strftime("%H:%M:%S"))
        print("="*80)

        rows = []

        for symbol, token in symbols.items():

            data = smartApi.getMarketData(
                mode="FULL",
                exchangeTokens={"NSE": [token]}
            )

            quote = data["data"]["fetched"][0]
            ltp = quote.get("ltp", 0)

            depth = quote.get("depth", {})
            buy_qty = sum(level["quantity"] for level in depth.get("buy", []))
            sell_qty = sum(level["quantity"] for level in depth.get("sell", []))

            diff = buy_qty - sell_qty

            # -------- PREVIOUS -------- #
            prev_buy = previous_data.get(symbol, {}).get("buy", buy_qty)

            buy_diff = buy_qty - prev_buy
            buy_change = (buy_diff / prev_buy * 100) if prev_buy else 0

            # -------- SIGNAL -------- #
            if buy_change >= 2:
                signal = "🟢 BUY"
            elif buy_change <= -2:
                signal = "🔴 SELL"
            else:
                signal = "⚪ NEUTRAL"

            # store current
            previous_data[symbol] = {
                "buy": buy_qty
            }

            # -------- TERMINAL UI -------- #
            print(f"""
{symbol}  | LTP: ₹{ltp}
----------------------------------------
Buy Qty   : {buy_qty:,}
Sell Qty  : {sell_qty:,}
Difference: {diff:,}

Prev Buy  : {prev_buy:,}
Buy Change: {buy_diff:,}
Buy %     : {buy_change:.2f}%

👉 SIGNAL : {signal}
----------------------------------------
""")

            # -------- CSV ROW -------- #
            rows.append([
                datetime.now().strftime("%H:%M:%S"),
                symbol,
                ltp,
                buy_qty,
                sell_qty,
                diff,
                prev_buy,
                buy_diff,
                round(buy_change, 2),
                signal
            ])

        df = pd.DataFrame(rows)
        df.to_csv(file_path, mode="a", header=False, index=False)

        time.sleep(3)

    except Exception as e:
        print("Error:", e)
        time.sleep(2)