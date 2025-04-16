import os
import time
from alpaca_trade_api.rest import REST, TimeFrame

# Load environment variables (Render automatically injects them)
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

print("✅ Starting bot...")

if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials!")

# Initialize API
api = REST(API_KEY, API_SECRET, BASE_URL)

def run_strategy():
    print("🚀 Checking account + stock prices...")

    # Account info
    account = api.get_account()
    print(f"💰 Cash: ${account.cash} | Buying Power: ${account.buying_power}")

    # Stock check
    symbols = ["AAPL", "TSLA", "NVDA"]
    for symbol in symbols:
        try:
            price = api.get_last_trade(symbol).price
            print(f"📈 {symbol} price: ${price}")
        except Exception as e:
            print(f"❌ Error getting {symbol}: {e}")

while True:
    run_strategy()
    print("🕐 Waiting 60s...\n")
    time.sleep(60)
