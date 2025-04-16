import os
import time
import logging
from alpaca_trade_api import REST
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# Initialize Alpaca API
api = REST(API_KEY, API_SECRET, BASE_URL)

# Strategy configuration
WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "META"]
RSI_PERIOD = 14
RSI_BUY_THRESHOLD = 30
TAKE_PROFIT = 0.03  # 3% gain
STOP_LOSS = -0.02   # 2% loss
CHECK_INTERVAL = 60  # seconds

# Logging config
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Get RSI
def get_rsi(symbol):
    try:
        bars = api.get_bars(symbol, "1Day", limit=RSI_PERIOD + 1).df
        if len(bars) < RSI_PERIOD + 1:
            return None

        delta = bars.close.diff()[1:]
        gain = delta.where(delta > 0, 0).mean()
        loss = -delta.where(delta < 0, 0).mean()
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    except Exception as e:
        logging.error(f"RSI error for {symbol}: {e}")
        return None

# Buy logic
def evaluate_and_trade():
    for symbol in WATCHLIST:
        rsi = get_rsi(symbol)
        if rsi is None:
            continue

        logging.info(f"🔎 {symbol} RSI: {rsi}")
        if rsi < RSI_BUY_THRESHOLD:
            try:
                price = float(api.get_last_trade(symbol).price)
                cash = float(api.get_account().cash)
                qty = int(cash // price)
                if qty > 0:
                    api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side='buy',
                        type='market',
                        time_in_force='day'
                    )
                    logging.info(f"✅ Bought {qty} shares of {symbol} @ ${price:.2f}")
                else:
                    logging.info(f"⚠️ Not enough cash to buy {symbol}")
            except Exception as e:
                logging.error(f"❌ Buy error for {symbol}: {e}")

# Sell logic

def manage_open_trades():
    try:
        positions = api.list_positions()
        for pos in positions:
            symbol = pos.symbol
            qty = int(float(pos.qty))
            pl_pct = float(pos.unrealized_plpc)

            if qty < 1:
                continue

            if pl_pct >= TAKE_PROFIT or pl_pct <= STOP_LOSS:
                try:
                    api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side='sell',
                        type='market',
                        time_in_force='day'
                    )
                    logging.info(f"💰 Sold {symbol} | Qty: {qty} | P/L: {pl_pct*100:.2f}%")
                except Exception as e:
                    logging.error(f"❌ Sell error for {symbol}: {e}")
    except Exception as e:
        logging.error(f"❌ Error managing trades: {e}")

# Main loop
while True:
    try:
        account = api.get_account()
        logging.info(f"💰 Cash: ${float(account.cash):,.2f} | Buying Power: ${float(account.buying_power):,.2f}")

        evaluate_and_trade()
        manage_open_trades()

        logging.info("⏱️ Sleeping...")
        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        logging.error(f"Unhandled error: {e}")
        time.sleep(10)
