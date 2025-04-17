import os
import time
import logging
import yfinance as yf
import pandas as pd
import datetime
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator

# === CONFIG ===
API_KEY = "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = "https://paper-api.alpaca.markets"
RSI_BUY = 45
RSI_SELL = 60
TRADE_PERCENT = 0.10
MAX_TICKERS = 100
SLEEP_SECONDS = 10
POSITION_LOG = {}
COVERED_CALLS = {}

api = REST(API_KEY, API_SECRET, BASE_URL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# === HELPERS ===
def get_rsi(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if df.empty: return None
        return RSIIndicator(df['Close']).rsi().iloc[-1]
    except Exception as e:
        logging.warning(f"[RSI] {symbol} error: {e}")
        return None

def get_price(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        return df['Close'].iloc[-1]
    except Exception as e:
        logging.warning(f"[Price] {symbol} error: {e}")
        return None

def scan_stocks():
    try:
        tickers = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        return tickers["Symbol"].tolist()[:MAX_TICKERS]
    except Exception as e:
        logging.error(f"Scan error: {e}")
        return []

def has_position(symbol):
    try:
        pos = api.get_position(symbol)
        return int(pos.qty) > 0
    except:
        return False

def should_exit(symbol, current_price):
    try:
        if symbol in POSITION_LOG:
            entry = POSITION_LOG[symbol]['entry']
            pnl = (current_price - entry) / entry * 100
            logging.info(f"{symbol} live P/L: {pnl:.2f}%")
            return pnl >= 6 or pnl <= -2.5
        return False
    except Exception as e:
        logging.warning(f"[Exit Check] {symbol}: {e}")
        return False

def trade(symbol, side, price):
    try:
        acc = api.get_account()
        bp = float(acc.buying_power)
        if bp < 50:
            logging.warning(f"Skipping {symbol}: Low buying power ${bp}")
            return
        qty = max(1, int((bp * TRADE_PERCENT) / price))
        api.submit_order(symbol=symbol, qty=qty, side=side, type="market", time_in_force="gtc")
        logging.info(f"🟢 {side.upper()} {symbol} x{qty} @ ${price:.2f}")

        if side == "buy":
            POSITION_LOG[symbol] = {"entry": price, "qty": qty}
            if qty >= 100:
                open_covered_call(symbol, price)
        elif side == "sell" and symbol in POSITION_LOG:
            entry = POSITION_LOG[symbol]['entry']
            pnl = (price - entry) / entry * 100
            logging.info(f"💰 Sold {symbol} for P/L: {pnl:.2f}%")
            if symbol in COVERED_CALLS:
                del COVERED_CALLS[symbol]
            del POSITION_LOG[symbol]
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === COVERED CALL SIMULATION ===
def open_covered_call(symbol, entry_price):
    strike = round(entry_price + 5, 2)
    premium = 2.00
    expiry = datetime.datetime.now() + datetime.timedelta(days=7)

    COVERED_CALLS[symbol] = {
        "entry_price": entry_price,
        "strike": strike,
        "premium": premium,
        "expiry": expiry,
        "shares": 100
    }
    logging.info(f"📥 OPENED Covered Call on {symbol} | Strike: ${strike} | Premium: ${premium}")

def check_covered_calls(current_prices):
    now = datetime.datetime.now()
    for symbol in list(COVERED_CALLS):
        data = COVERED_CALLS[symbol]
        if now >= data["expiry"]:
            price = current_prices.get(symbol, 0)
            if price >= data["strike"]:
                gain = (data["strike"] - data["entry_price"]) * data["shares"] + data["premium"] * data["shares"]
                logging.info(f"📤 {symbol} CALL ASSIGNED @ ${data['strike']} — Profit: ${gain:.2f}")
            else:
                gain = (price - data["entry_price"]) * data["shares"] + data["premium"] * data["shares"]
                logging.info(f"✅ {symbol} CALL EXPIRED — Profit: ${gain:.2f}")
            del COVERED_CALLS[symbol]

# === LOOP ===
while True:
    symbols = scan_stocks()
    try:
        acc = api.get_account()
        logging.info(f"Cash: ${acc.cash} | Buying Power: ${acc.buying_power}")
    except Exception as e:
        logging.warning(f"[Account Error] {e}")
        continue

    current_prices = {}
    for symbol in symbols:
        price = get_price(symbol)
        rsi = get_rsi(symbol)
        if None in (price, rsi):
            continue

        current_prices[symbol] = price
        logging.info(f"{symbol}: ${price:.2f} | RSI: {rsi:.2f}")

        if has_position(symbol):
            if rsi > RSI_SELL or should_exit(symbol, price):
                trade(symbol, "sell", price)
        elif rsi < RSI_BUY:
            trade(symbol, "buy", price)

    check_covered_calls(current_prices)
    logging.info(f"Sleeping {SLEEP_SECONDS}s...")
    time.sleep(SLEEP_SECONDS)
