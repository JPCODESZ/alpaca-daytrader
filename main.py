import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
from ta.momentum import RSIIndicator
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials!")

# Initialize API
api = REST(API_KEY, API_SECRET, BASE_URL)

# Strategy thresholds (more aggressive)
RSI_BUY = 45
RSI_SELL = 60

# Add volatile tickers
symbols = ["AAPL", "TSLA", "NVDA", "TQQQ", "SOXL", "RIOT", "MARA"]

# Fetch RSI
def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=100).df
        if bars.empty:
            return None
        close = bars['close']
        rsi = RSIIndicator(close).rsi().iloc[-1]
        return round(rsi, 2)
    except Exception as e:
        logging.error(f"❌ Error calculating RSI for {symbol}: {e}")
        return None

# Fetch current price
def get_price(symbol):
    try:
        quote = api.get_latest_trade(symbol)
        return quote.price
    except Exception as e:
        logging.error(f"❌ Error fetching price for {symbol}: {e}")
        return None

# Main trading strategy
def run_strategy():
    logging.info("🔄 Checking account and stock prices...")
    try:
        account = api.get_account()
        cash = float(account.cash)
        buying_power = float(account.buying_power)
        logging.info(f"💰 Cash: ${cash} | Buying Power: ${buying_power}")
    except Exception as e:
        logging.error(f"❌ Error getting account: {e}")
        return

    for symbol in symbols:
        price = get_price(symbol)
        rsi = get_rsi(symbol)
        if price is None or rsi is None:
            continue

        logging.info(f"📈 {symbol} price: ${price} | RSI: {rsi}")
        try:
            # More aggressive: trade even at tighter RSI margins
            if rsi < RSI_BUY:
                qty = int((buying_power * 0.05) / price)  # 5% of buying power
                if qty > 0:
                    api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc')
                    logging.info(f"🟢 BUY {qty} shares of {symbol} at ${price}")
            elif rsi > RSI_SELL:
                positions = api.list_positions()
                for p in positions:
                    if p.symbol == symbol:
                        api.submit_order(symbol=symbol, qty=int(p.qty), side='sell', type='market', time_in_force='gtc')
                        logging.info(f"🔴 SELL {p.qty} shares of {symbol} at ${price}")
        except Exception as e:
            logging.error(f"❌ Trade error for {symbol}: {e}")

# Run the strategy loop
while True:
    run_strategy()
    logging.info("⏳ Waiting 60 seconds...")
    time.sleep(60)
