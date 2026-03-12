-- Add court type surfaces (CushionX, Acrylic, Concrete) to pickleball-capable robots
-- These are standard court surface labels that complement the existing sport court surfaces from migration 017

UPDATE robot_catalog SET
  surfaces = ARRAY['CushionX', 'Acrylic', 'Concrete'] || surfaces,
  updated_at = NOW()
WHERE sku IN ('PUDU-CC1PRO-2025-001', 'PUDU-CC1-2025-001', 'KEEN-C40-2025-001', 'KEEN-C30-2025-001');
