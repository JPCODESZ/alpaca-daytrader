import os
import time
import logging
import yfinance as yf
import pandas as pd
import requests
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === API CONFIG ===
API_KEY = "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = "https://paper-api.alpaca.markets"
FMP_API_KEY = "eJI8bQkL1Ov2tS307tYaO0VTAaguLoNd"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === SETTINGS ===
RSI_BUY = 45
RSI_SELL = 60
TRADE_PERCENT = 0.10
MAX_TICKERS = 500

# === RSI via Yahoo Finance ===
def get_rsi(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if df.empty:
            return None
        close = df['Close']
        return RSIIndicator(close).rsi().iloc[-1]
    except Exception as e:
        logging.error(f"RSI error {symbol}: {e}")
        return None

# === Get current price ===
def get_price(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        return df['Close'].iloc[-1]
    except Exception as e:
        logging.error(f"Price error {symbol}: {e}")
        return None

# === Get AI signal from FMP ===
def get_ai_score(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v4/score?symbol={symbol}&apikey={FMP_API_KEY}"
        res = requests.get(url).json()
        return float(res[0].get("score", 0)) if isinstance(res, list) and res else 0.0
    except Exception as e:
        logging.error(f"AI score error {symbol}: {e}")
        return 0.0

# === Scan for stock symbols ===
def scan_stocks():
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP_API_KEY}"
        data = requests.get(url).json()
        if not isinstance(data, list):
            logging.error(f"Bad symbol data: {data}")
            return []
        return [x["symbol"] for x in data if x.get("exchangeShortName") in ["NYSE", "NASDAQ"]][:MAX_TICKERS]
    except Exception as e:
        logging.error(f"Scan error: {e}")
        return []

# === Check position ===
def has_position(symbol):
    try:
        pos = api.get_position(symbol)
        return int(pos.qty) > 0
    except:
        return False

# === Submit order ===
def trade(symbol, side, price):
    try:
        bp = float(api.get_account().buying_power)
        qty = max(1, int((bp * TRADE_PERCENT) / price))
        api.submit_order(symbol=symbol, qty=qty, side=side, type="market", time_in_force="gtc")
        logging.info(f"{side.upper()} {symbol} x{qty} @ ${price:.2f}")
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === Check if should exit ===
def should_exit(symbol, current):
    try:
        pos = api.get_position(symbol)
        avg = float(pos.avg_entry_price)
        pnl = (current - avg) / avg * 100
        logging.info(f"{symbol} P/L: {pnl:.2f}%")
        return pnl >= 5 or pnl <= -3
    except Exception as e:
        logging.error(f"Exit check error {symbol}: {e}")
        return False

# === Main run ===
def run():
    symbols = scan_stocks()
    logging.info("Checking market...")
    try:
        acc = api.get_account()
        logging.info(f"Cash: ${acc.cash} | Power: ${acc.buying_power}")
    except Exception as e:
        logging.error(f"Account error: {e}")
        return

    for symbol in symbols:
        price = get_price(symbol)
        rsi = get_rsi(symbol)
        score = get_ai_score(symbol)

        if None in (price, rsi): continue

        logging.info(f"{symbol}: ${price:.2f} | RSI: {rsi:.2f} | AI: {score:.2f}")
        if score < 0.3: continue

        if has_position(symbol):
            if rsi > RSI_SELL or should_exit(symbol, price):
                trade(symbol, "sell", price)
        elif rsi < RSI_BUY:
            trade(symbol, "buy", price)

while True:
    run()
    logging.info("Sleeping 60s...")
    time.sleep(60)
