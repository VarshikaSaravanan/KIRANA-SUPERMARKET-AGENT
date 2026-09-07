import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in environment")

if __name__ == "__main__":
    url = input("Paste your public webhook URL (e.g. https://your-app.onrender.com/webhook): ").strip()
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        json={"url": url, "drop_pending_updates": True},
        timeout=30
    )
    data = resp.json()
    if data.get("ok"):
        print("✅ Webhook set:", data["result"].get("url"))
        info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=30).json()
        print("📋 Webhook info:", info.get("result"))
    else:
        print("❌ Failed to set webhook:", data)