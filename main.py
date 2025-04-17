import os
import time
import logging
import yfinance as yf
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator
import pandas as pd
import requests

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === HARDCODED API CREDS ===
API_KEY = "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = "https://paper-api.alpaca.markets"
FMP_API_KEY = "eJI8bQkL1Ov2tS307tYaO0VTAaguLoNd"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === STRATEGY SETTINGS ===
RSI_BUY = 45
RSI_SELL = 60
BAR_LIMIT = 100
TRADE_PERCENTAGE = 0.10
MAX_TICKERS = 500  # expanded to more than 100

# === Get RSI using Yahoo Finance ===
def get_rsi(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if df.empty:
            logging.warning(f"⚠️ No data for {symbol}")
            return None

        close_prices = df['Close']
        rsi = RSIIndicator(close_prices).rsi().iloc[-1]
        return rsi
    except Exception as e:
        logging.error(f"❌ Error getting RSI for {symbol}: {e}")
        return None

# === AI scoring signal ===
def get_ai_signal(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v4/score?symbol={symbol}&apikey={FMP_API_KEY}"
        response = requests.get(url)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            score = data[0].get('score', 0)
            return float(score)
        else:
            return 0.0
    except Exception as e:
        logging.error(f"❌ Error fetching AI score for {symbol}: {e}")
        return 0.0

# === Get all tradable tickers from FMP ===
def scan_all_stocks():
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP_API_KEY}"
        response = requests.get(url)
        data = response.json()
        tickers = [item["symbol"] for item in data if item.get("exchangeShortName") in ["NYSE", "NASDAQ"]]
        logging.info(f"🔍 Loaded {len(tickers)} tradable tickers.")
        return tickers[:MAX_TICKERS]
    except Exception as e:
        logging.error(f"❌ Error loading stock list: {e}")
        return []

# === Get current price ===
def get_price(symbol):
    try:
        price = yf.Ticker(symbol).history(period="1d", interval="1m")['Close'].iloc[-1]
        return price
    except Exception as e:
        logging.error(f"❌ Error fetching price for {symbol}: {e}")
        return None

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

# === Smart profit/stop logic ===
def should_exit_position(symbol, current_price):
    try:
        position = api.get_position(symbol)
        avg_price = float(position.avg_entry_price)
        change_pct = (current_price - avg_price) / avg_price * 100

        logging.info(f"📊 {symbol} P/L %: {change_pct:.2f} (Avg: ${avg_price:.2f})")

        if change_pct >= 5:
            logging.info(f"🎯 Target hit for {symbol}, selling for profit.")
            return True
        elif change_pct <= -3:
            logging.info(f"🚩 Stop-loss triggered for {symbol}, exiting position.")
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"❌ Error checking exit conditions for {symbol}: {e}")
        return False

# === Main Strategy Loop ===
def run():
    SYMBOLS = scan_all_stocks()

    logging.info("🔄 Checking account and stock prices...")

    try:
        account = api.get_account()
        logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")
    except Exception as e:
        logging.error(f"❌ Account fetch error: {e}")
        return

    for symbol in SYMBOLS:
        price = get_price(symbol)
        rsi = get_rsi(symbol)
        ai_score = get_ai_signal(symbol)

        if price is None or rsi is None:
            continue

        logging.info(f"📈 {symbol} price: ${price:.2f} | RSI: {rsi:.2f} | AI Score: {ai_score:.2f}")

        if ai_score < 0.3:
            continue  # Skip low confidence

        if has_position(symbol):
            if should_exit_position(symbol, price) or rsi > RSI_SELL:
                submit_order(symbol, "sell", price)
        elif rsi < RSI_BUY:
            submit_order(symbol, "buy", price)

while True:
    run()
    logging.info("⏳ Waiting 60 seconds...")
    time.sleep(60)
