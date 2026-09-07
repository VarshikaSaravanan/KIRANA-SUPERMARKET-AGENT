# Kirana Store Operations Agent

A Telegram-only conversational agent that runs an Indian kirana/supermarket end-to-end: stock management, billing with GST, customer credit (khata), daily reports, PDF invoices, and PPTX analysis decks.

## Features

- **Inventory**: Stock-in, new products, stock queries, low-stock alerts
- **Billing**: Multi-turn draft bills with edits, atomic finalize, GST breakdown (CGST/SGST)
- **Khata (Credit)**: Customer ledger with credit/payment tracking
- **Reports**: Daily sales summary, payment split, GST collected
- **Documents**: GST-compliant PDF invoices, business analysis PPTX decks
- **Preferences**: Persistent owner settings across chats
- **Idempotency**: Safe retry handling at webhook and bill level
- **Concurrency**: Row-level locks prevent stock corruption

## Architecture

```
kirana-agent/
├── agent/core.py          # Agent loop, prompt, executor
├── skills/                # Domain tools (called by agent)
│   ├── inventory.py
│   ├── billing.py
│   ├── khata.py
│   └── reporting.py
├── services/              # External integrations
│   ├── db.py              # Supabase client + helpers
│   ├── pdf.py             # Invoice generation (reportlab)
│   └── pptx.py            # Analysis deck (python-pptx)
├── webhook/               # Telegram entry points
│   ├── flask_app.py       # Webhook server (production)
│   └── polling.py         # Long polling (local dev)
├── migrations/            # SQL schema + RPCs
├── seed.py                # Sample product data
├── config.py              # Environment & constants
└── main.py                # Entry point
```

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Supabase project (PostgreSQL)
- Telegram bot token (@BotFather)
- DeepSeek V4 Pro API key (via NVIDIA endpoints)

### 2. Setup
```bash
cd kirana-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### 3. Database
Run the migration in Supabase SQL editor:
```sql
-- Copy contents of migrations/001_schema.sql
```

Seed sample products:
```bash
python seed.py
```

### 4. Local Development (Polling)
```bash
python webhook/polling.py
```
Message your bot on Telegram.

### 5. Local Webhook (with ngrok)
```bash
# Terminal 1
python webhook/flask_app.py

# Terminal 2
ngrok http 5000
# Copy the https URL, then:
python -c "import requests, os; requests.post(f'https://api.telegram.org/bot{os.getenv(\"TELEGRAM_BOT_TOKEN\")}/setWebhook', json={'url': 'https://YOUR_NGROK_URL/webhook'})"
```

### 6. Deploy to Render
1. Push this repo to GitHub
2. Create new Web Service on Render from repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
5. Add environment variables in Render dashboard
6. After deploy, set webhook:
```bash
python -c "import requests, os; requests.post(f'https://api.telegram.org/bot{os.getenv(\"TELEGRAM_BOT_TOKEN\")}/setWebhook', json={'url': 'https://YOUR_RENDER_URL/webhook'})"
```

## Usage Examples

```
# Stock
"50 packets Maggi received at cost 12 MRP 14"
"new item: Amul Butter 100g, GST 12%, sell 52, MRP 54"

# Billing (multi-turn)
"start bill"
"add 2kg sugar, 1 Aashirvaad atta 5kg, 4 Maggi"
"remove butter"
"change Maggi to 6"
"finalize UPI"

# Stock query
"how much sugar left?"
"what's running low?"

# Khata
"Ramesh bought 500 on credit"
"Ramesh paid 300"
"Ramesh balance?"

# Reports
"today's sales"
"close the day"

# Documents
"send that bill as PDF"
"generate weekly analysis deck"

# Preferences
"always default to UPI"
"my shop name is Gupta Kirana"
```

## Key Technical Details

### GST Calculation
- Per-item: `taxable = sellPrice / (1 + gstRate/100) * qty`
- `CGST = SGST = (sellPrice * qty - taxable) / 2`
- Stored at item level in `BillItem` for audit trail

### Idempotency
- **Webhook**: `ProcessedUpdate` table deduplicates Telegram retries
- **Billing**: `idempotencyKey` on `Bill` prevents double-finalize
- **Stock**: `decrement_stock_safe` RPC with `FOR UPDATE` lock

### Concurrency
- `SELECT ... FOR UPDATE` in RPC serializes stock decrements
- Draft bills isolated per chat until finalize

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (not anon) |
| `DEEPSEEK_API_KEY` | DeepSeek V4 Pro via NVIDIA |
| `WEBHOOK_URL` | Production webhook URL |
| `PORT` | Server port (default 5000) |

## License

MIT