# Kirana Store Operations Agent

**Telegram Bot:** `@Varshika_Supermarket_bot`

A Telegram-only conversational agent that operates an Indian kirana/supermarket end-to-end. The agent handles inventory, billing with GST, customer credit (khata), reporting, PDF invoices and business analysis decks through natural-language conversations.

## 1. Harness & Why I Picked It

I built the agent using a **Python + Telegram + Supabase** harness.

* **Telegram** is the user-facing interface, making the system accessible without building a separate frontend.
* **Python** provides a lightweight environment for implementing the agent loop, domain skills, document generation, and integrations.
* **Supabase/PostgreSQL** provides persistent storage and transactional database operations.
* **DeepSeek V4 Pro via NVIDIA endpoints** is used as the reasoning/model layer for interpreting natural-language requests and deciding which tools to call.
* **Flask + Gunicorn** provides the production webhook server, while polling is available for local development.
* **ReportLab** generates GST invoices as PDFs and **python-pptx** generates business analysis decks.

This harness was chosen because it keeps the architecture simple, inexpensive, Telegram-native, and easy to deploy while still providing reliable database transactions for business-critical operations.

## 2. Control Loop

The agent follows a **tool-using control loop** rather than directly modifying the database from the language model.

```text
Telegram Message
       ↓
Webhook / Polling
       ↓
Agent Core
       ↓
LLM interprets intent
       ↓
Select appropriate skill/tool
       ↓
Validate arguments
       ↓
Execute database/service operation
       ↓
Tool result returned to Agent
       ↓
LLM decides next action or response
       ↓
Telegram Reply / Generated Document
```

The agent maintains conversational state for tasks such as multi-turn billing. For example:

```text
User: start bill
Agent: Bill started.

User: add 2kg sugar and 4 Maggi
Agent: Added items to draft bill.

User: change Maggi to 6
Agent: Updated Maggi quantity to 6.

User: finalize UPI
Agent: Bill finalized and stock deducted.
```

The model is responsible for **understanding intent and choosing tools**, while deterministic code handles database updates, calculations, locking, and document generation.

## 3. Skill / Tool Design

The agent is divided into domain-specific skills so that each business operation has a clear responsibility.

### Inventory Skill

Handles:

* Adding new products
* Stock-in
* Stock queries
* Low-stock detection

### Billing Skill

Handles:

* Creating draft bills
* Adding/removing/updating items
* GST calculation
* Finalizing bills
* Atomic stock deduction
* Idempotent finalization

### Khata Skill

Handles:

* Customer credit
* Payments
* Outstanding balances
* Customer ledger history

### Reporting Skill

Handles:

* Daily sales
* Payment-method breakdown
* GST collected
* Business summaries

### Document Tools

Separate services generate:

* GST-compliant PDF invoices using ReportLab
* Business analysis PPTX decks using python-pptx

The tools expose **structured inputs and outputs** instead of allowing the LLM to directly manipulate SQL. This keeps business-critical operations deterministic and easier to validate and debug.

## 4. Hard Parts & Solutions

### Multi-turn billing

Bills are maintained as drafts until the owner explicitly finalizes them. This allows natural edits such as adding, removing, or changing quantities without affecting stock prematurely.

### GST accuracy

GST is calculated deterministically at item level:

```text
Taxable = Selling Price / (1 + GST Rate / 100) × Quantity
GST = Gross Amount - Taxable
CGST = GST / 2
SGST = GST / 2
```

The calculated values are stored with each bill item for auditability.

### Preventing duplicate Telegram updates

Telegram/webhook retries can cause the same update to arrive more than once. A `ProcessedUpdate` record is used to make webhook processing idempotent.

### Preventing duplicate bill finalization

Each bill has an idempotency key so that retrying the finalize operation cannot create duplicate transactions.

### Concurrent stock updates

Stock deduction uses a PostgreSQL RPC with `SELECT ... FOR UPDATE`. This serializes concurrent updates and prevents stock from becoming corrupted when multiple operations attempt to modify the same product.

### Keeping drafts isolated

Draft bills are associated with the Telegram chat, allowing each conversation to maintain its own bill state until finalization.

### Reliable document generation

PDF and PPTX creation is separated from the agent reasoning layer. The agent requests document generation through services, while deterministic Python code produces the final files.

## 5. Architecture

```text
kirana-agent/
├── agent/
│   └── core.py              # Agent loop and executor
├── skills/
│   ├── inventory.py         # Inventory tools
│   ├── billing.py           # Billing tools
│   ├── khata.py             # Credit/ledger tools
│   └── reporting.py         # Reports
├── services/
│   ├── db.py                # Supabase/PostgreSQL
│   ├── pdf.py               # PDF invoices
│   └── pptx.py              # Analysis decks
├── webhook/
│   ├── flask_app.py         # Production webhook
│   └── polling.py           # Local development
├── migrations/
│   └── 001_schema.sql
├── seed.py
├── config.py
└── main.py
```

## 6. Example Capabilities

The owner can interact entirely through Telegram:

```text
"50 packets Maggi received at cost 12 MRP 14"
"how much sugar is left?"
"start bill"
"add 2kg sugar and 4 Maggi"
"change Maggi to 6"
"finalize UPI"
"Ramesh bought 500 on credit"
"Ramesh paid 300"
"Ramesh balance?"
"today's sales"
"send that bill as PDF"
"generate weekly analysis deck"
"always default to UPI"
```

The result is a **Telegram-first supermarket operations agent** where the LLM handles natural-language interaction and tool selection, while deterministic backend services handle transactions, calculations, persistence, concurrency, and document generation.
