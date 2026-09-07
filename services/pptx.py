from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from services.db import get_all_finalized_bills, fetch_all
from langchain_core.tools import tool
from datetime import datetime


def generate_analysis_deck() -> str:
    """Generate a business analysis PPTX deck."""
    bills = get_all_finalized_bills()
    items = fetch_all("BillItem")
    
    # Aggregate data
    total_sales = sum(float(b["totalAmount"]) for b in bills)
    total_tax = sum(float(b["taxAmount"]) for b in bills)
    bill_count = len(bills)
    
    # Top products by quantity
    product_qty = {}
    product_revenue = {}
    for item in items:
        pid = item["productId"]
        product_qty[pid] = product_qty.get(pid, 0) + float(item["quantity"])
        product_revenue[pid] = product_revenue.get(pid, 0) + float(item["total"])
    
    # Get product names
    from services.db import get_product_by_id
    top_by_qty = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:5]
    top_by_rev = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Payment split
    upi = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "UPI")
    cash = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "Cash")
    card = sum(float(b["totalAmount"]) for b in bills if b["paymentMethod"] == "Card")
    
    prs = Presentation()
    
    # Slide 1: Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Kirana Store Business Analysis"
    slide.placeholders[1].text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Slide 2: Executive Summary
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Executive Summary"
    tf = slide.placeholders[1].text_frame
    tf.text = f"Total Orders: {bill_count}"
    for text, val in [
        ("Gross Sales", f"₹{total_sales:.2f}"),
        ("Total GST Collected", f"₹{total_tax:.2f}"),
        ("Avg Order Value", f"₹{total_sales/bill_count:.2f}" if bill_count else "₹0"),
    ]:
        p = tf.add_paragraph()
        p.text = f"{text}: {val}"
    
    # Slide 3: Payment Split
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Payment Method Split"
    tf = slide.placeholders[1].text_frame
    tf.text = f"UPI: ₹{upi:.2f} ({upi/total_sales*100:.1f}%)" if total_sales else "UPI: ₹0"
    for text, val in [("Cash", cash), ("Card", card)]:
        p = tf.add_paragraph()
        pct = f" ({val/total_sales*100:.1f}%)" if total_sales else ""
        p.text = f"{text}: ₹{val:.2f}{pct}"
    
    # Slide 4: Top Products by Quantity
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Top 5 Products by Quantity Sold"
    tf = slide.placeholders[1].text_frame
    if top_by_qty:
        tf.text = f"{get_product_by_id(top_by_qty[0][0])['name']}: {top_by_qty[0][1]} units"
        for pid, qty in top_by_qty[1:]:
            p = tf.add_paragraph()
            p.text = f"{get_product_by_id(pid)['name']}: {qty} units"
    else:
        tf.text = "No sales data yet."
    
    # Slide 5: Top Products by Revenue
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Top 5 Products by Revenue"
    tf = slide.placeholders[1].text_frame
    if top_by_rev:
        tf.text = f"{get_product_by_id(top_by_rev[0][0])['name']}: ₹{top_by_rev[0][1]:.2f}"
        for pid, rev in top_by_rev[1:]:
            p = tf.add_paragraph()
            p.text = f"{get_product_by_id(pid)['name']}: ₹{rev:.2f}"
    else:
        tf.text = "No sales data yet."
    
    pptx_path = f"analysis_{datetime.now().strftime('%Y%m%d')}.pptx"
    prs.save(pptx_path)
    return pptx_path


@tool
def create_analysis_deck(dummy: str = "") -> str:
    """Tool wrapper: Generate weekly/monthly analysis PPTX deck."""
    return generate_analysis_deck()