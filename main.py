import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
# Make sure BASE_URL does NOT include '/v2'
BASE_URL = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

# Configuration for trading
SYMBOLS = ["AAPL", "TSLA", "NVDA"]  # Symbols you want to trade
RSI_PERIOD = 14
RSI_THRESHOLD = 30
TRADE_AMOUNT = 1000  # USD per trade
SLEEP_SECONDS = 300  # 5 minutes between cycles

# Setup Alpaca API connection
api = REST(API_KEY, API_SECRET, BASE_URL)
account = api.get_account()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logging.info("✅ Connected to Alpaca")
logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

def get_cash():
    return float(api.get_account().cash)

def get_price(symbol):
    # Get the latest trade price
    trade = api.get_latest_trade(symbol)
    return float(trade.price)

def get_rsi(symbol, period=RSI_PERIOD):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=100).df
        if bars.empty or len(bars) < period + 1:
            logging.warning(f"⚠️ Insufficient data for {symbol}")
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
            time_in_force='day',      # For extended hours, must be 'day'
            limit_price=price,
            extended_hours=True       # Enable pre-market/post-market
        )
        logging.info(f"✅ Order placed: BUY {qty} {symbol} at ${price:.2f}")
    except Exception as e:
        logging.error(f"❌ Failed to place order for {symbol}: {e}")

def run_strategy(symbols):
    logging.info("🔁 Running strategy...")
    cash = get_cash()
    logging.info(f"💰 Cash available: ${cash:.2f}")
    
    for symbol in symbols:
        logging.info(f"🔎 Checking {symbol}")
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
                logging.warning(f"⚠️ Skipping {symbol}: insufficient funds or calculated qty < 1")
        else:
            logging.info(f"⏸️ Skipping {symbol} — RSI {rsi:.2f} is above threshold")
    logging.info("✅ Strategy run complete.")

def manage_open_trades():
    logging.info("🔄 Managing open positions...")
    try:
        positions = api.list_positions()
        for pos in positions:
            symbol = pos.symbol
            qty = int(float(pos.qty))
            if qty <= 0:
                continue
            pl_pct = float(pos.unrealized_plpc)
            # Sell if profit is 6% or more, or loss is 3% or more
            try:
                if pl_pct >= 0.06:
                    api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logging.info(f"🎯 Sold {symbol} — reached take profit ({pl_pct*100:.2f}%)")
                elif pl_pct <= -0.03:
                    api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logging.info(f"🛑 Sold {symbol} — reached stop loss ({pl_pct*100:.2f}%)")
            except Exception as e:
                logging.error(f"❌ Error executing sell for {symbol}: {e}")
    except Exception as e:
        logging.error(f"❌ Trade management error: {e}")

if __name__ == "__main__":
    while True:
        try:
            run_strategy(SYMBOLS)
            manage_open_trades()
            logging.info("🕒 Sleeping for 5 minutes...")
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logging.error(f"Unhandled error: {e}")
            time.sleep(30)
