import os
import time
import logging
import yfinance as yf
import pandas as pd
from alpaca_trade_api.rest import REST

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === API CONFIG ===
API_KEY = "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === SETTINGS ===
TRADE_PERCENT = 0.10
MIN_RR = 2.5
LOOKBACK = 50
ZONE_MARGIN = 0.5  # extra room for stops
BATCH_SIZE = 20

# === TICKERS ===
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "JNJ", "WMT", "XOM", "PG", "MA", "HD", "CVX", "LLY", "ABBV",
    "AVGO", "KO", "PEP", "MRK", "BAC", "COST", "ADBE", "PFE", "TMO", "CSCO",
    "ABT", "ACN", "MCD", "QCOM", "DHR", "VZ", "NEE", "TXN", "LIN", "INTC",
    "CRM", "NKE", "ORCL", "WFC", "AMGN", "AMD", "LOW", "UPS", "SCHW", "PM"
]

positions = {}
batch_index = 0

# === DETECT TREND ===
def detect_trend(df):
    highs = df['High']
    lows = df['Low']
    if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
        return "uptrend"
    elif highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
        return "downtrend"
    return "sideways"

# === FIND ZONE ===
def find_demand_zone(df):
    for i in range(len(df)-2, 0, -1):
        body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
        prev_bodies = abs(df['Close'].iloc[i-2:i] - df['Open'].iloc[i-2:i]).mean()
        if body > 2 * prev_bodies and df['Close'].iloc[i] > df['Open'].iloc[i]:
            return df['Low'].iloc[i-1], df['High'].iloc[i-1]
    return None, None

def find_supply_zone(df):
    for i in range(len(df)-2, 0, -1):
        body = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
        prev_bodies = abs(df['Close'].iloc[i-2:i] - df['Open'].iloc[i-2:i]).mean()
        if body > 2 * prev_bodies and df['Close'].iloc[i] < df['Open'].iloc[i]:
            return df['Low'].iloc[i-1], df['High'].iloc[i-1]
    return None, None

# === CHECK RISK/REWARD ===
def valid_rr(entry, stop, target):
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        return False
    rr = reward / risk
    return rr >= MIN_RR

# === TRADE ===
def trade(symbol, side, price, stop, target):
    try:
        acc = api.get_account()
        bp = float(acc.buying_power)
        qty = max(1, int((bp * TRADE_PERCENT) / price))

        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc"
        )

        positions[symbol] = {
            "side": side,
            "entry": price,
            "stop": stop,
            "target": target,
            "qty": qty
        }

        logging.info(f"TRADE: {side.upper()} {symbol} @ {price:.2f} | Stop: {stop:.2f} | Target: {target:.2f}")
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === RUN ===
def run():
    global batch_index
    batch = TICKERS[batch_index:batch_index+BATCH_SIZE]
    batch_index = (batch_index + BATCH_SIZE) % len(TICKERS)

    for symbol in batch:
        try:
            df = yf.Ticker(symbol).history(period="5d", interval="5m")[-LOOKBACK:]
            if df.empty:
                continue

            trend = detect_trend(df)
            price = df['Close'].iloc[-1]

            if trend == "uptrend":
                low, high = find_demand_zone(df)
                if low is None:
                    continue
                stop = low - ZONE_MARGIN
                target = df['High'].max()
                if low < price < high and valid_rr(price, stop, target):
                    trade(symbol, "buy", price, stop, target)

            elif trend == "downtrend":
                low, high = find_supply_zone(df)
                if low is None:
                    continue
                stop = high + ZONE_MARGIN
                target = df['Low'].min()
                if low < price < high and valid_rr(price, stop, target):
                    trade(symbol, "sell", price, stop, target)

            logging.info(f"{symbol}: {price:.2f} | Trend: {trend}")
        except Exception as e:
            logging.error(f"{symbol} error: {e}")

while True:
    run()
    logging.info("⏳ Waiting 10 seconds...")
    time.sleep(10)
