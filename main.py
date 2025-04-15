
import os
import time
import schedule
import pandas as pd
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import ta

# Load environment variables
load_dotenv()

# Alpaca API credentials from .env
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)

# Configurations
STOCKS = ['TSLA', 'AAPL', 'NVDA']  # Add more tickers if needed
RISK_PER_TRADE = 100               # Dollars per trade
STOP_LOSS_PCT = 0.02               # 2% stop-loss
TAKE_PROFIT_PCT = 0.04             # 4% take-profit

# Get RSI indicator
def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, '15Min', limit=50).df
        if bars.empty:
            print(f"⚠️ No data for {symbol}")
            return None
        close_prices = bars['close']
        rsi = ta.momentum.RSIIndicator(close_prices).rsi().iloc[-1]
        return rsi
    except Exception as e:
        print(f"❌ Failed to get RSI for {symbol}: {e}")
        return None

# Main trading function
def run_strategy():
    print("🚀 Starting strategy run...")
    for symbol in STOCKS:
        try:
            rsi = get_rsi(symbol)
            if rsi is None:
                continue

            print(f"{symbol} RSI: {rsi:.2f}")
            if rsi < 30:  # Oversold signal
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

                print(f"✅ Placed buy order for {qty} shares of {symbol} at ${price:.2f}")
            else:
                print(f"⏸️ No trade: {symbol} RSI is not oversold.")
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")

# Run strategy once on boot
print("🔁 Running bot immediately on startup...")
run_strategy()

# Optional: repeat every X minutes (can comment out if not needed)
schedule.every(30).minutes.do(run_strategy)

while True:
    schedule.run_pending()
    time.sleep(10)
