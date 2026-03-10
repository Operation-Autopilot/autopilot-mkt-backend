-- 018_data_corrections.sql
-- Correct verified data quality issues across robot_catalog.
-- Sources: avidbots.com, tennantco.com, gausium.com/specs/ (March 2026)
--
-- Corrections:
--   Neo 2W:      navigation "BrainOS" (Brain Corp/Tennant) → "Avidbots Autonomy"; runtime 3.5h → 4-6h
--   T380AMR:     runtime ~3h → up to 4-5h (verified from Tennant spec sheet)
--   Scrubber 50: cleaning width 500mm → 460mm; coverage 1,800 → 500–1,300 m²/h practical; add 3h runtime, 30L/24L tanks, 800mm aisle
--   Scrubber 75: coverage 3,000 → 700–1,400 m²/h practical; add 4-6h runtime; waste tank 75L → 50L; add 1,400mm aisle
--   Omnie:       add 2,621 m²/h coverage, 3h active/8h standby runtime, 33L/24L tanks, 800mm aisle
--   Vacuum 40:   coverage ~500 → 400–800 m²/h practical; runtime 3-4h → 3h active/18h standby; add H13 HEPA; aisle 60cm → 800mm

-- Neo 2W: BrainOS is Brain Corp technology (used by Tennant) — Avidbots uses its own Avidbots Autonomy platform
UPDATE robot_catalog SET
  key_reasons = ARRAY[
    'Industry-leading 2600 m²/h coverage',
    'Avidbots Autonomy navigation',
    'Built for 24/7 industrial environments'
  ],
  specs = ARRAY[
    '~2600 m²/h coverage',
    '4-6h runtime',
    'Lead-Acid 220Ah battery',
    '1.5m min aisle width',
    'Manual docking'
  ],
  updated_at = NOW()
WHERE sku = 'AVID-NEO2W-2025-001';

-- T380AMR: Tennant spec sheet shows up to 4-5h runtime depending on battery option
UPDATE robot_catalog SET
  specs = ARRAY[
    'Up to 3106 m²/h coverage',
    'up to 4-5h runtime',
    'Lead-Acid or Li-ion options',
    '75cm min aisle width'
  ],
  updated_at = NOW()
WHERE sku = 'TENN-T380AMR-2025-001';

-- Scrubber 50: gausium.com/specs/ confirms 460mm brush width; practical coverage 500–1,300 m²/h (not theoretical max)
UPDATE robot_catalog SET
  specs = ARRAY[
    '460mm cleaning width',
    '500–1,300 m²/h practical coverage',
    '3h runtime',
    '30L clean / 24L waste tanks',
    '800mm min aisle width',
    '3D LiDAR navigation',
    'Auto-docking with water management'
  ],
  updated_at = NOW()
WHERE sku = 'GAUS-S50-2025-001';

-- Scrubber 75: practical throughput 700–1,400 m²/h (3,000 was theoretical max); waste tank is 50L not 75L; 1,400mm aisle needed
UPDATE robot_catalog SET
  specs = ARRAY[
    '750mm cleaning width',
    '700–1,400 m²/h practical coverage',
    '4-6h runtime',
    '75L clean / 50L waste tanks',
    '1,400mm min aisle width',
    '3D LiDAR navigation',
    'Auto-docking with water management'
  ],
  updated_at = NOW()
WHERE sku = 'GAUS-S75-2025-001';

-- Omnie: add verified coverage, runtime, and tank specs from gausium.com
UPDATE robot_catalog SET
  specs = ARRAY[
    '780mm cleaning width',
    '2,621 m²/h coverage',
    '3h active / 8h standby runtime',
    '33L clean / 24L waste tanks',
    '800mm min aisle width',
    'Dual roller brush system',
    '3D LiDAR + 360° vision',
    'Multimodal SLAM navigation',
    'Auto-docking with water management'
  ],
  updated_at = NOW()
WHERE sku = 'GAUS-OMNIE-2025-001';

-- Vacuum 40: practical coverage 400–800 m²/h (not ~500 flat); 3h active / 18h standby runtime; H13 HEPA; 800mm aisle
UPDATE robot_catalog SET
  specs = ARRAY[
    '400–800 m²/h practical coverage',
    '3h active / 18h standby runtime',
    'H13 HEPA filter',
    'Lithium-ion battery',
    '800mm min aisle width',
    'Auto-charging'
  ],
  updated_at = NOW()
WHERE sku = 'GAUS-V40-2025-001';
