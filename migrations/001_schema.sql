-- Kirana Agent Database Schema (Supabase/PostgreSQL)

-- 1. Product Master
CREATE TABLE IF NOT EXISTS "Product" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    "isLoose" BOOLEAN NOT NULL DEFAULT FALSE,
    unit TEXT NOT NULL,
    "costPrice" DOUBLE PRECISION NOT NULL,
    mrp DOUBLE PRECISION NOT NULL,
    "sellPrice" DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
    "reorderLevel" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "hsnCode" TEXT,
    "gstRate" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_name ON "Product" USING BTREE (name);

-- 2. Owner Preferences
CREATE TABLE IF NOT EXISTS "OwnerPreference" (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS "OwnerPreference_key_key" ON "OwnerPreference" USING BTREE (key);

-- 3. Customer (Khata)
CREATE TABLE IF NOT EXISTS "Customer" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- 4. Khata Transactions
CREATE TABLE IF NOT EXISTS "KhataTransaction" (
    id TEXT PRIMARY KEY,
    "customerId" TEXT NOT NULL REFERENCES "Customer"(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    amount DOUBLE PRECISION NOT NULL,
    type TEXT NOT NULL,
    reference TEXT,
    "createdAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Bills
CREATE TABLE IF NOT EXISTS "Bill" (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    "totalAmount" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "taxAmount" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "paymentMethod" TEXT,
    "createdAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    "telegramChatId" BIGINT,
    "customerId" TEXT REFERENCES "Customer"(id) ON UPDATE CASCADE ON DELETE SET NULL,
    "idempotencyKey" TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_bill_status_chat ON "Bill" USING BTREE (status, "telegramChatId");

-- 6. Bill Items (with GST breakdown)
CREATE TABLE IF NOT EXISTS "BillItem" (
    id TEXT PRIMARY KEY,
    "billId" TEXT NOT NULL REFERENCES "Bill"(id) ON UPDATE CASCADE ON DELETE CASCADE,
    "productId" TEXT NOT NULL REFERENCES "Product"(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    quantity DOUBLE PRECISION NOT NULL,
    "unitPrice" DOUBLE PRECISION NOT NULL,
    "gstRate" DOUBLE PRECISION NOT NULL,
    total DOUBLE PRECISION NOT NULL,
    "taxableValue" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "cgstAmount" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "sgstAmount" DOUBLE PRECISION NOT NULL DEFAULT 0
);

-- 7. Chat History
CREATE TABLE IF NOT EXISTS "ChatMessage" (
    id TEXT PRIMARY KEY DEFAULT (gen_random_uuid())::TEXT,
    "chatId" BIGINT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_message_chat ON "ChatMessage" USING BTREE ("chatId", "createdAt");

-- 8. Processed Updates (Telegram idempotency)
CREATE TABLE IF NOT EXISTS "ProcessedUpdate" (
    "updateId" BIGINT PRIMARY KEY,
    "processedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 9. Atomic Stock Decrement RPC (prevents oversell + race conditions)
CREATE OR REPLACE FUNCTION decrement_stock_safe(p_id TEXT, p_quantity NUMERIC)
RETURNS NUMERIC LANGUAGE plpgsql AS $$
DECLARE
    current_stock NUMERIC;
BEGIN
    SELECT quantity INTO current_stock FROM "Product" WHERE id = p_id FOR UPDATE;
    
    IF current_stock IS NULL THEN
        RAISE EXCEPTION 'Product % not found', p_id;
    END IF;
    
    IF current_stock < p_quantity THEN
        RAISE EXCEPTION 'Oversell guard: available %, requested %', current_stock, p_quantity;
    END IF;
    
    UPDATE "Product" 
    SET quantity = quantity - p_quantity, "updatedAt" = NOW() 
    WHERE id = p_id;
    
    RETURN current_stock - p_quantity;
END $$;