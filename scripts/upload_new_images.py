#!/usr/bin/env python3
"""Upload new robot images from ~/Downloads to Supabase Storage and update database.

Uploads images, prepends angled shots as 1st image, appends the rest to existing URLs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.supabase import get_supabase_client


STORAGE_BUCKET = "robot-images"
DOWNLOADS = Path.home() / "Downloads"

# Each robot: (robot_id, prepend_files, append_files)
# prepend_files go BEFORE existing images, append_files go AFTER
ROBOT_UPLOADS = [
    {
        "name": "Vacuum 40",
        "id": "f06a9ecd-2f57-4724-a7fd-ddf6f4b627c4",
        "prepend": ["gausium-v40.jpeg"],  # angled 3/4 shot
        "append": [
            "Gallery-Vacuum-40-2-min.jpeg",
            "Gallery-Vacuum-40-3-min.jpeg",
            "Gallery-Vacuum-40-4-min.jpeg",
            "Gallery-Vacuum-40-5-min.jpeg",
        ],
    },
    {
        "name": "Scrubber 50",
        "id": "bc0aebc9-5cd3-46c2-9c60-627a4e2b0d13",
        "prepend": ["Gallery-Scrubber-50-Pro-1-min-1.jpg"],  # angled 3/4 shot
        "append": [
            "Gallery-Scrubber-50-Pro-2-min-1.jpg",
            "Gallery-Scrubber-50-Pro-3-min-2.jpg",
            "Gallery-Scrubber-50-Pro-4-min-1.jpg",
            "Gallery-Scrubber-50-Pro-5-min-1.jpg",
            "Scrubber-50-V4.2-specs-1536x1331.png",
        ],
    },
    {
        "name": "Beetle",
        "id": "67bdf4b6-8b1b-49e1-9f9f-1cb834f1872e",
        "prepend": [],
        "append": ["Beetle-SW1-Pro_Spec-1-577x500.png"],
    },
    {
        "name": "Omnie",
        "id": "0cba0c1f-c674-4740-b1f1-4a73b576a707",
        "prepend": [],
        "append": ["OMNIE.257-1536x1331.png"],
    },
    {
        "name": "Phantas",
        "id": "14b0b9c0-9d07-4935-b4c0-6356b9b59487",
        "prepend": [],
        "append": ["Phantas-V1.3-front-spec-1536x1331.png"],
    },
]


def upload_file(client, robot_id, filename):
    """Upload a file to Supabase Storage and return its public URL."""
    file_path = DOWNLOADS / filename
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Normalize filename for storage (lowercase, no spaces)
    storage_name = filename.lower().replace(" ", "-")
    storage_path = f"robots/{robot_id}/{storage_name}"

    ext = file_path.suffix.lower()
    content_types = {".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/jpeg")

    with open(file_path, "rb") as f:
        file_data = f.read()

    client.storage.from_(STORAGE_BUCKET).upload(
        path=storage_path,
        file=file_data,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    settings = get_settings()
    return f"{settings.supabase_url}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"


def main():
    client = get_supabase_client()

    for robot in ROBOT_UPLOADS:
        name = robot["name"]
        robot_id = robot["id"]
        print(f"\n--- {name} ---")

        # Get existing image URLs
        result = client.table("robot_catalog").select("image_url").eq("id", robot_id).execute()
        existing_urls = [u.strip() for u in (result.data[0]["image_url"] or "").split(",") if u.strip()]
        print(f"  Existing: {len(existing_urls)} image(s)")

        # Upload prepend files
        prepend_urls = []
        for f in robot["prepend"]:
            print(f"  Uploading (prepend): {f}")
            url = upload_file(client, robot_id, f)
            prepend_urls.append(url)
            print(f"    -> {url}")

        # Upload append files
        append_urls = []
        for f in robot["append"]:
            print(f"  Uploading (append): {f}")
            url = upload_file(client, robot_id, f)
            append_urls.append(url)
            print(f"    -> {url}")

        # Build final URL list: prepend + existing + append
        final_urls = prepend_urls + existing_urls + append_urls
        print(f"  Final: {len(final_urls)} image(s)")

        # Update DB
        client.table("robot_catalog").update({"image_url": ",".join(final_urls)}).eq("id", robot_id).execute()
        print(f"  Updated DB")

    print("\nDone!")


if __name__ == "__main__":
    main()
