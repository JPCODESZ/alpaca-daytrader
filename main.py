import os
import time
import requests
import pandas as pd
import ta
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame

# Load env vars
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# Alpaca connection
api = REST(API_KEY, API_SECRET, BASE_URL)
account = api.get_account()
print("✅ Connected to Alpaca")
print(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

# Constants
RSI_THRESHOLD = 30
RISK_PER_TRADE = 300
STOP_LOSS_PCT = 0.03
TAKE_PROFIT_PCT = 0.06
MIN_PRICE = 2.00

def get_top_losers(limit=5):
    try:
        url = f"https://financialmodelingprep.com/api/v3/losers?apikey={FMP_API_KEY}"
        res = requests.get(url)
        data = res.json()
        symbols = [item['ticker'] for item in data[:limit]]
        print(f"📉 Top losers: {symbols}")
        return symbols
    except Exception as e:
        print(f"❌ Error fetching losers: {e}")
        return []

def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, TimeFrame.Minute, limit=50).df
        if bars.empty:
            return None
        rsi = ta.momentum.RSIIndicator(bars['close']).rsi().iloc[-1]
        return rsi
    except Exception as e:
        print(f"❌ RSI error for {symbol}: {e}")
        return None

def run_strategy(symbols):
    print("\n🚀 Running strategy...\n")
    for symbol in symbols:
        try:
            rsi = get_rsi(symbol)
            if rsi is None:
                continue

            price = float(api.get_latest_trade(symbol).price)
            print(f"{symbol} RSI: {rsi:.2f}, Price: ${price:.2f}")

            if rsi < RSI_THRESHOLD and price > MIN_PRICE:
                qty = max(1, int(RISK_PER_TRADE / price))
                stop_price = round(price * (1 - STOP_LOSS_PCT), 2)
                take_profit = round(price * (1 + TAKE_PROFIT_PCT), 2)

                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='gtc',
                    order_class='bracket',
                    stop_loss={'stop_price': stop_price},
                    take_profit={'limit_price': take_profit}
                )
                print(f"✅ BUY {qty}x {symbol} @ ${price:.2f} | ⛔ Stop: ${stop_price:.2f} | 🎯 Target: ${take_profit:.2f}")
            else:
                print(f"⏸️ Skipping {symbol} — Conditions not met.")
        except Exception as e:
            print(f"❌ Error with {symbol}: {e}")
    print("\n✅ Strategy run complete.\n")

def manage_open_trades():
    print("🔄 Managing open trades...")
    try:
        positions = api.list_positions()
        for p in positions:
            symbol = p.symbol
            qty = int(p.qty)
            pl_pct = float(p.unrealized_plpc)

            if pl_pct >= 0.06:
                api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                print(f"🎯 Took profit on {symbol} (+6%)")

            elif pl_pct <= -0.03:
                api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                print(f"🛑 Stopped loss on {symbol} (-3%)")
    except Exception as e:
        print(f"❌ Trade management error: {e}")

# MAIN
if __name__ == "__main__":
    losers = get_top_losers(limit=5)
    run_strategy(losers)
    manage_open_trades()
