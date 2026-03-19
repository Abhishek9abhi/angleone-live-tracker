import time
import os 
import requests
import pyotp
from datetime import datetime
from collections import deque
import pandas as pd

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volume import VolumeWeightedAveragePrice

# -------- TELEGRAM -------- #
BOT_TOKEN = "8261206773:AAHZuexLEn6g-fne6fLPI2PSceAlUsuX-eg"
CHAT_ID = "8565808280"

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

# -------- LOGIN -------- #
API_KEY = "API_KEY"
CLIENT_ID = "CLIENT_ID"
PASSWORD = "PASSWORD"
TOTP_SECRET = os.getenv("TOTP_SECRET") TOTP = pyotp.TOTP(TOTP_SECRET).now()

obj = SmartConnect(API_KEY)
session = obj.generateSession(CLIENT_ID, PASSWORD, TOTP)

AUTH_TOKEN = session["data"]["jwtToken"]
FEED_TOKEN = obj.getfeedToken()

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

# -------- DATA STORAGE -------- #
tick_data = {s: deque(maxlen=300) for s in stocks}
prev_data = {}
last_signal = {}

# -------- TELEGRAM BUTTON -------- #
def build_message(symbol, data, indicators):

    return f"""
📊 {symbol}

💰 LTP: {data['ltp']}
📈 Buy: {data['buy']}
📉 Sell: {data['sell']}

🔄 Buy%: {data['buy_pct']:.2f}%
🔄 Sell%: {data['sell_pct']:.2f}%

📊 Indicators:
RSI: {indicators.get('RSI')}
MACD: {indicators.get('MACD')}
EMA: {indicators.get('EMA')}
ADX: {indicators.get('ADX')}
"""

# -------- INDICATORS -------- #
def get_indicators(symbol):
    df = pd.DataFrame(tick_data[symbol])
    if len(df) < 20:
        return {}

    rsi = RSIIndicator(df["ltp"]).rsi().iloc[-1]
    macd = MACD(df["ltp"]).macd().iloc[-1]
    ema = EMAIndicator(df["ltp"]).ema_indicator().iloc[-1]
    adx = ADXIndicator(df["ltp"], df["ltp"], df["ltp"]).adx().iloc[-1]

    return {
        "RSI": round(rsi, 2),
        "MACD": round(macd, 2),
        "EMA": round(ema, 2),
        "ADX": round(adx, 2)
    }

# -------- SIGNAL -------- #
def get_signal(buy_pct, sell_pct):

    if buy_pct >= 10:
        return "🟢 BUY SIGNAL"
    elif buy_pct <= -10:
        return "🔴 SELL SIGNAL"

    if sell_pct >= 10:
        return "🔴 SELL PRESSURE"
    elif sell_pct <= -10:
        return "🟢 BUY PRESSURE"

    return None

# -------- WEBSOCKET CALLBACK -------- #
def on_data(ws, message):

    token = message["token"]
    ltp = message.get("last_traded_price", 0)

    symbol = None
    for k, v in stocks.items():
        if v == token:
            symbol = k
            break

    if not symbol:
        return

    buy = message.get("total_buy_quantity", 0)
    sell = message.get("total_sell_quantity", 0)

    tick_data[symbol].append({
        "ltp": ltp,
        "buy": buy,
        "sell": sell
    })

# -------- START SOCKET -------- #
sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_ID, FEED_TOKEN)

def on_open(ws):
    sws.subscribe("abc123", 1, list(stocks.values()))

sws.on_open = on_open
sws.on_data = on_data

sws.connect(threaded=True)

# -------- MAIN LOOP -------- #
while True:

    now = datetime.now().time()

    if now < datetime.strptime("09:00", "%H:%M").time() or now > datetime.strptime("15:30", "%H:%M").time():
        time.sleep(30)
        continue

    for symbol in stocks:

        data_list = tick_data[symbol]
        if len(data_list) < 2:
            continue

        last = data_list[-1]
        prev = data_list[-2]

        buy_diff = last["buy"] - prev["buy"]
        sell_diff = last["sell"] - prev["sell"]

        buy_pct = (buy_diff / prev["buy"] * 100) if prev["buy"] else 0
        sell_pct = (sell_diff / prev["sell"] * 100) if prev["sell"] else 0

        data = {
            "ltp": last["ltp"],
            "buy": last["buy"],
            "sell": last["sell"],
            "buy_pct": buy_pct,
            "sell_pct": sell_pct
        }

        signal = get_signal(buy_pct, sell_pct)

        if signal and last_signal.get(symbol) != signal:

            indicators = get_indicators(symbol)
            msg = build_message(symbol, data, indicators) + f"\n🚨 {signal}"

            send(msg)
            last_signal[symbol] = signal

    time.sleep(3)
