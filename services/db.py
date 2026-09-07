import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Initialize Supabase client
_supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_client() -> Client:
    return _supabase


# Helper functions for common operations
def fetch_one(table: str, filters: dict):
    res = _supabase.table(table).select("*").match(filters).limit(1).execute()
    return res.data[0] if res.data else None


def fetch_all(table: str, filters: dict = None, order: str = None):
    query = _supabase.table(table).select("*")
    if filters:
        query = query.match(filters)
    if order:
        query = query.order(order)
    res = query.execute()
    return res.data or []


def insert_row(table: str, data: dict):
    res = _supabase.table(table).insert(data).execute()
    return res.data[0] if res.data else None


def upsert_row(table: str, data: dict, on_conflict: str = None):
    query = _supabase.table(table).upsert(data)
    if on_conflict:
        query = query.on_conflict(on_conflict)
    res = query.execute()
    return res.data[0] if res.data else None


def update_row(table: str, data: dict, filters: dict):
    res = _supabase.table(table).update(data).match(filters).execute()
    return res.data[0] if res.data else None


def delete_rows(table: str, filters: dict):
    res = _supabase.table(table).delete().match(filters).execute()
    return res.data


def rpc_call(fn_name: str, params: dict):
    return _supabase.rpc(fn_name, params).execute()


def search_products(term: str):
    return _supabase.table("Product").select(
        "id,name,brand,unit,costPrice,mrp,sellPrice,quantity,reorderLevel,hsnCode,gstRate,isLoose"
    ).ilike("name", f"%{term}%").execute().data or []


def get_product_by_id(product_id: str):
    return fetch_one("Product", {"id": product_id})


def get_low_stock_products():
    all_products = fetch_all("Product")
    return [p for p in all_products if float(p["quantity"]) <= float(p["reorderLevel"])]


def get_finalized_bills_today():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return _supabase.table("Bill").select("*").eq("status", BILL_STATUS_FINALIZED).gte("createdAt", f"{today}T00:00:00").execute().data or []


def get_all_finalized_bills():
    return _supabase.table("Bill").select("*").eq("status", BILL_STATUS_FINALIZED).execute().data or []


def get_bill_with_items(bill_id: str):
    bill = fetch_one("Bill", {"id": bill_id})
    if not bill:
        return None, []
    items = _supabase.table("BillItem").select(
        "*, Product(name,hsnCode,gstRate)"
    ).eq("billId", bill_id).execute().data or []
    return bill, items


def get_chat_history(chat_id: int, limit: int = 50):
    res = _supabase.table("ChatMessage").select("*").eq("chatId", chat_id).order("createdAt", desc=True).limit(limit).execute()
    return list(reversed(res.data)) if res.data else []


def save_chat_message(chat_id: int, role: str, content: str):
    _supabase.table("ChatMessage").insert({
        "chatId": chat_id,
        "role": role,
        "content": content
    }).execute()


def clear_chat_history(chat_id: int):
    _supabase.table("ChatMessage").delete().eq("chatId", chat_id).execute()


def check_and_mark_update_processed(update_id: int) -> bool:
    """Returns True if this is a new update (not processed before)."""
    try:
        _supabase.table("ProcessedUpdate").insert({"updateId": update_id}).execute()
        return True
    except Exception:
        return False  # Duplicate update