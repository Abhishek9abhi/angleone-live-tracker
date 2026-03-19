import time
import requests
import pyotp
from datetime import datetime
from collections import deque
import pandas as pd
from SmartApi import SmartConnect
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volume import VolumeWeightedAveragePrice

# -------- TELEGRAM -------- #
BOT_TOKEN = "NEW_TOKEN_HERE"
CHAT_ID = "YOUR_CHAT_ID"

def send(msg, buttons=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = buttons
    requests.post(url, json=data)

# -------- INLINE BUTTON -------- #
def buttons(symbol):
    return {
        "inline_keyboard": [
            [{"text": "📊 Last 15 Min", "callback_data": f"last15_{symbol}"}],
            [{"text": "📈 Indicators", "callback_data": f"ind_{symbol}"}]
        ]
    }

# -------- LOGIN -------- #
API_KEY = "API_KEY"
CLIENT_ID = "CLIENT_ID"
PASSWORD = "PASSWORD"
TOTP_SECRET = "TOTP"

totp = pyotp.TOTP(TOTP_SECRET).now()
smartApi = SmartConnect(API_KEY)
smartApi.generateSession(CLIENT_ID, PASSWORD, totp)

# -------- STOCKS -------- #
stocks = {
    "IDEA": "14366",
    "YESBANK": "11915",
    "ALOKINDS": "13990",
    "PCJEWELLER": "29135",
    "RTNPOWER": "1348",
    "HATHWAY": "13889",
    "HCC": "12051",
    "RPOWER": "2885"
}

prev = {}
history = {s: deque(maxlen=300) for s in stocks}  # 15 min data

last_signal = {}

# -------- LOOP -------- #
while True:

    now = datetime.now().time()

    # Market time control
    if now < datetime.strptime("09:00", "%H:%M").time() or now > datetime.strptime("15:30", "%H:%M").time():
        time.sleep(30)
        continue

    for symbol, token in stocks.items():

        data = smartApi.getMarketData(
            mode="FULL",
            exchangeTokens={"NSE": [token]}
        )

        q = data["data"]["fetched"][0]
        ltp = q["ltp"]

        depth = q.get("depth", {})
        buy = sum(x["quantity"] for x in depth.get("buy", []))
        sell = sum(x["quantity"] for x in depth.get("sell", []))

        # Store history
        history[symbol].append({"ltp": ltp, "buy": buy, "sell": sell})

        prev_buy = prev.get(symbol, {}).get("buy", buy)
        prev_sell = prev.get(symbol, {}).get("sell", sell)

        buy_diff = buy - prev_buy
        sell_diff = sell - prev_sell

        buy_pct = (buy_diff / prev_buy * 100) if prev_buy else 0
        sell_pct = (sell_diff / prev_sell * 100) if prev_sell else 0

        signal = None

        if buy_pct >= 10:
            signal = "🟢 BUY SIGNAL"
        elif buy_pct <= -10:
            signal = "🔴 SELL SIGNAL"

        if sell_pct >= 10:
            signal = "🔴 SELL PRESSURE"
        elif sell_pct <= -10:
            signal = "🟢 BUY PRESSURE"

        # Send alert only when signal changes
        if signal and last_signal.get(symbol) != signal:

            msg = f"""
📊 *{symbol}*

💰 LTP: ₹{ltp}
📈 Buy: {buy}
📉 Sell: {sell}

🔄 Buy%: {buy_pct:.2f}%
🔄 Sell%: {sell_pct:.2f}%

🚨 {signal}
"""

            send(msg, buttons(symbol))
            last_signal[symbol] = signal

        prev[symbol] = {"buy": buy, "sell": sell}

    time.sleep(3)
