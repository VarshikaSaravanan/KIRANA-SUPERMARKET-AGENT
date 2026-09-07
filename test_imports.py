from agent.core import process_message
from skills.inventory import find_product, stock_in, add_product, check_stock, list_low_stock
from skills.billing import billing_start, billing_add_item, billing_remove_item, billing_view, billing_finalize
from skills.khata import khata_manage
from skills.reporting import daily_summary, set_owner_preference, get_owner_preferences
from services.pdf import create_invoice_pdf
from services.pptx import create_analysis_deck
from services.db import get_client, fetch_one, fetch_all
from config import TELEGRAM_BOT_TOKEN, SUPABASE_URL

print("All imports OK")