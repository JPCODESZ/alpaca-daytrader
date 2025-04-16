import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID", "PKHAJ5KK14MHZSVTMD05")
API_SECRET = os.getenv("APCA_API_SECRET_KEY", "444XYfuXVes0ta4LDFBENrkdi44HCeJOobfIOn2J")
BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

# Risk & config
SYMBOLS = ["AAPL", "TSLA", "NVDA", "KZR"]
RSI_PERIOD = 14
RSI_THRESHOLD = 30
TRADE_AMOUNT = 3000  # Higher risk per trade
SLEEP_SECONDS = 60   # Check every 1 minute

# Profit/Loss thresholds
TAKE_PROFIT = 0.10
STOP_LOSS = -0.05

# Setup API & logging
api = REST(API_KEY, API_SECRET, BASE_URL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def get_cash():
    return float(api.get_account().cash)

def get_price(symbol):
    return float(api.get_latest_trade(symbol).price)

def get_rsi(symbol, period=RSI_PERIOD):
    try:
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
    except Exception as e:
        logging.warning(f"RSI error for {symbol}: {e}")
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
        logging.info(f"✅ Placed BUY: {symbol} x {qty} @ ${price:.2f}")
    except Exception as e:
        logging.error(f"❌ Order failed for {symbol}: {e}")

def run_strategy(symbols):
    logging.info("🚀 Running strategy...")
    cash = get_cash()
    logging.info(f"💵 Cash: ${cash:.2f}")

    for symbol in symbols:
        logging.info(f"🔎 RSI check for {symbol}")
        rsi = get_rsi(symbol)
        if rsi is None:
            continue
        logging.info(f"{symbol} RSI: {rsi:.2f}")

        if rsi < RSI_THRESHOLD:
            price = get_price(symbol)
            qty = int(TRADE_AMOUNT // price)
            if qty >= 1 and cash >= qty * price:
                place_order(symbol, qty, price)
            else:
                logging.warning(f"⚠️ Not enough funds or quantity too low for {symbol}")
        else:
            logging.info(f"⏸️ Skipping {symbol}: RSI > {RSI_THRESHOLD}")

def manage_open_trades():
    logging.info("📊 Managing positions...")
    try:
        positions = api.list_positions()
        for pos in positions:
            symbol = pos.symbol
            try:
                live_qty = int(float(api.get_position(symbol).qty))
                if live_qty < 1:
                    logging.warning(f"⚠️ {symbol}: qty is 0, skipping")
                    continue

                pl_pct = float(pos.unrealized_plpc)
                if pl_pct >= TAKE_PROFIT or pl_pct <= STOP_LOSS:
                    api.submit_order(
                        symbol=symbol,
                        qty=live_qty,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logging.info(f"💰 Sold {symbol} | P/L: {pl_pct*100:.2f}%")
            except Exception as e:
                logging.error(f"❌ Sell error for {symbol}: {e}")
    except Exception as e:
        logging.error(f"❌ Position check failed: {e}")

if __name__ == "__main__":
    while True:
        try:
            run_strategy(SYMBOLS)
            manage_open_trades()
            logging.info(f"🕐 Sleeping {SLEEP_SECONDS} seconds...\n")
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logging.error(f"💥 Main error: {e}")
            time.sleep(30)
