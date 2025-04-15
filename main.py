import os
import time
import pandas as pd
import ta
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

print("🔧 Starting trading bot...")

# Load .env variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

# Connect to Alpaca
try:
    api = REST(API_KEY, API_SECRET, BASE_URL)
    account = api.get_account()
    print("✅ Connected to Alpaca.")
    print(f"📊 Buying Power: ${float(account.buying_power):,.2f}")
    print(f"💰 Cash: ${float(account.cash):,.2f}")
    print(f"📈 Equity: ${float(account.equity):,.2f}")
except Exception as e:
    print(f"❌ Failed to connect to Alpaca: {e}")
    exit(1)

# Settings
STOCKS = ['TSLA', 'AAPL', 'NVDA']
RISK_PER_TRADE = 100
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04
RSI_THRESHOLD = 50  # TEMP for testing — change to 30 later

def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=50).df
        if bars.empty:
            print(f"⚠️ No data for {symbol}")
            return None
        close = bars['close']
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        print(f"🔎 RSI for {symbol}: {rsi:.2f}")
        return rsi
    except Exception as e:
        print(f"❌ RSI error for {symbol}: {e}")
        return None

def run_strategy():
    print("\n🚀 Running strategy...\n")
    for symbol in STOCKS:
        try:
            rsi = get_rsi(symbol)
            if rsi is None:
                continue

            print(f"{symbol} RSI: {rsi:.2f}")
            if rsi < RSI_THRESHOLD:
                try:
                    price = float(api.get_latest_trade(symbol).price)
                    qty = int(RISK_PER_TRADE / price)

                    if qty < 1:
                        print(f"⚠️ Skipping {symbol}: not enough funds for even 1 share at ${price:.2f}")
                        continue

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

                    print(f"✅ TRADE: {qty}x {symbol} @ ${price:.2f}")
                    print(f"   ⛔ Stop: ${stop_loss:.2f} | 🎯 Take-Profit: ${take_profit:.2f}")
                except Exception as e:
                    print(f"❌ Trade failed for {symbol}: {e}")
            else:
                print(f"⏸️ No trade for {symbol} — RSI {rsi:.2f} is above threshold.")
        except Exception as e:
            print(f"❌ Unexpected error for {symbol}: {e}")

    print("\n✅ Strategy run complete.")

# Run the bot once
print("🔁 Starting bot now...")
run_strategy()
print("✅ Script finished executing.\n")
