import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.rest import TimeFrameUnit
import pandas as pd
from ta.momentum import RSIIndicator

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load API credentials from environment
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials. Check your .env or environment variables.")

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)

# Settings
symbols = ["AAPL", "TSLA", "NVDA"]
position_size = 1000  # dollars per trade
rsi_buy_threshold = 30
rsi_sell_threshold = 70

# Strategy function
def run_strategy():
    logging.info("🔄 Checking account and stock prices...")
    account = api.get_account()
    logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

    for symbol in symbols:
        try:
            bars = api.get_bars(symbol, TimeFrame(15, TimeFrameUnit.Minute), limit=50).df
            if bars.empty:
                logging.warning(f"⚠️ No bar data for {symbol}")
                continue

            rsi = RSIIndicator(bars['close']).rsi()
            latest_rsi = rsi.iloc[-1]
            current_price = bars['close'].iloc[-1]

            logging.info(f"📈 {symbol} price: ${current_price:.2f} | RSI: {latest_rsi:.2f}")

            position_qty = 0
            try:
                position = api.get_position(symbol)
                position_qty = float(position.qty)
            except:
                pass  # No position

            if latest_rsi < rsi_buy_threshold and position_qty == 0:
                qty_to_buy = int(position_size / current_price)
                api.submit_order(symbol=symbol, qty=qty_to_buy, side='buy', type='market', time_in_force='gtc')
                logging.info(f"✅ BUY {symbol} | Qty: {qty_to_buy} | Price: ${current_price:.2f}")

            elif latest_rsi > rsi_sell_threshold and position_qty > 0:
                api.submit_order(symbol=symbol, qty=position_qty, side='sell', type='market', time_in_force='gtc')
                logging.info(f"🚨 SELL {symbol} | Qty: {position_qty} | Price: ${current_price:.2f}")

        except Exception as e:
            logging.error(f"❌ Error handling {symbol}: {e}")

# Run loop
while True:
    try:
        run_strategy()
    except Exception as e:
        logging.error(f"🚫 Strategy error: {e}")
    logging.info("⏳ Waiting 60 seconds...")
    time.sleep(60)
