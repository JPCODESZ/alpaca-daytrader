import os
import time
import pandas as pd
import ta
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

# === Load Environment Variables ===
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

# === Connect to Alpaca ===
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

# === Configuration ===
STOCKS = ['TSLA', 'AAPL', 'NVDA']
RISK_PER_TRADE = 100
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

# === Calculate RSI ===
def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=50).df
        if bars.empty:
            print(f"⚠️ No data for {symbol}")
            return None
        close = bars['close']
        rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
        return rsi
    except Exception as e:
        print(f"❌ Error fetching RSI for {symbol}: {e}")
        return None

# === Trading Logic ===
def run_strategy():
    print("\n🚀 Running strategy...")
    for symbol in STOCKS:
        rsi = get_rsi(symbol)
        if rsi is None:
            continue
        print(f"{symbol} RSI: {rsi:.2f}")
        if rsi < 30:
            try:
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
                print(f"✅ Order placed for {qty}x {symbol} at ${price:.2f}")
                print(f"   ⛔ Stop: ${stop_loss:.2f} | 🎯 Target: ${take_profit:.2f}")
            except Exception as e:
                print(f"❌ Failed to trade {symbol}: {e}")
        else:
            print(f"⏸️ Skipping {symbol} — RSI is not oversold.")

# === Run Bot Immediately ===
print("🔁 Starting bot now...")
run_strategy()
print("✅ Bot finished. Ready for next run.")
