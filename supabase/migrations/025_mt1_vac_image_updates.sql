-- Migration 025: MT1 Vac image corrections
-- 1. Swap images 1 and 2 (make mt1-vac-2.png the hero image)
-- 2. Remove image 3 (mt1-vac-3.webp)
-- Result: [mt1-vac-2.png, mt1-vac-1.webp]

UPDATE robot_catalog
SET
    image_url = array_to_string(
        ARRAY[
            (string_to_array(image_url, ','))[2],
            (string_to_array(image_url, ','))[1]
        ],
        ','
    ),
    updated_at = NOW()
WHERE name = 'MT1 Vac';
