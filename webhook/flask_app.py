import os
import re
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request
from telegram import Update, Bot
from agent.core import process_message, handle_new_chat
from services.db import get_client, check_and_mark_update_processed
from config import TELEGRAM_BOT_TOKEN, PORT

app = Flask(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)


def send_file_if_present(chat_id: int, text: str):
    """Send PDF/PPTX files referenced in response text."""
    for ext in ('.pdf', '.pptx'):
        match = re.search(r'([\w.-]+\.' + ext.lstrip('.') + r')', text)
        if match and os.path.exists(match.group(1)):
            with open(match.group(1), 'rb') as f:
                asyncio.run(bot.send_document(chat_id=chat_id, document=f))


async def process_update(update: Update):
    if not update or not update.message or not update.message.text:
        return
    
    # Idempotency: skip already-processed updates
    update_id = update.update_id
    if not check_and_mark_update_processed(update_id):
        print(f"Duplicate update {update_id} skipped")
        return
    
    user_text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Handle /new command
    if user_text.strip() == "/new":
        reply = handle_new_chat(chat_id)
        await bot.send_message(chat_id=chat_id, text=reply)
        return
    
    # Send typing indicator
    await bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Process via agent
    result = process_message(chat_id, user_text)
    reply_text = result.get("text", "Sorry, I couldn't process that.")
    
    # Send response
    await bot.send_message(chat_id=chat_id, text=reply_text)
    
    # Send any generated files
    send_file_if_present(chat_id, reply_text)


@app.route("/")
def health():
    return "Kirana Agent Webhook Server Running"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method != "POST":
        return "OK"
    
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        if update:
            asyncio.run(process_update(update))
    except Exception as e:
        print(f"Webhook error: {type(e).__name__}: {e}")
        try:
            if update and update.effective_chat:
                asyncio.run(bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Internal error. Please try again."
                ))
        except Exception:
            pass
    
    return "OK"


@app.route("/cron/reminders", methods=["GET"])
def cron_reminders():
    """Send khata payment reminders (triggered by cron)."""
    try:
        from services.db import get_client
        supabase = get_client()
        res = supabase.table("Customer").select("*").gt("balance", 0).execute()
        if not res.data:
            return "No pending khata balances."
        
        # Get an active chat to send to
        hist = supabase.table("ChatMessage").select("chatId").limit(1).execute()
        if not hist.data:
            return "No active chats."
        
        chat_id = hist.data[0]["chatId"]
        msg = "📋 *Khata Reminders*\nCustomers with pending balances:\n"
        for c in res.data:
            msg += f"- {c['name']}: ₹{c['balance']:.2f}\n"
        
        asyncio.run(bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"))
        return "Reminders sent."
    except Exception as e:
        return str(e), 500


@app.route("/cron/weekly-report", methods=["GET"])
def cron_weekly_report():
    """Generate and send weekly analysis deck (triggered by cron)."""
    try:
        from services.pptx import generate_analysis_deck
        from services.db import get_client
        supabase = get_client()
        
        hist = supabase.table("ChatMessage").select("chatId").limit(1).execute()
        if not hist.data:
            return "No active chats."
        chat_id = hist.data[0]["chatId"]
        
        pptx_path = generate_analysis_deck()
        
        asyncio.run(bot.send_message(
            chat_id=chat_id,
            text="📊 *Weekly Analysis Deck Ready*",
            parse_mode="Markdown"
        ))
        with open(pptx_path, 'rb') as f:
            asyncio.run(bot.send_document(chat_id=chat_id, document=f))
        return "Report sent."
    except Exception as e:
        return str(e), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)