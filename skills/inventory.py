from langchain_core.tools import tool
from services.db import (
    get_product_by_id, search_products, get_low_stock_products,
    insert_row, update_row
)
from typing import Optional
import uuid


@tool
def find_product(search_term: str) -> str:
    """
    ALWAYS call this first when user mentions a product.
    Searches product master by name. Returns matching products with IDs, prices, stock.
    If multiple distinct variants match (e.g., 5kg vs 10kg), ask user to clarify.
    If zero matches, treat as new product.
    """
    results = search_products(search_term)
    if not results:
        return f"No products found matching '{search_term}'. This may be a new item."
    
    lines = []
    for p in results:
        stock_info = f"{p['quantity']} {p['unit']}" if not p['isLoose'] else f"{p['quantity']} {p['unit']} (loose)"
        lines.append(
            f"- ID: {p['id']} | {p['name']} | {stock_info} | "
            f"Sell: ₹{p['sellPrice']} | MRP: ₹{p['mrp']} | Cost: ₹{p['costPrice']} | "
            f"GST: {p['gstRate']}% | Reorder: {p['reorderLevel']}"
        )
    
    return f"Found {len(results)} matching product(s):\n" + "\n".join(lines)


@tool
def stock_in(product_id: str, quantity: float, cost_price: Optional[float] = None, sell_price: Optional[float] = None, mrp: Optional[float] = None) -> str:
    """
    Receive stock for an existing product. Increments quantity.
    Optionally updates cost_price, sell_price, mrp if provided.
    """
    product = get_product_by_id(product_id)
    if not product:
        return f"Product with ID '{product_id}' not found."
    
    new_qty = float(product["quantity"]) + float(quantity)
    update_data = {"quantity": new_qty, "updatedAt": "now()"}
    if cost_price is not None:
        update_data["costPrice"] = float(cost_price)
    if sell_price is not None:
        update_data["sellPrice"] = float(sell_price)
    if mrp is not None:
        update_data["mrp"] = float(mrp)
    
    update_row("Product", update_data, {"id": product_id})
    
    msg = f"Stock received. {product['name']} now has {new_qty} {product['unit']} in stock."
    if any(v is not None for v in [cost_price, sell_price, mrp]):
        msg += " Prices updated."
    return msg


@tool
def add_product(
    product_id: str, name: str, unit: str, cost_price: float, sell_price: float, mrp: float,
    initial_stock: float, reorder_level: float, gst_rate: float,
    brand: Optional[str] = None, is_loose: bool = False, hsn_code: Optional[str] = None
) -> str:
    """
    Add a completely new product to the catalog.
    product_id: unique identifier (e.g., 'AASH-ATTA-5KG')
    """
    data = {
        "id": product_id,
        "name": name,
        "brand": brand,
        "isLoose": is_loose,
        "unit": unit,
        "costPrice": float(cost_price),
        "sellPrice": float(sell_price),
        "mrp": float(mrp),
        "quantity": float(initial_stock),
        "reorderLevel": float(reorder_level),
        "gstRate": float(gst_rate),
        "hsnCode": hsn_code,
    }
    insert_row("Product", data)
    return f"Added new product: {name} (ID: {product_id}) with {initial_stock} {unit} in stock."


@tool
def check_stock(item_name: str) -> str:
    """Query current stock level and prices for a product."""
    results = search_products(item_name)
    if not results:
        return f"No product found matching '{item_name}'."
    
    lines = []
    for p in results:
        lines.append(
            f"{p['name']} (ID: {p['id']}): {p['quantity']} {p['unit']} | "
            f"Sell: ₹{p['sellPrice']} | Cost: ₹{p['costPrice']} | GST: {p['gstRate']}%"
        )
    return "\n".join(lines)


@tool
def list_low_stock(dummy: str = "") -> str:
    """List products at or below reorder level."""
    low = get_low_stock_products()
    if not low:
        return "All items are well stocked."
    
    lines = [f"- {p['name']}: {p['quantity']} {p['unit']} (reorder at {p['reorderLevel']})" for p in low]
    return "Items running low:\n" + "\n".join(lines)