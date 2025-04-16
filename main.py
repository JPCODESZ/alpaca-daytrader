import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
from ta.momentum import RSIIndicator
import pandas as pd

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === LOAD ENV VARS ===
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials. Check environment variables.")

api = REST(API_KEY, API_SECRET, BASE_URL)

# === STRATEGY SETTINGS ===
RSI_BUY = 45
RSI_SELL = 60
SYMBOLS = ["AAPL", "TSLA", "NVDA", "TQQQ", "SOXL"]
TIMEFRAME = TimeFrame.Minute  # 1-minute bars
BAR_LIMIT = 100  # for RSI calc
TRADE_AMOUNT = 1  # shares per trade

def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, TIMEFRAME, limit=BAR_LIMIT).df
        if bars.empty:
            logging.warning(f"⚠️ No data for {symbol}")
            return None, None

        close_prices = bars['close']
        rsi = RSIIndicator(close_prices).rsi().iloc[-1]
        latest_price = close_prices.iloc[-1]
        return latest_price, rsi
    except Exception as e:
        logging.error(f"❌ Error fetching RSI for {symbol}: {e}")
        return None, None

def submit_order(symbol, side):
    try:
        api.submit_order(
            symbol=symbol,
            qty=TRADE_AMOUNT,
            side=side,
            type="market",
            time_in_force="gtc"
        )
        logging.info(f"✅ {side.upper()} order submitted for {symbol}")
    except Exception as e:
        logging.error(f"❌ Trade error for {symbol}: {e}")

def run():
    logging.info("🔄 Checking account and stock prices...")

    try:
        account = api.get_account()
        logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")
    except Exception as e:
        logging.error(f"❌ Account fetch error: {e}")
        return

    for symbol in SYMBOLS:
        price, rsi = get_rsi(symbol)
        if price is None or rsi is None:
            continue

        logging.info(f"📈 {symbol} price: ${price:.2f} | RSI: {rsi:.2f}")

        if rsi < RSI_BUY:
            submit_order(symbol, "buy")
        elif rsi > RSI_SELL:
            submit_order(symbol, "sell")

while True:
    run()
    logging.info("⏳ Waiting 60 seconds...")
    time.sleep(60)
