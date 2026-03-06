-- Migration: seed T300 and T600 transport SKUs
-- These two SKUs were missing from 006_create_robot_catalog.sql

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
    image_url,
    stripe_product_id,
    stripe_lease_price_id,
    stripe_product_id_test,
    stripe_lease_price_id_test,
    active
)
VALUES
(
    'PUDU-T300-2025-001',
    'T300',
    'Pudu',
    'Material Movement AMR',
    'Manufacturing, back-of-house logistics (automated material transport)',
    ARRAY['Transport'],
    ARRAY['Concrete'],
    3000.00,
    60000.00,
    1.0,
    ARRAY[
        '300kg payload capacity',
        'LiDAR + VSLAM navigation',
        '8h runtime — longest in catalog',
        'Designed for industrial logistics workflows'
    ],
    ARRAY[
        '300kg payload',
        '8h runtime',
        'LiDAR + VSLAM',
        '60cm min aisle width',
        'Auto-docking'
    ],
    '/PUDU-T300-1.jpg',
    '',
    '',
    '',
    '',
    true
),
(
    'PUDU-T600-2025-001',
    'T600',
    'Pudu',
    'Heavy Payload AMR',
    'Heavy manufacturing, warehouse (high-capacity material transport)',
    ARRAY['Transport'],
    ARRAY['Concrete'],
    4000.00,
    80000.00,
    1.0,
    ARRAY[
        '600kg payload capacity — highest in catalog',
        'LiDAR + VSLAM navigation',
        '6-12h runtime',
        'Compatible with robotic arm attachment'
    ],
    ARRAY[
        '600kg payload',
        '6-12h runtime',
        'LiDAR + VSLAM',
        '70cm min aisle width',
        'Auto-docking'
    ],
    '/Pudu-T600-1.webp',
    '',
    '',
    '',
    '',
    true
)
ON CONFLICT (sku) DO UPDATE SET
    name            = EXCLUDED.name,
    manufacturer    = EXCLUDED.manufacturer,
    category        = EXCLUDED.category,
    best_for        = EXCLUDED.best_for,
    modes           = EXCLUDED.modes,
    surfaces        = EXCLUDED.surfaces,
    purchase_price  = EXCLUDED.purchase_price,
    time_efficiency = EXCLUDED.time_efficiency,
    key_reasons     = EXCLUDED.key_reasons,
    specs           = EXCLUDED.specs,
    image_url       = EXCLUDED.image_url,
    active          = EXCLUDED.active,
    updated_at      = NOW();

-- Ensure all 13 canonical SKUs are active
UPDATE robot_catalog
SET active = true, updated_at = NOW()
WHERE sku IN (
    'PUDU-CC1PRO-2025-001',
    'PUDU-CC1-2025-001',
    'PUDU-MT1-2025-001',
    'AVID-NEO2W-2025-001',
    'AVID-KAS-2025-001',
    'TENN-T7AMR-2025-001',
    'TENN-T380AMR-2025-001',
    'GAUS-PHANTAS-2025-001',
    'GAUS-V40-2025-001',
    'KEEN-C40-2025-001',
    'KEEN-C30-2025-001',
    'PUDU-T300-2025-001',
    'PUDU-T600-2025-001'
)
AND active = false;
