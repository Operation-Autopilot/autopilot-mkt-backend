#!/usr/bin/env python3
"""Enhance robot product images for better 3D generation quality.

Preprocessing pipeline:
1. Background removal using rembg
2. Optional upscaling for small images
3. Save enhanced versions and optionally upload to Supabase

Usage:
    python enhance_images.py
    python enhance_images.py --robot "CC1 Pro"
    python enhance_images.py --skip-upload
"""

import argparse
import json
import logging
import os
import sys
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image
from rembg import remove
from supabase import create_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/enhanced")
MIN_SIZE = 512


def get_supabase_client():
    """Create Supabase client from env vars."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def download_image(url: str) -> Image.Image | None:
    """Download image from URL."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None


def remove_background(img: Image.Image) -> Image.Image:
    """Remove background from image using rembg."""
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    result = remove(img_bytes.getvalue())
    return Image.open(BytesIO(result))


def upscale_if_needed(img: Image.Image, min_size: int = MIN_SIZE) -> Image.Image:
    """Upscale image if below minimum size using Lanczos resampling."""
    w, h = img.size
    if min(w, h) >= min_size:
        return img

    scale = min_size / min(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    logger.info(f"  Upscaling from {w}x{h} to {new_w}x{new_h}")
    return img.resize((new_w, new_h), Image.LANCZOS)


def enhance_robot_images(robot: dict, output_dir: Path, skip_upload: bool = False):
    """Enhance all images for a single robot."""
    image_urls = robot.get("image_url", "")
    if not image_urls:
        logger.warning(f"No images for {robot['name']}")
        return []

    urls = [u.strip() for u in image_urls.split(",") if u.strip()]
    robot_dir = output_dir / robot["name"].replace(" ", "_").lower()
    robot_dir.mkdir(parents=True, exist_ok=True)

    enhanced = []
    for i, url in enumerate(urls):
        logger.info(f"  Processing image {i+1}/{len(urls)}: {url[:80]}...")
        img = download_image(url)
        if img is None:
            continue

        # Convert to RGBA for transparency support
        img = img.convert("RGBA")

        # Remove background
        logger.info(f"    Removing background...")
        img_nobg = remove_background(img)

        # Upscale if needed
        img_nobg = upscale_if_needed(img_nobg)

        # Save
        filename = f"enhanced_{i+1}.png"
        filepath = robot_dir / filename
        img_nobg.save(filepath, "PNG")
        logger.info(f"    Saved: {filepath}")

        enhanced.append({
            "original_url": url,
            "enhanced_path": str(filepath),
            "size": img_nobg.size,
        })

    return enhanced


def main():
    parser = argparse.ArgumentParser(description="Enhance robot images for 3D generation")
    parser.add_argument("--robot", help="Process a specific robot by name")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to Supabase")
    parser.add_argument("--output-dir", default="output/enhanced", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = get_supabase_client()

    # Fetch robots
    query = client.table("robot_catalog").select("id, name, image_url").eq("active", True)
    if args.robot:
        query = query.ilike("name", f"%{args.robot}%")
    response = query.execute()

    robots = response.data or []
    if not robots:
        logger.error("No robots found")
        sys.exit(1)

    logger.info(f"Enhancing images for {len(robots)} robot(s)...")

    results = {}
    for robot in robots:
        logger.info(f"Processing: {robot['name']}")
        enhanced = enhance_robot_images(robot, output_dir, args.skip_upload)
        results[robot["name"]] = {
            "robot_id": robot["id"],
            "enhanced_count": len(enhanced),
            "images": enhanced,
        }

    # Save results
    report_path = output_dir / "enhancement_report.json"
    report_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Report saved to {report_path}")

    total = sum(r["enhanced_count"] for r in results.values())
    print(f"\nEnhanced {total} images across {len(results)} robots.")


if __name__ == "__main__":
    main()
