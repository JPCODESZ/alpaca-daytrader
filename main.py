import os
import time
import logging
import yfinance as yf
import pandas as pd
from alpaca_trade_api.rest import REST

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

# === API CONFIG ===
API_KEY = os.getenv("APCA_API_KEY_ID") or "PKKZSPUPBKLW7U6EY9S2"
API_SECRET = os.getenv("APCA_API_SECRET_KEY") or "u9e3ZLpN8Ov72Oh6Yca6MhBHfftJNNeKiKjXfBal"
BASE_URL = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === SETTINGS ===
PROFIT_TARGET = 0.5   # 50% profit target
STOP_LOSS = 0.2       # 20% stop loss
TRADE_RISK = 0.10     # 10% of account equity per trade
MAX_POSITIONS = 10

# === LOAD STOCKS ===
TICKERS = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]['Symbol'].tolist()
TICKERS = [t.replace(".", "-") for t in TICKERS]  # Match Yahoo format

positions = {}

# === DETECT STRONG BREAKOUT ===
def is_breakout(df):
    recent = df['Close'].iloc[-5:]
    avg_vol = df['Volume'].mean()
    volume_spike = df['Volume'].iloc[-1] > 1.5 * avg_vol
    strong_candle = recent[-1] > recent.max() - (recent.max() - recent.min()) * 0.2
    return volume_spike and strong_candle

# === MANAGE ORDERS ===
def trade(symbol, price):
    try:
        acc = api.get_account()
        equity = float(acc.equity)
        max_trade_value = equity * TRADE_RISK
        qty = max(1, int(max_trade_value / price))

        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="market",
            time_in_force="gtc"
        )

        positions[symbol] = {
            "entry": price,
            "target": price * (1 + PROFIT_TARGET),
            "stop": price * (1 - STOP_LOSS),
            "qty": qty
        }

        logging.info(f"BUY {symbol} @ {price:.2f} | Target: {price * (1 + PROFIT_TARGET):.2f} | Stop: {price * (1 - STOP_LOSS):.2f}")
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === MONITOR AND CLOSE ===
def manage_positions():
    for symbol, data in list(positions.items()):
        try:
            price = yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
            if price >= data['target']:
                api.submit_order(symbol=symbol, qty=data['qty'], side="sell", type="market", time_in_force="gtc")
                logging.info(f"TAKE PROFIT {symbol} @ {price:.2f}")
                del positions[symbol]
            elif price <= data['stop']:
                api.submit_order(symbol=symbol, qty=data['qty'], side="sell", type="market", time_in_force="gtc")
                logging.info(f"STOP LOSS {symbol} @ {price:.2f}")
                del positions[symbol]
        except Exception as e:
            logging.error(f"Manage error {symbol}: {e}")

# === RUN LOOP ===
def run():
    for symbol in TICKERS[:100]:  # limit cycle for speed
        try:
            df = yf.Ticker(symbol).history(period="5d", interval="15m")
            if df.empty or symbol in positions:
                continue
            price = df['Close'].iloc[-1]
            if is_breakout(df) and len(positions) < MAX_POSITIONS:
                trade(symbol, price)
            logging.info(f"{symbol}: {price:.2f} | Checked")
        except Exception as e:
            logging.error(f"Scan error {symbol}: {e}")
    manage_positions()

while True:
    run()
    logging.info("⏳ Sleeping 10s...")
    time.sleep(10)
