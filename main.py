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
API_KEY = os.getenv("APCA_API_KEY_ID") or "PKT2O4O41F47DJWEBP45"
API_SECRET = os.getenv("APCA_API_SECRET_KEY") or "qzZE3AuSnfTF7dxd5spkT4ZMrHkBwLSPw5P6LSn4"
BASE_URL = os.getenv("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"

api = REST(API_KEY, API_SECRET, BASE_URL)

# === SETTINGS ===
PROFIT_TARGET = 0.5   # 50% profit target
STOP_LOSS = 0.2       # 20% stop loss
TRADE_RISK = 0.10     # 10% of account equity per trade
MAX_POSITIONS = 10
ENTRY_ORDER_TYPE = "limit"  # Options: market, limit, stop
USE_TRAILING_STOP = True
TRAILING_PERCENT = 5  # Trailing stop percent if enabled

# === LOAD US STOCK SYMBOLS ===
TICKERS = pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100")[4]['Ticker'].tolist()
TICKERS += pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]['Symbol'].tolist()
TICKERS = list(set(t.replace(".", "-") for t in TICKERS))

positions = {}

# === DETECT BREAKOUT ===
def is_breakout(df):
    recent = df['Close'].iloc[-5:]
    avg_vol = df['Volume'].mean()
    volume_spike = df['Volume'].iloc[-1] > 1.5 * avg_vol
    strong_candle = recent[-1] > recent.max() - (recent.max() - recent.min()) * 0.2
    return volume_spike and strong_candle

# === DETECT BREAKDOWN ===
def is_breakdown(df):
    recent = df['Close'].iloc[-5:]
    avg_vol = df['Volume'].mean()
    volume_spike = df['Volume'].iloc[-1] > 1.5 * avg_vol
    weak_candle = recent[-1] < recent.min() + (recent.max() - recent.min()) * 0.2
    return volume_spike and weak_candle

# === PLACE ORDER ===
def trade(symbol, price, side):
    try:
        acc = api.get_account()
        equity = float(acc.equity)
        max_trade_value = equity * TRADE_RISK
        qty = max(1, int(max_trade_value / price))

        if USE_TRAILING_STOP:
            api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type="trailing_stop",
                time_in_force="gtc",
                trail_percent=TRAILING_PERCENT
            )
        else:
            order_params = {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": ENTRY_ORDER_TYPE,
                "time_in_force": "gtc"
            }
            if ENTRY_ORDER_TYPE == "limit":
                order_params["limit_price"] = price
            elif ENTRY_ORDER_TYPE == "stop":
                order_params["stop_price"] = price

            api.submit_order(**order_params)

        entry = price
        target = price * (1 + PROFIT_TARGET) if side == "buy" else price * (1 - PROFIT_TARGET)
        stop = price * (1 - STOP_LOSS) if side == "buy" else price * (1 + STOP_LOSS)

        positions[symbol] = {
            "entry": entry,
            "target": target,
            "stop": stop,
            "qty": qty,
            "side": side
        }

        logging.info(f"{side.upper()} {symbol} @ {entry:.2f} | Target: {target:.2f} | Stop: {stop:.2f}")
    except Exception as e:
        logging.error(f"Trade error {symbol}: {e}")

# === MONITOR AND EXIT ===
def manage_positions():
    for symbol, data in list(positions.items()):
        try:
            price = yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
            hit_target = price >= data['target'] if data['side'] == "buy" else price <= data['target']
            hit_stop = price <= data['stop'] if data['side'] == "buy" else price >= data['stop']

            if hit_target or hit_stop:
                api.submit_order(
                    symbol=symbol,
                    qty=data['qty'],
                    side="sell" if data['side'] == "buy" else "buy",
                    type="market",
                    time_in_force="gtc"
                )
                reason = "TAKE PROFIT" if hit_target else "STOP LOSS"
                logging.info(f"{reason} {symbol} @ {price:.2f}")
                del positions[symbol]
        except Exception as e:
            logging.error(f"Manage error {symbol}: {e}")

# === RUN LOOP ===
def run():
    for symbol in TICKERS[:150]:
        try:
            df = yf.Ticker(symbol).history(period="5d", interval="15m")
            if df.empty or symbol in positions:
                continue
            price = df['Close'].iloc[-1]
            if len(positions) < MAX_POSITIONS:
                if is_breakout(df):
                    trade(symbol, price, "buy")
                elif is_breakdown(df):
                    trade(symbol, price, "sell")
            logging.info(f"{symbol}: {price:.2f} | Checked")
        except Exception as e:
            logging.error(f"Scan error {symbol}: {e}")

    manage_positions()

while True:
    run()
    logging.info("⏳ Sleeping 10s...")
    time.sleep(10)
