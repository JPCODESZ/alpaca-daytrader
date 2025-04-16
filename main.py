import os
import time
import logging
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.rest import APIError

load_dotenv()  # Only needed for local dev. Safe to keep on Render.

# Load environment variables
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# Debug print
print("🔎 DEBUG ENV VARS")
print("API_KEY:", API_KEY)
print("API_SECRET:", API_SECRET)
print("BASE_URL:", BASE_URL)

# Validate credentials
if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials. Check your .env or Render environment variables.")

# Init Alpaca API
api = REST(API_KEY, API_SECRET, BASE_URL)

def get_rsi(symbol, timeframe=TimeFrame.Minute, bars=14):
    try:
        barset = api.get_bars(symbol, timeframe, limit=bars).df
        close = barset['close']
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception as e:
        print(f"❌ RSI error for {symbol}: {e}")
        return None

def run_strategy():
    symbols = ["TSLA", "AAPL", "NVDA"]
    for symbol in symbols:
        try:
            price = float(api.get_last_trade(symbol).price)
            account = api.get_account()
            cash = float(account.cash)
            qty = int(cash // price)

            rsi = get_rsi(symbol)
            print(f"{symbol} RSI: {rsi}")

            if rsi is not None and rsi < 30 and qty > 0:
                print(f"📈 Buying {qty} shares of {symbol} at ${price}")
                api.submit_order(symbol=symbol, qty=qty, side="buy", type="market", time_in_force="gtc")
            else:
                print(f"⏸️ Skipping {symbol}")
        except APIError as e:
            print(f"❌ Trade error for {symbol}: {e}")
        except Exception as e:
            print(f"❌ Unknown error for {symbol}: {e}")

# Loop forever, every 60s
while True:
    print("🚀 Running strategy loop...")
    run_strategy()
    time.sleep(60)
