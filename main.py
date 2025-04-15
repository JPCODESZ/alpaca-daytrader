import os
import time
import schedule
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
import ta
import pandas as pd

# Load environment variables
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

api = REST(API_KEY, API_SECRET, BASE_URL)

# Stock settings
STOCKS = ['TSLA', 'AAPL', 'NVDA']
RISK_PER_TRADE = 100  # dollars per trade
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

def get_rsi(symbol):
    barset = api.get_bars(symbol, '15Min', limit=50).df
    if barset.empty:
        return None
    close = barset['close']
    rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]
    return rsi

def run_strategy():
    for stock in STOCKS:
        try:
            rsi = get_rsi(stock)
            if rsi is None:
                continue
            print(f"{stock} RSI: {rsi:.2f}")
            if rsi < 30:  # Oversold condition
                price = api.get_last_trade(stock).price
                qty = int(RISK_PER_TRADE / price)
                stop_loss = round(price * (1 - STOP_LOSS_PCT), 2)
                take_profit = round(price * (1 + TAKE_PROFIT_PCT), 2)

                api.submit_order(
                    symbol=stock,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='gtc',
                    order_class='bracket',
                    stop_loss={'stop_price': stop_loss},
                    take_profit={'limit_price': take_profit}
                )
                print(f"✅ Bought {qty} shares of {stock} at ${price}")
        except Exception as e:
            print(f"Error trading {stock}: {e}")

schedule.every().day.at("09:35").do(run_strategy)

print("🤖 Bot is running... waiting for 09:35 AM EST")

while True:
    schedule.run_pending()
    time.sleep(10)
