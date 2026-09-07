from langchain_core.tools import tool
from services.db import get_finalized_bills_today, get_all_finalized_bills, fetch_all, upsert_row, fetch_all as db_fetch_all
from datetime import datetime


@tool
def daily_summary(dummy: str = "") -> str:
    """Generate today's sales summary: total sales, tax, payment split."""
    bills = get_finalized_bills_today()
    if not bills:
        return f"No finalized sales today ({datetime.now().strftime('%Y-%m-%d')})."
    
    total_sales = sum(float(b["totalAmount"]) for b in bills)
    total_tax = sum(float(b["taxAmount"]) for b in bills)
    
    upi = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "UPI")
    cash = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "Cash")
    card = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "Card")
    
    return (
        f"--- Daily Summary ({datetime.now().strftime('%Y-%m-%d')}) ---\n"
        f"Bills: {len(bills)}\n"
        f"Total Sales: ₹{total_sales:.2f}\n"
        f"GST Collected: ₹{total_tax:.2f}\n"
        f"--- Payment Split ---\n"
        f"UPI: ₹{upi:.2f}\n"
        f"Cash: ₹{cash:.2f}\n"
        f"Card: ₹{card:.2f}"
    )


@tool
def set_owner_preference(key: str, value: str) -> str:
    """Save a persistent preference (e.g., default_payment=UPI, shop_name=My Kirana)."""
    upsert_row("OwnerPreference", {"key": key, "value": value, "id": key}, on_conflict="key")
    return f"Preference saved: {key} = {value}"


@tool
def get_owner_preferences(dummy: str = "") -> str:
    """Retrieve all saved preferences."""
    prefs = db_fetch_all("OwnerPreference")
    if not prefs:
        return "No preferences set."
    return "Saved Preferences:\n" + "\n".join(f"{p['key']}: {p['value']}" for p in prefs)