import os
import time
import requests
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

# === Config ===
RSI_THRESHOLD = 30
RISK_PER_TRADE = 300
STOP_LOSS_PCT = 0.03
TAKE_PROFIT_PCT = 0.06
MIN_PRICE = 2.00

CRYPTO_SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD"]

def get_top_losers(limit=3):
    try:
        url = f"https://financialmodelingprep.com/api/v3/losers?apikey={FMP_API_KEY}"
        res = requests.get(url)
        data = res.json()
        return [item['ticker'] for item in data[:limit]]
    except Exception as e:
        print(f"❌ Failed to fetch top losers: {e}")
        return []

def get_rsi(symbol, timeframe=TimeFrame.Minute, bars=50):
    try:
        df = api.get_bars(symbol, timeframe, limit=bars).df
        if df.empty: return None
        rsi = ta.momentum.RSIIndicator(df['close']).rsi().iloc[-1]
        return rsi
    except Exception as e:
        print(f"❌ RSI error for {symbol}: {e}")
        return None

def place_trade(symbol, price):
    qty = max(1, int(RISK_PER_TRADE / price))
    stop = round(price * (1 - STOP_LOSS_PCT), 2)
    target = round(price * (1 + TAKE_PROFIT_PCT), 2)

    api.submit_order(
        symbol=symbol,
        qty=qty,
        side='buy',
        type='market',
        time_in_force='gtc',
        order_class='bracket',
        stop_loss={'stop_price': stop},
        take_profit={'limit_price': target}
    )

    print(f"✅ BUY {qty}x {symbol} @ ${price:.2f} | ⛔ Stop: ${stop:.2f} | 🎯 Target: ${target:.2f}")

def run_strategy(symbols):
    print("\n🚀 Running strategy...\n")
    for symbol in symbols:
        try:
            rsi = get_rsi(symbol)
            if rsi is None:
                continue

            price = float(api.get_latest_trade(symbol).price)
            print(f"🔎 {symbol} RSI: {rsi:.2f} @ ${price:.2f}")

            if rsi < RSI_THRESHOLD and price > MIN_PRICE:
                place_trade(symbol, price)
            else:
                print(f"⏸️ Skipping {symbol} — RSI > {RSI_THRESHOLD}")
        except Exception as e:
            print(f"❌ Strategy error on {symbol}: {e}")
    print("\n✅ Strategy complete.\n")

def manage_open_trades():
    print("🔄 Managing open positions...")
    try:
        positions = api.list_positions()
        for p in positions:
            symbol = p.symbol
            qty = int(p.qty)
            pl_pct = float(p.unrealized_plpc)

            if pl_pct >= 0.06:
                api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                print(f"🎯 Sold {symbol} — hit take profit")

            elif pl_pct <= -0.03:
                api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc')
                print(f"🛑 Sold {symbol} — hit stop loss")
    except Exception as e:
        print(f"❌ Trade manager error: {e}")

# === Run Bot ===
if __name__ == "__main__":
    stock_symbols = get_top_losers()
    all_symbols = stock_symbols + CRYPTO_SYMBOLS
    run_strategy(all_symbols)
    manage_open_trades()
