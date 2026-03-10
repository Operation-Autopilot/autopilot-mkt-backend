-- Migration 014: Add Gynger financing columns to orders table
--
-- Adds:
--   gynger_application_id  — Gynger's application reference ID (set when user applies for financing)
--   payment_provider       — Which payment provider was used: 'stripe' (default) | 'gynger'

ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS gynger_application_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(50) DEFAULT 'stripe';

-- Index for looking up orders by Gynger application ID (used in webhook handler)
CREATE INDEX IF NOT EXISTS idx_orders_gynger_application_id
  ON orders (gynger_application_id)
  WHERE gynger_application_id IS NOT NULL;

COMMENT ON COLUMN orders.gynger_application_id IS 'Gynger financing application ID, set when payment_provider = ''gynger''';
COMMENT ON COLUMN orders.payment_provider IS 'Payment provider used for this order: ''stripe'' or ''gynger''';
