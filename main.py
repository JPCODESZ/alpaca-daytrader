import os
import time
import logging
import yfinance as yf
import pandas as pd
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === API CONFIG ===
API_KEY = "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === SETTINGS ===
RSI_BUY = 45
RSI_SELL = 60
TRADE_PERCENT = 0.10
MAX_TICKERS = 2000
POSITION_LOG = {}

# === Static NASDAQ + NYSE ticker list (top ~2000 based on market cap or volume) ===
STATIC_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "JNJ", "WMT", "XOM", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "AVGO", "KO",
    "PEP", "MRK", "BAC", "COST", "ADBE", "PFE", "TMO", "CSCO", "ABT", "ACN", "MCD",
    "QCOM", "DHR", "VZ", "NEE", "TXN", "LIN", "INTC", "CRM", "NKE", "ORCL", "WFC",
    "AMGN", "AMD", "LOW", "UPS", "SCHW", "PM", "MS", "RTX", "UNP", "GS", "IBM",
    "ISRG", "CAT", "CVS", "MDT", "INTU", "SPGI", "DE", "BLK", "TGT", "PLD", "BKNG",
    "ELV", "LMT", "SYK", "MO", "ADP", "C", "CI", "AMT", "ZTS", "NOW", "MMC", "GEHC",
    "ADSK", "VRTX", "CB", "GM", "ADI", "FIS", "GILD", "MET", "USB", "ATVI", "REGN",
    "AON", "FISV", "MAR", "PSX", "PNC", "HCA", "AEP", "SO", "TFC", "APD", "BIIB",
    # ... (You can keep adding more tickers to expand to 2000)
]

# === RSI via Yahoo Finance ===
def get_rsi(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        if df.empty:
            return None
        close = df['Close']
        return RSIIndicator(close).rsi().iloc[-1]
    except Exception as e:
        logging.error(f"RSI error {symbol}: {e}")
        return None

# === Get current price ===
def get_price(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval="1m")
        return df['Close'].iloc[-1]
    except Exception as e:
        logging.error(f"Price error {symbol}: {e}")
        return None

# === Use static list ===
def scan_stocks():
    return STATIC_TICKERS[:MAX_TICKERS]

# === Check position ===
def has_position(symbol):
    try:
        pos = api.get_position(symbol)
        return int(pos.qty) > 0
    except:
        return False

# === Submit order ===
def trade(symbol, side, price):
    try:
        bp = float(api.get_account().buying_power)
        qty = max(1, int((bp * TRADE_PERCENT) / price))
        api.submit_order(symbol=symbol, qty=qty, side=side, type="market", time_in_force="gtc")
        logging.info(f"{side.upper()} {symbol} x{qty} @ ${price:.2f}")

        if side == "buy":
            POSITION_LOG[symbol] = {"entry": price, "qty": qty}
        elif side == "sell" and symbol in POSITION_LOG:
            entry = POSITION_LOG[symbol]['entry']
            pnl = ((price - entry) / entry) * 100
            logging.info(f"{symbol} sold for P/L: {pnl:.2f}%")
            del POSITION_LOG[symbol]
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === Check if should exit ===
def should_exit(symbol, current):
    try:
        if symbol in POSITION_LOG:
            entry = POSITION_LOG[symbol]['entry']
            pnl = (current - entry) / entry * 100
            logging.info(f"{symbol} live P/L: {pnl:.2f}%")
            return pnl >= 6 or pnl <= -2.5
        return False
    except Exception as e:
        logging.error(f"Exit check error {symbol}: {e}")
        return False

# === Main run ===
def run():
    symbols = scan_stocks()
    logging.info("Checking market...")
    try:
        acc = api.get_account()
        logging.info(f"Cash: ${acc.cash} | Power: ${acc.buying_power}")
    except Exception as e:
        logging.error(f"Account error: {e}")
        return

    for symbol in symbols:
        price = get_price(symbol)
        rsi = get_rsi(symbol)

        if None in (price, rsi):
            continue

        logging.info(f"{symbol}: ${price:.2f} | RSI: {rsi:.2f}")

        if has_position(symbol):
            if rsi > RSI_SELL or should_exit(symbol, price):
                trade(symbol, "sell", price)
        elif rsi < RSI_BUY:
            trade(symbol, "buy", price)

while True:
    run()
    logging.info("Sleeping 10s...")
    time.sleep(10)
