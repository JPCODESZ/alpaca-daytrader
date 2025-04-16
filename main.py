import time
import os
import logging
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION === #
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

RSI_THRESHOLD = 30
TRADE_AMOUNT = 1000  # dollars per trade
SYMBOLS = ["AAPL", "TSLA", "NVDA"]  # add more if you'd like
SLEEP_INTERVAL = 300  # in seconds

# === INIT API === #
api = REST(API_KEY, API_SECRET, BASE_URL)

def get_cash():
    account = api.get_account()
    return float(account.cash)

def get_price(symbol):
    quote = api.get_latest_trade(symbol)
    return float(quote.price)

def get_rsi(symbol, period=14):
    bars = api.get_bars(symbol, TimeFrame.Minute, limit=100).df
    if bars.empty or len(bars) < period + 1:
        return None

    close = bars['close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def place_order(symbol, qty, price):
    try:
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            type='limit',
            time_in_force='day',
            limit_price=price,
            extended_hours=True
        )
        logging.info(f"✅ Order placed: BUY {qty} {symbol} at ${price}")
    except Exception as e:
        logging.error(f"❌ Failed to place order for {symbol}: {e}")

def run_strategy():
    logging.info("🔁 Starting strategy loop...")
    cash = get_cash()
    logging.info(f"💰 Cash available: ${cash:.2f}")

    for symbol in SYMBOLS:
        logging.info(f"🔎 Checking {symbol}")
        rsi = get_rsi(symbol)
        if rsi is None:
            logging.warning(f"⚠️ Could not calculate RSI for {symbol}")
            continue

        logging.info(f"{symbol} RSI: {rsi:.2f}")
        if rsi < RSI_THRESHOLD:
            price = get_price(symbol)
            qty = int(TRADE_AMOUNT // price)
            if qty >= 1 and cash >= price * qty:
                place_order(symbol, qty, price)
            else:
                logging.warning(f"⚠️ Not enough cash or qty too small for {symbol}")
        else:
            logging.info(f"⏸️ Skipping {symbol} — RSI not low enough")

# === LOOP === #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    while True:
        try:
            run_strategy()
            time.sleep(SLEEP_INTERVAL)
        except Exception as e:
            logging.error(f"Unhandled error: {e}")
            time.sleep(30)
