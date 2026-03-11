-- 021_set_inactive_robots.sql
-- Mark T7AMR, T380AMR, T300, and T600 as inactive (active = false).
-- These robots will no longer be returned by the catalog API (active_only=True by default).

UPDATE robot_catalog SET active = false WHERE sku = 'TENN-T7AMR-2025-001';
UPDATE robot_catalog SET active = false WHERE sku = 'TENN-T380AMR-2025-001';
UPDATE robot_catalog SET active = false WHERE name = 'T300' AND manufacturer = 'Pudu';
UPDATE robot_catalog SET active = false WHERE name = 'T600' AND manufacturer = 'Pudu';
UPDATE robot_catalog SET active = false WHERE name = 'T16AMR';
