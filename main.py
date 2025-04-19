import os
import time
import logging
import yfinance as yf
import pandas as pd
from alpaca_trade_api.rest import REST
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

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
RSI_BUY = 40
RSI_SELL = 60
TRADE_PERCENT = 0.10
MAX_TICKERS = 3000
POSITION_LOG = {}

# === RSI & ATR Fetch ===
def get_indicators(symbol):
    try:
        df = yf.Ticker(symbol).history(period="2d", interval="1m")
        if df.empty:
            return None, None, None, None

        df.dropna(inplace=True)
        close = df['Close']
        high = df['High']
        low = df['Low']

        rsi = RSIIndicator(close).rsi().iloc[-1]
        atr = AverageTrueRange(high, low, close).average_true_range().iloc[-1]
        current_price = close.iloc[-1]
        prev_close = close.iloc[-2]

        return rsi, atr, current_price, prev_close
    except Exception as e:
        logging.error(f"Indicator error {symbol}: {e}")
        return None, None, None, None

# === SMA Check ===
def is_above_sma200(symbol):
    try:
        df = yf.Ticker(symbol).history(period="200d")
        sma = df['Close'].rolling(200).mean().iloc[-1]
        return df['Close'].iloc[-1] > sma
    except:
        return False

# === Get stock list ===
def scan_stocks():
    try:
        tickers = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        return tickers['Symbol'].tolist()[:MAX_TICKERS]
    except Exception as e:
        logging.error(f"Scan error: {e}")
        return []

# === Position Check ===
def has_position(symbol):
    try:
        pos = api.get_position(symbol)
        return int(pos.qty) > 0
    except:
        return False

# === Submit Order ===
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

# === Exit Logic ===
def should_exit(symbol, price, atr):
    try:
        if symbol in POSITION_LOG:
            entry = POSITION_LOG[symbol]['entry']
            pnl = (price - entry) / entry * 100
            trail_stop = price < entry - atr
            locked_profit = pnl > 10 and (price < entry * 0.90)
            logging.info(f"{symbol} P/L: {pnl:.2f}%")
            return pnl >= 50 or pnl <= -5 or trail_stop or locked_profit
        return False
    except Exception as e:
        logging.error(f"Exit check error {symbol}: {e}")
        return False

# === Main Loop ===
def run():
    symbols = scan_stocks()
    logging.info("🔄 Running market check...")
    try:
        acc = api.get_account()
        logging.info(f"💰 Cash: ${acc.cash} | Buying Power: ${acc.buying_power}")
    except Exception as e:
        logging.error(f"Account error: {e}")
        return

    for symbol in symbols:
        if not is_above_sma200(symbol):
            continue

        rsi, atr, price, prev_close = get_indicators(symbol)
        if None in (rsi, atr, price, prev_close):
            continue

        logging.info(f"{symbol}: ${price:.2f} | RSI: {rsi:.2f} | ATR: {atr:.2f}")

        if has_position(symbol):
            if rsi > RSI_SELL or should_exit(symbol, price, atr):
                trade(symbol, "sell", price)
        elif rsi < RSI_BUY:
            trade(symbol, "buy", price)

while True:
    run()
    logging.info("⏳ Sleeping 10s...")
    time.sleep(10)
