import os
import time
import logging
from alpaca_trade_api.rest import REST, TimeFrame

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load credentials
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# Validate credentials
if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials!")

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)

def run_strategy():
    try:
        logging.info("🔄 Checking account and stock prices...")

        # Get account details
        account = api.get_account()
        logging.info(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

        # Monitor selected tickers
        symbols = ["AAPL", "TSLA", "NVDA"]
        for symbol in symbols:
            try:
                price = api.get_last_trade(symbol).price
                logging.info(f"📈 {symbol} price: ${price}")
            except Exception as e:
                logging.error(f"❌ Error fetching price for {symbol}: {e}")

    except Exception as e:
        logging.error(f"❌ Strategy run failed: {e}")

# Loop forever
while True:
    run_strategy()
    logging.info("⏳ Waiting 60 seconds...\n")
    time.sleep(60)
