import os
import re
import sys
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from agent.core import process_message, handle_new_chat
from config import TELEGRAM_BOT_TOKEN

load_dotenv()

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    print("\n[SHUTDOWN] Ctrl+C received, stopping gracefully...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    print(f"[START] User {user.id} (@{user.username}) in chat {chat_id}")
    await update.message.reply_text(
        "🏪 Kirana Store Agent\n\n"
        "I manage your shop: stock, bills, khata, reports.\n"
        "Try: '50 Maggi received at ₹12', 'bill: 2kg sugar, 1 atta, UPI', "
        "'Ramesh owes 500', 'today sales', 'send invoice PDF'.\n\n"
        "Use /new to clear chat (preferences saved)."
    )


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the chat history for this user."""
    chat_id = update.effective_chat.id
    user = update.effective_user
    print(f"[NEW] User {user.id} in chat {chat_id}")
    reply = handle_new_chat(chat_id)
    await update.message.reply_text(reply)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user messages via the agent."""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user = update.effective_user

    print(f"[MSG] User {user.id} (@{user.username}) in chat {chat_id}: {user_message}")

    # Send processing action
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Call agent
        print(f"[AGENT] Processing message for chat {chat_id}...")
        response = process_message(chat_id, user_message)
        print(f"[AGENT] Got response: {response}")
        reply_text = response.get("text", "Error processing request.")

        print(f"[REPLY] Chat {chat_id}: {reply_text[:200]}")

        # Send text response
        await update.message.reply_text(reply_text)
        print(f"[SENT] Reply sent to chat {chat_id}")

        # Check for generated files
        for ext in ('.pdf', '.pptx'):
            match = re.search(r'([\w.-]+\.' + ext.lstrip('.') + r')', reply_text)
            if match and os.path.exists(match.group(1)):
                print(f"[FILE] Sending {match.group(1)} to chat {chat_id}")
                await update.message.reply_document(document=open(match.group(1), 'rb'))

    except Exception as e:
        print(f"[ERROR] Chat {chat_id}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await update.message.reply_text(f"Sorry, an error occurred: {str(e)}")
        except Exception:
            pass  # Ignore if we can't send error message


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors from the Application."""
    print(f"[APP ERROR] {context.error}")
    import traceback
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)


async def post_init(application: Application) -> None:
    """Called after application starts."""
    print("[INIT] Bot initialized and polling started")
    me = await application.bot.get_me()
    print(f"[BOT] Connected as @{me.username} (ID: {me.id})")


async def post_shutdown(application: Application) -> None:
    """Called before application stops."""
    print("[SHUTDOWN] Bot stopped")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    print("=" * 50)
    print("Starting Kirana Store Agent...")
    print(f"Bot token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print("=" * 50)

    # Create the Application with network timeouts
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_chat))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    print("Bot is polling. Press Ctrl+C to stop.")
    print("=" * 50)

    # Run with drop_pending_updates to avoid processing old messages
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )


if __name__ == "__main__":
    main()