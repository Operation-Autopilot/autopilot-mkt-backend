-- 022_robot_image_updates.sql
-- Robot image and catalog corrections (March 2026):
--
--   Kleenbot C30:  delete first image  (keep images 2–3)
--   Scrubber 75:   set active = false
--   Avidbots Kas:  swap image order (image 2 becomes primary, image 1 becomes second)
--   Scrubber 50:   delete first image  (keep images 2–3)
--   Gausium Omnie: delete second image (keep images 1, 3)
--   Mira:          delete third image  (keep images 1–2)
--
-- image_url is a comma-separated list of public storage URLs.
-- PostgreSQL array slicing is 1-based and inclusive on both ends.

-- 1. Kleenbot C30 — remove first image (index 1), keep remainder
UPDATE robot_catalog
SET
    image_url  = array_to_string((string_to_array(image_url, ','))[2:], ','),
    updated_at = NOW()
WHERE sku = 'KEEN-C30-2025-001';

-- 2. Scrubber 75 — mark inactive
UPDATE robot_catalog
SET
    active     = false,
    updated_at = NOW()
WHERE sku = 'GAUS-S75-2025-001';

-- 3. Avidbots Kas — swap images 1 & 2 (make current image 2 the primary hero image)
UPDATE robot_catalog
SET
    image_url  = array_to_string(
                    ARRAY[
                        (string_to_array(image_url, ','))[2],
                        (string_to_array(image_url, ','))[1]
                    ] || (string_to_array(image_url, ','))[3:],
                    ','
                 ),
    updated_at = NOW()
WHERE sku = 'AVID-KAS-2025-001';

-- 4. Scrubber 50 — remove first image (index 1), keep remainder
UPDATE robot_catalog
SET
    image_url  = array_to_string((string_to_array(image_url, ','))[2:], ','),
    updated_at = NOW()
WHERE sku = 'GAUS-S50-2025-001';

-- 5. Gausium Omnie — remove second image (keep index 1 and 3+)
UPDATE robot_catalog
SET
    image_url  = array_to_string(
                    (string_to_array(image_url, ','))[1:1]
                    || (string_to_array(image_url, ','))[3:],
                    ','
                 ),
    updated_at = NOW()
WHERE sku = 'GAUS-OMNIE-2025-001';

-- 6. Mira — remove third image (keep indices 1 and 2 only)
UPDATE robot_catalog
SET
    image_url  = array_to_string((string_to_array(image_url, ','))[1:2], ','),
    updated_at = NOW()
WHERE name = 'Mira';
