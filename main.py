import os
import time
from alpaca_trade_api.rest import REST, TimeFrame

# Load environment variables
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

# Confirm API keys loaded
if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing Alpaca API credentials. Check your environment variables.")

# Connect to Alpaca
api = REST(API_KEY, API_SECRET, BASE_URL)

# List of stocks to monitor
symbols = ["AAPL", "TSLA", "NVDA"]

def check_account_and_prices():
    try:
        account = api.get_account()
        print(f"💼 Account: Cash = ${account.cash}, Buying Power = ${account.buying_power}")
    except Exception as e:
        print(f"❌ Failed to fetch account: {e}")
        return

    for symbol in symbols:
        try:
            last_price = api.get_last_trade(symbol).price
            print(f"📈 {symbol}: ${last_price}")
        except Exception as e:
            print(f"❌ Failed to fetch {symbol} price: {e}")

if __name__ == "__main__":
    print("✅ Bot started.")
    while True:
        check_account_and_prices()
        print("⏳ Sleeping for 60 seconds...\n")
        time.sleep(60)
