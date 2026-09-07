from langchain_core.tools import tool
from services.db import fetch_one, fetch_all, insert_row, update_row
from typing import Optional
import uuid
from datetime import datetime


@tool
def khata_manage(customer_name: str, action: str, amount: Optional[float] = None, customer_id: Optional[str] = None) -> str:
    """
    Manage customer credit (Khata).
    Actions:
    - 'create': Create new customer (requires customer_name, optional customer_id)
    - 'balance': Check balance (requires customer_name or customer_id)
    - 'credit': Add credit (customer bought on credit) - requires amount
    - 'payment': Record payment received - requires amount
    """
    # Resolve customer
    if customer_id:
        customer = fetch_one("Customer", {"id": customer_id})
    else:
        # Search by name (case-insensitive)
        results = fetch_all("Customer")
        customer = next((c for c in results if c["name"].lower() == customer_name.lower()), None)
    
    if action == "create":
        if customer:
            return f"Customer '{customer['name']}' already exists (ID: {customer['id']})."
        cid = customer_id or str(uuid.uuid4())
        insert_row("Customer", {"id": cid, "name": customer_name, "balance": 0})
        return f"Customer '{customer_name}' created (ID: {cid})."
    
    if not customer:
        return f"Customer '{customer_name}' not found. Use 'create' action first."
    
    cid = customer["id"]
    current_balance = float(customer["balance"])
    
    if action == "balance":
        if current_balance == 0:
            return f"{customer['name']} has no outstanding balance."
        return f"{customer['name']} owes ₹{current_balance:.2f}."
    
    if amount is None or amount <= 0:
        return "Please specify a valid positive amount."
    
    if action == "credit":
        new_balance = current_balance + amount
        update_row("Customer", {"balance": new_balance, "updatedAt": datetime.now().isoformat()}, {"id": cid})
        
        insert_row("KhataTransaction", {
            "id": str(uuid.uuid4()),
            "customerId": cid,
            "amount": amount,
            "type": "credit_added",
            "reference": "Purchase on credit",
            "createdAt": datetime.now().isoformat(),
        })
        return f"Added ₹{amount:.2f} credit for {customer['name']}. New balance: ₹{new_balance:.2f}."
    
    if action == "payment":
        new_balance = current_balance - amount
        update_row("Customer", {"balance": new_balance, "updatedAt": datetime.now().isoformat()}, {"id": cid})
        
        insert_row("KhataTransaction", {
            "id": str(uuid.uuid4()),
            "customerId": cid,
            "amount": amount,
            "type": "payment_received",
            "reference": "Payment received",
            "createdAt": datetime.now().isoformat(),
        })
        return f"Recorded ₹{amount:.2f} payment from {customer['name']}. Remaining balance: ₹{new_balance:.2f}."
    
    return f"Unknown action: {action}. Use: create, balance, credit, payment."