-- 023_add_test_robot.sql
-- Adds a $0.01 penny robot for end-to-end Stripe checkout testing.
-- Stripe price IDs can be updated later via robot_catalog UPDATE once created.

INSERT INTO robot_catalog (
  sku,
  name,
  manufacturer,
  category,
  best_for,
  modes,
  surfaces,
  monthly_lease,
  purchase_price,
  time_efficiency,
  key_reasons,
  specs,
  active
) VALUES (
  'TEST-PENNY-2025-001',
  'Penny Test Bot',
  'Autopilot',
  'Test',
  'End-to-end Stripe checkout testing at $0.01',
  ARRAY['Test'],
  ARRAY['Test'],
  0.01,
  0.01,
  0.80,
  ARRAY['$0.01 lease and purchase for Stripe penny testing'],
  ARRAY['Monthly lease: $0.01', 'Purchase price: $0.01'],
  true
);
