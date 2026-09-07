from langchain_core.tools import tool
from services.db import (
    get_product_by_id, insert_row, update_row, fetch_all, fetch_one,
    rpc_call, get_bill_with_items
)
from typing import Optional
import uuid
from datetime import datetime


@tool
def billing_start(chat_id: int, idempotency_key: Optional[str] = None) -> str:
    """
    Start a new draft bill. Returns bill_id.
    Provide idempotency_key to safely retry (e.g., 'chat123-bill-1').
    """
    bill_id = str(uuid.uuid4())
    ikey = idempotency_key or f"{chat_id}-{bill_id[:8]}"
    
    data = {
        "id": bill_id,
        "status": "DRAFT",
        "totalAmount": 0,
        "taxAmount": 0,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "telegramChatId": chat_id,
        "idempotencyKey": ikey,
    }
    try:
        insert_row("Bill", data)
    except Exception as e:
        if "idempotencyKey" in str(e) or "duplicate" in str(e).lower():
            existing = fetch_one("Bill", {"idempotencyKey": ikey})
            if existing:
                return f"Bill already exists (idempotent). ID: {existing['id']}"
        raise
    
    return f"Started draft bill. ID: {bill_id}. Use this ID to add items."


@tool
def billing_add_item(bill_id: str, product_id: str, quantity: float) -> str:
    """Add an item to a draft bill. Checks stock availability."""
    bill = fetch_one("Bill", {"id": bill_id})
    if not bill:
        return f"Bill {bill_id} not found."
    if bill["status"] != "DRAFT":
        return f"Bill {bill_id} is not a draft (status: {bill['status']})."
    
    product = get_product_by_id(product_id)
    if not product:
        return f"Product {product_id} not found."
    
    if float(product["quantity"]) < float(quantity):
        return f"Insufficient stock. {product['name']} has {product['quantity']} {product['unit']} available, requested {quantity}."
    
    sell_price = float(product["sellPrice"])
    gst_rate = float(product["gstRate"])
    qty = float(quantity)
    
    # GST calculation: base = sell_price / (1 + gst_rate/100)
    taxable_value = round(sell_price / (1 + gst_rate / 100) * qty, 2)
    total_tax = round(sell_price * qty - taxable_value, 2)
    cgst = round(total_tax / 2, 2)
    sgst = round(total_tax / 2, 2)
    total = round(sell_price * qty, 2)
    
    item_id = str(uuid.uuid4())
    item_data = {
        "id": item_id,
        "billId": bill_id,
        "productId": product_id,
        "quantity": qty,
        "unitPrice": sell_price,
        "gstRate": gst_rate,
        "total": total,
        "taxableValue": taxable_value,
        "cgstAmount": cgst,
        "sgstAmount": sgst,
    }
    insert_row("BillItem", item_data)
    
    return f"Added {qty} x {product['name']} @ ₹{sell_price:.2f} = ₹{total:.2f} (Taxable: ₹{taxable_value:.2f}, CGST: ₹{cgst:.2f}, SGST: ₹{sgst:.2f})"


@tool
def billing_remove_item(bill_id: str, product_id: str) -> str:
    """Remove an item from a draft bill."""
    from services.db import delete_rows
    delete_rows("BillItem", {"billId": bill_id, "productId": product_id})
    return f"Removed product {product_id} from bill {bill_id}."


@tool
def billing_view(bill_id: str) -> str:
    """View current draft bill contents and totals."""
    bill = fetch_one("Bill", {"id": bill_id})
    if not bill:
        return f"Bill {bill_id} not found."
    
    items = fetch_all("BillItem", {"billId": bill_id})
    if not items:
        return f"Bill {bill_id} is empty."
    
    lines = []
    subtotal = 0
    total_tax = 0
    for item in items:
        # Get product name
        from services.db import get_product_by_id
        prod = get_product_by_id(item["productId"])
        name = prod["name"] if prod else item["productId"]
        lines.append(
            f"- {name}: {item['quantity']} x ₹{item['unitPrice']:.2f} = ₹{item['total']:.2f} "
            f"(Taxable: ₹{item['taxableValue']:.2f}, CGST: ₹{item['cgstAmount']:.2f}, SGST: ₹{item['sgstAmount']:.2f})"
        )
        subtotal += item["total"]
        total_tax += item["cgstAmount"] + item["sgstAmount"]
    
    return (
        f"Draft Bill {bill_id}:\n" + "\n".join(lines) +
        f"\nSubtotal: ₹{subtotal:.2f}\nTotal Tax (CGST+SGST): ₹{total_tax:.2f}\nGrand Total: ₹{subtotal:.2f}"
    )


@tool
def billing_finalize(bill_id: str, payment_method: str, customer_id: Optional[str] = None) -> str:
    """
    Finalize bill: atomically decrement stock, compute totals, mark finalized.
    payment_method: Cash, UPI, or Card
    """
    if payment_method not in ["Cash", "UPI", "Card"]:
        return "Invalid payment method. Use: Cash, UPI, or Card."
    
    bill = fetch_one("Bill", {"id": bill_id})
    if not bill:
        return f"Bill {bill_id} not found."
    if bill["status"] == "FINALIZED":
        return f"Bill {bill_id} already finalized (idempotent)."
    
    items = fetch_all("BillItem", {"billId": bill_id})
    if not items:
        return "Cannot finalize empty bill."
    
    total_amount = 0
    total_tax = 0
    
    for item in items:
        qty = float(item["quantity"])
        total_amount += float(item["total"])
        total_tax += float(item["cgstAmount"]) + float(item["sgstAmount"])
        
        # Atomic stock decrement via RPC
        try:
            rpc_call("decrement_stock_safe", {"p_id": item["productId"], "p_quantity": qty})
        except Exception as e:
            return f"Stock decrement failed for {item['productId']}: {str(e)}"
    
    update_data = {
        "status": "FINALIZED",
        "paymentMethod": payment_method,
        "totalAmount": total_amount,
        "taxAmount": total_tax,
        "updatedAt": datetime.now().isoformat(),
        "customerId": customer_id,
    }
    update_row("Bill", update_data, {"id": bill_id})
    
    return (
        f"Bill {bill_id} finalized!\n"
        f"Payment: {payment_method}\n"
        f"Total: ₹{total_amount:.2f}\n"
        f"Tax (CGST+SGST): ₹{total_tax:.2f}"
    )