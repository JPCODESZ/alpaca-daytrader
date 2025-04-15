import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import ta
import pandas as pd

print("🔧 Bot starting...")

# Load env vars
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

print("✅ ENV Loaded")
print(f"Key: {API_KEY[:4]}... | URL: {BASE_URL}")

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)

# Settings
STOCKS = ['TSLA']
RISK_PER_TRADE = 100
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, '15Min', limit=50).df
        if bars.empty:
            print(f"⚠️ No data for {symbol}")
            return None
        close = bars['close']
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        return rsi
    except Exception as e:
        print(f"❌ Failed to fetch RSI: {e}")
        return None

def run_strategy():
    print("🚀 Running strategy...")
    for symbol in STOCKS:
        rsi = get_rsi(symbol)
        if rsi is None:
            continue
        print(f"{symbol} RSI: {rsi:.2f}")
        if rsi < 30:
            price = api.get_last_trade(symbol).price
            qty = int(RISK_PER_TRADE / price)
            stop_loss = round(price * (1 - STOP_LOSS_PCT), 2)
            take_profit = round(price * (1 + TAKE_PROFIT_PCT), 2)

            api.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': stop_loss},
                take_profit={'limit_price': take_profit}
            )
            print(f"✅ Order placed: {qty}x {symbol} @ ${price:.2f}")
        else:
            print(f"⏸️ RSI not low enough: {rsi:.2f}")

# Run once
run_strategy()
print("✅ Bot run complete.")
