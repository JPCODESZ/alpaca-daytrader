import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np

# === CONFIG === #
API_KEY = "PKHAJ5KK14MHZSVTMD05"
API_SECRET = "444XYfuXVes0ta4LDFBENrkdi44HCeJOobfIOn2J"
BASE_URL = "https://paper-api.alpaca.markets/v2"  # Corrected endpoint

SYMBOLS = ["AAPL", "TSLA", "NVDA"]  # Add or remove symbols here
RSI_PERIOD = 14
RSI_THRESHOLD = 30
TRADE_AMOUNT = 1000  # USD per trade
SLEEP_SECONDS = 300  # Time between loops

# === SETUP === #
api = REST(API_KEY, API_SECRET, BASE_URL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def get_cash():
    return float(api.get_account().cash)

def get_price(symbol):
    trade = api.get_latest_trade(symbol)
    return float(trade.price)

def get_rsi(symbol, period=RSI_PERIOD):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=100).df
        close = bars['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception as e:
        logging.warning(f"⚠️ RSI error for {symbol}: {e}")
        return None

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
        logging.info(f"✅ Placed order: BUY {qty} {symbol} at ${price}")
    except Exception as e:
        logging.error(f"❌ Failed order for {symbol}: {e}")

def run_bot():
    logging.info("🔁 Running strategy loop...")
    cash = get_cash()
    logging.info(f"💰 Cash: ${cash:.2f}")

    for symbol in SYMBOLS:
        logging.info(f"🔎 Checking {symbol}")
        rsi = get_rsi(symbol)
        if rsi is None:
            continue

        logging.info(f"📉 {symbol} RSI: {rsi:.2f}")
        if rsi < RSI_THRESHOLD:
            price = get_price(symbol)
            qty = int(TRADE_AMOUNT // price)
            if qty >= 1 and cash >= price * qty:
                place_order(symbol, qty, price)
            else:
                logging.info(f"⚠️ Skipping {symbol} — insufficient funds or qty too low")
        else:
            logging.info(f"⏸️ Skipping {symbol} — RSI > {RSI_THRESHOLD}")

if __name__ == "__main__":
    while True:
        try:
            run_bot()
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logging.error(f"Unhandled error: {e}")
            time.sleep(30)
