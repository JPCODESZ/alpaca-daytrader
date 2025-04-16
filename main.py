import os
import time
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame, APIError

load_dotenv()

API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_API_BASE_URL")

print("✅ Script started")
print("🔍 API_KEY:", API_KEY)
print("🔍 BASE_URL:", BASE_URL)

if not API_KEY or not API_SECRET or not BASE_URL:
    raise ValueError("❌ Missing API credentials. Check your .env or Render environment variables.")

api = REST(API_KEY, API_SECRET, BASE_URL)

def run_strategy():
    print("🚀 Running trading strategy...")
    try:
        account = api.get_account()
        print(f"💰 Cash: {account.cash} | Buying Power: {account.buying_power}")
    except Exception as e:
        print(f"❌ Error fetching account: {e}")

    symbols = ["TSLA", "AAPL", "NVDA"]
    for symbol in symbols:
        print(f"🔎 Checking {symbol}...")
        try:
            price = float(api.get_last_trade(symbol).price)
            print(f"{symbol} last price: ${price}")
        except Exception as e:
            print(f"❌ Error fetching price for {symbol}: {e}")

# Keep looping every minute
while True:
    run_strategy()
    print("🕐 Waiting 60s...\n")
    time.sleep(60)
