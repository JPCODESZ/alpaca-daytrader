import os
import time

print("✅ STARTING DEBUG ENV TEST")

print("APCA_API_KEY_ID:", os.getenv("APCA_API_KEY_ID"))
print("APCA_API_SECRET_KEY:", os.getenv("APCA_API_SECRET_KEY"))
print("APCA_API_BASE_URL:", os.getenv("APCA_API_BASE_URL"))

time.sleep(60)
