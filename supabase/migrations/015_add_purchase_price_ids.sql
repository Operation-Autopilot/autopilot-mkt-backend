-- Add Stripe purchase price IDs to robot_catalog for one-time purchase support
-- (purchase_price column already exists but had no corresponding Stripe price IDs)

ALTER TABLE robot_catalog
    ADD COLUMN IF NOT EXISTS stripe_purchase_price_id VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS stripe_purchase_price_id_test VARCHAR(255) NOT NULL DEFAULT '';

-- Add payment_type to orders to distinguish lease vs purchase
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) NOT NULL DEFAULT 'lease';
