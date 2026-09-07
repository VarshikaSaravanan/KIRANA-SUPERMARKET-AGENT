import traceback
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, OPENAI_API_KEY, OPENAI_BASE_URL
from skills.inventory import find_product, stock_in, add_product, check_stock, list_low_stock
from skills.billing import billing_start, billing_add_item, billing_remove_item, billing_view, billing_finalize
from skills.khata import khata_manage
from skills.reporting import daily_summary, set_owner_preference, get_owner_preferences
from services.pdf import create_invoice_pdf
from services.pptx import create_analysis_deck
from services.db import get_client, get_chat_history, save_chat_message, clear_chat_history


def get_llm():
    """Get LLM from available providers (priority: DeepSeek > OpenAI)."""
    # 1. DeepSeek Official (recommended - fast, cheap, works on this network)
    if DEEPSEEK_API_KEY:
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=4096,
            timeout=30,
            max_retries=2,
        )
    # 2. OpenAI (fallback)
    if OPENAI_API_KEY:
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            temperature=0.1,
            max_tokens=4096,
            timeout=30,
            max_retries=2,
        )
    raise ValueError("No LLM API key found. Set DEEPSEEK_API_KEY (get from https://platform.deepseek.com) or OPENAI_API_KEY")


llm = get_llm()
print(f"[LLM] Using model: {llm.model_name}, base_url: {llm.openai_api_base}")


# Tool registry
TOOLS = [
    find_product, stock_in, add_product, check_stock, list_low_stock,
    billing_start, billing_add_item, billing_remove_item, billing_view, billing_finalize,
    khata_manage, daily_summary, set_owner_preference, get_owner_preferences,
    create_invoice_pdf, create_analysis_deck,
]

# System prompt
SYSTEM_PROMPT = """You are a Kirana Store Operations Agent. You manage inventory, billing, customer credit (khata), and reports for an Indian supermarket.

You operate via Telegram. The owner speaks in plain, terse language. You have tools for every operation — use them. Never guess prices, stock, or GST; always call the appropriate tool.

KEY RULES:
1. ALWAYS call find_product FIRST when a product is mentioned (billing, stock-in, query).
2. Billing is multi-turn: start → add_item (repeat) → view/edit → finalize. Stock decrements ONLY on finalize.
3. GST is calculated per item: taxable = sellPrice/(1+gst%), CGST=SGST=tax/2. Use sellPrice, not MRP.
4. Oversell is blocked at database level (RPC). If stock insufficient, tool will refuse.
5. Idempotency: billing_start accepts idempotency_key; billing_finalize checks status.
6. Khata: create customer → credit (they owe) → payment (reduces owed) → balance.
7. Preferences persist across chats (owner_preferences table).
8. Generate PDF invoices and PPTX decks via tools when asked.

If ambiguous (e.g., "add atta" — which variant?), ask for clarification. Don't assume.

Be concise. Respond in plain language like a shop assistant."""


# Create React agent (LangGraph)
agent = create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


def process_message(chat_id: int, user_message: str) -> dict:
    """Process a user message through the agent with chat history."""
    try:
        print(f"[AGENT] Loading history for chat {chat_id}")
        history = get_chat_history(chat_id)
        print(f"[AGENT] History loaded: {len(history)} messages")
        lc_history = []
        for msg in history:
            if msg['role'] == 'user':
                lc_history.append(HumanMessage(content=msg['content']))
            else:
                lc_history.append(AIMessage(content=msg['content']))
        
        greeting = ""
        if not history:
            greeting = "[First conversation. Briefly introduce yourself and capabilities.]\n\n"
        
        input_messages = lc_history + [HumanMessage(content=greeting + user_message)]
        print(f"[AGENT] Invoking agent with {len(input_messages)} messages")
        
        response = agent.invoke({"messages": input_messages})
        print(f"[AGENT] Agent response received")
        
        output = response["messages"][-1].content
        
        save_chat_message(chat_id, "user", user_message)
        save_chat_message(chat_id, "assistant", output)
        
        return {"text": output}
    
    except Exception as e:
        traceback.print_exc()
        return {"text": f"Error: {str(e)}. Check logs."}


def handle_new_chat(chat_id: int) -> str:
    """Clear chat history but keep preferences."""
    clear_chat_history(chat_id)
    return "Chat cleared. Your store preferences are still saved."