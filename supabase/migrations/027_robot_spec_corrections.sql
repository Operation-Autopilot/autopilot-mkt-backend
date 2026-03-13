-- 027_robot_spec_corrections.sql
-- Fix verified spec inaccuracies across robot_catalog.
-- Sources: gausium.com/specs/, pudurobotics.com, keenon.com (March 2026)
--
-- Also fixes 3 frontend parser bugs:
--   Omnie/Vacuum 40: runtime format "Xh active / Yh standby runtime" broke extractRuntimeFromSpecs regex
--   C20: comma in "~2,000 m²/charge" broke extractCoverageRate regex (parsed as 2 m²)
--
-- Corrections:
--   Beetle:     runtime 4-8h → 5h (Pro/60Ah variant; official max 5h)
--   Omnie:      runtime "8h standby" → "8h sweeping" (active mode, not standby); parser-safe format
--   Vacuum 40:  runtime "18h standby" → "18h mopping" (active mode); battery "Lithium-ion" → LiFePO₄ 60Ah
--   Scrubber 50: navigation "3D LiDAR" → "2D LiDAR" (per gausium.com/specs/scrubber50)
--   Phantas:    min aisle "52-60cm" → "55-60cm" (550mm via OTA / 600mm standard)
--   T300:       runtime "8h" → "6-12h" (6h loaded / 12h unloaded)
--   C30:        add Dust Mop mode (officially 3-in-1: Sweep/Vacuum/Dust Mop)
--   C55:        mode "Sweep" → "Squeegee" (per keenon.com/product/C55)
--   MT1 Vac:    add Dust Mop mode (per pudurobotics.com/products/mt1-vac)
--   C20:        coverage "~2,000 m²/charge" → "~400 m²/h" (consistent metric, fixes parser bug)
--
-- Also inserts Keenon DinerBot T10 (inactive hospitality delivery robot).

-- 1. Beetle: runtime 4–8h → 5h (Pro/60Ah variant)
UPDATE robot_catalog SET
  specs = ARRAY[
    '750mm cleaning path',
    '~3240 m²/h coverage',
    '5h runtime',
    '60Ah LFP battery',
    '3D LiDAR + RGB + depth camera'
  ],
  updated_at = NOW()
WHERE name = 'Beetle';

-- 2. Omnie: "3h active / 8h standby runtime" → parser-safe; 8h is sweeping, not standby
UPDATE robot_catalog SET
  specs = ARRAY[
    '780mm cleaning width',
    '2621 m²/h coverage',
    '3h runtime (scrubbing)',
    '8h sweeping',
    '33L clean / 24L waste tanks',
    '800mm min aisle width',
    'Dual roller brush system',
    '3D LiDAR + 360° vision',
    'Multimodal SLAM navigation',
    'Auto-docking with water management'
  ],
  updated_at = NOW()
WHERE name = 'Omnie';

-- 3. Vacuum 40: "3h active / 18h standby" → parser-safe; battery → LiFePO₄ 60Ah
UPDATE robot_catalog SET
  specs = ARRAY[
    '400-800 m²/h practical coverage',
    '3h runtime (vacuuming)',
    '18h mopping',
    'H13 HEPA filter',
    'LiFePO₄ 60Ah battery',
    '800mm min aisle width',
    'Auto-charging'
  ],
  updated_at = NOW()
WHERE name = 'Vacuum 40';

-- 4. Scrubber 50: 3D LiDAR → 2D LiDAR
UPDATE robot_catalog SET
  specs = ARRAY[
    '460mm cleaning width',
    '500-1300 m²/h practical coverage',
    '3h runtime',
    '30L clean / 24L waste tanks',
    '800mm min aisle width',
    '2D LiDAR navigation',
    'Auto-docking with water management'
  ],
  updated_at = NOW()
WHERE name = 'Scrubber 50';

-- 5. Phantas: min aisle 52-60cm → 55-60cm (550mm OTA / 600mm standard)
UPDATE robot_catalog SET
  specs = ARRAY[
    '350-700 m²/h coverage',
    '4-4.5h runtime',
    'LiFePO₄ battery',
    '55-60cm min aisle width',
    'Auto-docking'
  ],
  updated_at = NOW()
WHERE name = 'Phantas';

-- 6. T300: runtime 8h → 6-12h (load-dependent)
UPDATE robot_catalog SET
  specs = ARRAY[
    '300kg payload',
    '6-12h runtime',
    'LiDAR + VSLAM',
    '60cm min aisle width',
    'Auto-docking'
  ],
  updated_at = NOW()
WHERE name = 'T300';

-- 7. C30: add Dust Mop (officially 3-in-1: Sweep/Vacuum/Dust Mop)
UPDATE robot_catalog SET
  modes = ARRAY['Vacuum', 'Sweep', 'Dust Mop'],
  updated_at = NOW()
WHERE name = 'Kleenbot C30';

-- 8. C55: Sweep → Squeegee (per keenon.com)
UPDATE robot_catalog SET
  modes = ARRAY['Scrub', 'Vacuum', 'Squeegee'],
  updated_at = NOW()
WHERE name = 'Kleenbot C55';

-- 9. MT1 Vac: add Dust Mop mode
UPDATE robot_catalog SET
  modes = ARRAY['Vacuum', 'Sweep', 'Dust Mop'],
  updated_at = NOW()
WHERE name = 'MT1 Vac';

-- 10. C20: "~2,000 m²/charge" → "~400 m²/h" (fixes parser bug + consistent metric)
UPDATE robot_catalog SET
  specs = ARRAY[
    '450mm sweep / 285mm scrub width',
    '~400 m²/h coverage',
    '7L clean / 5L waste tank',
    'LiDAR + Vision navigation',
    'Auto-charging dock'
  ],
  updated_at = NOW()
WHERE name = 'Kleenbot C20';

-- 11. INSERT Keenon DinerBot T10 (inactive hospitality delivery robot)
INSERT INTO robot_catalog (
  sku, name, manufacturer, category, best_for,
  modes, surfaces, monthly_lease, purchase_price, time_efficiency,
  key_reasons, specs, active
) VALUES (
  'KEEN-T10-2025-001',
  'DinerBot T10',
  'Keenon',
  'Hospitality Delivery Robot',
  'Restaurants, hotels, retail (food delivery, greeting, advertising)',
  ARRAY['Delivery'],
  ARRAY['Indoor flat surfaces'],
  520.00,
  13000.00,
  0.80,
  ARRAY[
    '4-tray 40kg payload for multi-table delivery',
    '9-12.5h runtime — full shift coverage',
    'LiDAR + VSLAM + stereo vision navigation',
    'Dual displays: 11.6" control + 23.8" advertising'
  ],
  ARRAY[
    '40kg payload (4 trays, 10kg each)',
    '9-12.5h runtime',
    'LiFePO₄ 28.5Ah battery',
    '58.5cm min passage width',
    'LiDAR + VSLAM + 4 stereo vision cameras',
    '0.1-1.0 m/s adjustable speed'
  ],
  false
);
