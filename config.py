import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing in environment")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Supabase credentials missing in environment")

# LLM - DeepSeek Official API (OpenAI-compatible, works on Python 3.13)
# GET KEY FROM: https://platform.deepseek.com
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Fallback: OpenAI (if DeepSeek key not provided)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.openai.com/v1"

# Original NVIDIA (blocked from this network, but kept for reference)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

# App
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Constants
BILL_STATUS_DRAFT = "DRAFT"
BILL_STATUS_FINALIZED = "FINALIZED"
PAYMENT_METHODS = ["Cash", "UPI", "Card"]
GST_SLABS = [0, 5, 12, 18]