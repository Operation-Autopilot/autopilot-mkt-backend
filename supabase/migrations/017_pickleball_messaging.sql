-- 017_pickleball_messaging.sql
-- Prepend pickleball/sports-court messaging to CC1, CC1 Pro, C40, C30
-- Fireflies + HubSpot confirm all 4 are sold/deployed at pickleball facilities:
-- CC1/CC1 Pro: Calabasas PBC, PickleBOS, Rally House, Wenatchee RAC, etc.
-- C40/C30: Victory Pickleball ("Keenan robot order for Victory install")

-- CC1: primary pickleball sales robot
UPDATE robot_catalog SET
  best_for = 'Indoor pickleball & tennis facilities, racquet clubs, multi-court sports venues; ' || best_for,
  key_reasons = ARRAY[
    'Court-safe scrubbing: zero damage on Acrotech, hardwood & premium court surfaces',
    'Water-smart 8L system: controlled dispensing prevents over-wetting & court damage',
    '4-in-1 in one pass: sweep, vacuum, scrub & dust mop for full court maintenance'
  ] || key_reasons,
  surfaces = ARRAY[
    'Hardwood Sport Court', 'Acrotech Court', 'Sport Court Vinyl'
  ] || surfaces,
  updated_at = NOW()
WHERE sku = 'PUDU-CC1-2025-001';

-- CC1 Pro: large multi-court venue upgrade
UPDATE robot_catalog SET
  best_for = 'Large multi-court sports clubs, racquet & athletic centers; ' || best_for,
  key_reasons = ARRAY[
    'Court-proven 4-in-1: sweep, vacuum, scrub & dust mop in a single autonomous pass',
    'Precision LiDAR + Vision: navigates around nets, equipment & court lines without supervision',
    '24/7 ready with 15 min/day management — keep courts fresh before every session'
  ] || key_reasons,
  surfaces = ARRAY[
    'Hardwood Sport Court', 'Acrotech Court', 'Sport Court Vinyl'
  ] || surfaces,
  updated_at = NOW()
WHERE sku = 'PUDU-CC1PRO-2025-001';

-- C40 (Kleenbot C40): compact 4-in-1, deployed at Victory Pickleball
UPDATE robot_catalog SET
  best_for = 'Indoor pickleball & sports courts, compact multi-surface cleaning; ' || best_for,
  key_reasons = ARRAY[
    'Court-safe 4-in-1: scrub, vacuum, sweep & mop without damaging premium court surfaces',
    'Swappable battery: continuous court coverage across shifts with zero downtime',
    'Compact footprint: fits easily between courts, bleachers & lobby areas'
  ] || key_reasons,
  surfaces = ARRAY[
    'Hardwood Sport Court', 'Acrotech Court', 'Sport Court Vinyl'
  ] || surfaces,
  updated_at = NOW()
WHERE sku = 'KEEN-C40-2025-001';

-- C30 (Kleenbot C30): dry sweep & vacuum, used at Victory Pickleball
UPDATE robot_catalog SET
  best_for = 'Indoor pickleball courts & sports venues (dry sweep & vacuum); ' || best_for,
  key_reasons = ARRAY[
    'Court-safe dry cleaning: sweep & vacuum court surfaces without any moisture risk',
    '6h runtime: covers multiple courts in a single charge cycle',
    'Entry-level autonomy: easiest deployment (2/5 complexity) for first-time robot facilities'
  ] || key_reasons,
  surfaces = ARRAY[
    'Hardwood Sport Court', 'Acrotech Court', 'Sport Court Vinyl'
  ] || surfaces,
  updated_at = NOW()
WHERE sku = 'KEEN-C30-2025-001';
