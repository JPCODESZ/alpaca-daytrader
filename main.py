import os
import time
import logging
import yfinance as yf
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator
import pandas as pd

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === HARDCODED API CREDS ===
API_KEY = "PKJA5OXADZI7EPNS5UER"
API_SECRET = "a7WRbJuiJkNbe7fYlIf7n5UnlslSHZlruZTonQu8"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === STRATEGY SETTINGS ===
RSI_BUY = 45
RSI_SELL = 60
SYMBOLS = ["AAPL", "TSLA", "NVDA", "TQQQ", "SOXL"]
BAR_LIMIT = 100
TRADE_PERCENTAGE = 0.10  # 10% of buying power per trade

# === Get latest price and RSI using Yahoo Finance ===
def get_price_and_rsi(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if df.empty:
            logging.warning(f"⚠️ No data for {symbol}")
            return None, None

        close_prices = df['Close']
        rsi = RSIIndicator(close_prices).rsi().iloc[-1]
        price = close_prices.iloc[-1]
        return price, rsi
    except Exception as e:
        logging.error(f"❌ Error getting RSI for {symbol}: {e}")
        return None, None

# === Submit Order ===
def submit_order(symbol, side, price):
    try:
        account = api.get_account()
        buying_power = float(account.buying_power)
        trade_amount = buying_power * TRADE_PERCENTAGE
        qty = max(1, int(trade_amount / price))

        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc"
        )
        logging.info(f"✅ {side.upper()} order submitted for {symbol} with {qty} shares (~${qty * price:.2f})")
    except Exception as e:
        logging.error(f"❌ Trade error for {symbol}: {e}")

# === Check if position exists ===
def has_position(symbol):
    try:
        position = api.get_position(symbol)
        return int(position.qty) > 0
    except:
        return False

# === Main Strategy Loop ===
def run():
    logging.info("🔄 Checking account and stock prices...")

    try:
        account = api.get_account()
        logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")
    except Exception as e:
        logging.error(f"❌ Account fetch error: {e}")
        return

    for symbol in SYMBOLS:
        price, rsi = get_price_and_rsi(symbol)
        if price is None or rsi is None:
            continue

        logging.info(f"📈 {symbol} price: ${price:.2f} | RSI: {rsi:.2f}")

        if rsi < RSI_BUY:
            submit_order(symbol, "buy", price)
        elif rsi > RSI_SELL and has_position(symbol):
            submit_order(symbol, "sell", price)

while True:
    run()
    logging.info("⏳ Waiting 60 seconds...")
    time.sleep(60)
