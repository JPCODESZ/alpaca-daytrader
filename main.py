import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load .env if running locally
load_dotenv()

# API Credentials (fallbacks if .env isn't set)
API_KEY = os.getenv("APCA_API_KEY_ID", "PKHAJ5KK14MHZSVTMD05")
API_SECRET = os.getenv("APCA_API_SECRET_KEY", "444XYfuXVes0ta4LDFBENrkdi44HCeJOobfIOn2J")
BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

# Trading Configuration
SYMBOLS = ["AAPL", "TSLA", "NVDA"]
RSI_PERIOD = 14
RSI_THRESHOLD = 30
TRADE_AMOUNT = 1000  # $ per trade
SLEEP_SECONDS = 300  # 5 minutes

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)
account = api.get_account()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logging.info("✅ Connected to Alpaca")
logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

def get_cash():
    return float(api.get_account().cash)

def get_price(symbol):
    trade = api.get_latest_trade(symbol)
    return float(trade.price)

def get_rsi(symbol, period=RSI_PERIOD):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=100).df
        if bars.empty or len(bars) < period + 1:
            logging.warning(f"⚠️ Not enough data for {symbol}")
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
        logging.error(f"❌ RSI error for {symbol}: {e}")
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
        logging.info(f"✅ Placed BUY order: {qty} {symbol} @ ${price:.2f}")
    except Exception as e:
        logging.error(f"❌ Order failed for {symbol}: {e}")

def run_strategy(symbols):
    logging.info("🚀 Running strategy...")
    cash = get_cash()
    logging.info(f"💵 Cash: ${cash:.2f}")

    for symbol in symbols:
        logging.info(f"🔍 Checking {symbol}")
        rsi = get_rsi(symbol)
        if rsi is None:
            continue

        logging.info(f"{symbol} RSI: {rsi:.2f}")
        if rsi < RSI_THRESHOLD:
            price = get_price(symbol)
            qty = int(TRADE_AMOUNT // price)
            if qty >= 1 and cash >= price * qty:
                place_order(symbol, qty, price)
            else:
                logging.warning(f"⚠️ Not enough funds or qty too low for {symbol}")
        else:
            logging.info(f"⏸️ Skipping {symbol}, RSI {rsi:.2f} too high")

    logging.info("✅ Strategy check complete.")

def manage_open_trades():
    logging.info("📊 Managing open positions...")
    try:
        positions = api.list_positions()
        for pos in positions:
            symbol = pos.symbol
            try:
                live_qty = int(float(api.get_position(symbol).qty))
                if live_qty < 1:
                    logging.warning(f"⚠️ Skipping {symbol}: 0 qty")
                    continue

                pl_pct = float(pos.unrealized_plpc)
                if pl_pct >= 0.06:
                    api.submit_order(symbol=symbol, qty=live_qty, side='sell', type='market', time_in_force='day')
                    logging.info(f"🎯 Sold {symbol}: +{pl_pct*100:.2f}% profit")
                elif pl_pct <= -0.03:
                    api.submit_order(symbol=symbol, qty=live_qty, side='sell', type='market', time_in_force='day')
                    logging.info(f"🛑 Sold {symbol}: -{pl_pct*100:.2f}% loss")
            except Exception as e:
                logging.error(f"❌ Sell error for {symbol}: {e}")
    except Exception as e:
        logging.error(f"❌ Failed to manage positions: {e}")

if __name__ == "__main__":
    while True:
        try:
            run_strategy(SYMBOLS)
            manage_open_trades()
            logging.info(f"⏳ Sleeping {SLEEP_SECONDS // 60} mins...\n")
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logging.error(f"💥 Main loop error: {e}")
            time.sleep(30)
