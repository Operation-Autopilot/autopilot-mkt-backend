#!/usr/bin/env python3
"""Assess robot product images for 3D generation suitability.

Evaluates resolution, blur, background complexity, and available angles
for each robot in the catalog. Outputs a JSON report with per-robot
assessments and best candidate image selection.

Usage:
    python assess_images.py
    python assess_images.py --robot "CC1 Pro"
    python assess_images.py --output output/image_assessment.json
"""

import argparse
import json
import logging
import os
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Minimum requirements for 3D generation
MIN_RESOLUTION = 512
IDEAL_RESOLUTION = 1024


def get_supabase_client():
    """Create Supabase client from env vars."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def download_image(url: str) -> Image.Image | None:
    """Download image from URL and return PIL Image."""
    import requests

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None


def assess_resolution(img: Image.Image) -> dict:
    """Assess image resolution."""
    w, h = img.size
    min_dim = min(w, h)
    score = min(1.0, min_dim / IDEAL_RESOLUTION)
    return {
        "width": w,
        "height": h,
        "min_dimension": min_dim,
        "meets_minimum": min_dim >= MIN_RESOLUTION,
        "score": round(score, 2),
    }


def assess_blur(img: Image.Image) -> dict:
    """Assess image sharpness using Laplacian variance."""
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float64)

    # Laplacian kernel
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    from scipy.signal import convolve2d

    laplacian = convolve2d(arr, kernel, mode="valid")
    variance = float(np.var(laplacian))

    # Thresholds: < 100 = very blurry, 100-500 = acceptable, > 500 = sharp
    if variance > 500:
        score = 1.0
    elif variance > 100:
        score = 0.5 + 0.5 * (variance - 100) / 400
    else:
        score = variance / 200

    return {
        "laplacian_variance": round(variance, 1),
        "is_blurry": variance < 100,
        "score": round(min(1.0, score), 2),
    }


def assess_background(img: Image.Image) -> dict:
    """Assess background complexity (simpler = better for 3D gen)."""
    # Convert to small thumbnail for fast analysis
    thumb = img.copy()
    thumb.thumbnail((256, 256))
    arr = np.array(thumb.convert("RGB"))

    # Check color variance in border regions (top/bottom/left/right 10%)
    h, w = arr.shape[:2]
    border = max(1, int(min(h, w) * 0.1))

    borders = np.concatenate([
        arr[:border, :].reshape(-1, 3),    # top
        arr[-border:, :].reshape(-1, 3),   # bottom
        arr[:, :border].reshape(-1, 3),    # left
        arr[:, -border:].reshape(-1, 3),   # right
    ])

    # Low variance in borders = clean background
    bg_variance = float(np.mean(np.var(borders, axis=0)))

    if bg_variance < 500:
        score = 1.0  # Very clean background
    elif bg_variance < 2000:
        score = 0.7
    elif bg_variance < 5000:
        score = 0.4
    else:
        score = 0.2

    return {
        "border_variance": round(bg_variance, 1),
        "is_clean": bg_variance < 2000,
        "score": round(score, 2),
    }


def assess_image(url: str) -> dict | None:
    """Full assessment of a single image."""
    img = download_image(url)
    if img is None:
        return None

    resolution = assess_resolution(img)
    blur = assess_blur(img)
    background = assess_background(img)

    # Overall suitability score (weighted average)
    overall = (
        resolution["score"] * 0.3
        + blur["score"] * 0.3
        + background["score"] * 0.4
    )

    return {
        "url": url,
        "format": img.format or url.rsplit(".", 1)[-1],
        "resolution": resolution,
        "blur": blur,
        "background": background,
        "overall_score": round(overall, 2),
        "suitable_for_3d": overall >= 0.5 and resolution["meets_minimum"],
    }


def assess_robot(robot: dict) -> dict:
    """Assess all images for a single robot."""
    image_urls = robot.get("image_url", "")
    if not image_urls:
        return {
            "robot_id": robot["id"],
            "robot_name": robot["name"],
            "image_count": 0,
            "images": [],
            "best_candidate": None,
            "needs_more_images": True,
            "recommendation": "No images available. Source product photos first.",
        }

    urls = [u.strip() for u in image_urls.split(",") if u.strip()]
    assessments = []
    for url in urls:
        result = assess_image(url)
        if result:
            assessments.append(result)

    # Sort by overall score
    assessments.sort(key=lambda x: x["overall_score"], reverse=True)
    best = assessments[0] if assessments else None
    suitable_count = sum(1 for a in assessments if a["suitable_for_3d"])

    needs_more = len(assessments) < 3

    if not best or not best["suitable_for_3d"]:
        recommendation = "Images are low quality. Source higher-resolution product photos."
    elif needs_more:
        recommendation = f"Only {len(assessments)} image(s). Add more angles (front, side, 3/4) for better results."
    else:
        recommendation = "Ready for 3D generation."

    return {
        "robot_id": robot["id"],
        "robot_name": robot["name"],
        "image_count": len(assessments),
        "suitable_count": suitable_count,
        "images": assessments,
        "best_candidate": best,
        "needs_more_images": needs_more,
        "recommendation": recommendation,
    }


def main():
    parser = argparse.ArgumentParser(description="Assess robot images for 3D generation")
    parser.add_argument("--robot", help="Assess a specific robot by name")
    parser.add_argument("--output", default="output/image_assessment.json", help="Output JSON path")
    args = parser.parse_args()

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

    logger.info(f"Assessing {len(robots)} robot(s)...")

    results = []
    for robot in robots:
        logger.info(f"  Assessing: {robot['name']}")
        result = assess_robot(robot)
        results.append(result)

    # Summary
    ready = sum(1 for r in results if not r["needs_more_images"] and r.get("suitable_count", 0) > 0)
    needs_images = sum(1 for r in results if r["needs_more_images"])

    report = {
        "total_robots": len(results),
        "ready_for_generation": ready,
        "needs_more_images": needs_images,
        "robots": results,
    }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    logger.info(f"Report saved to {output_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"IMAGE ASSESSMENT SUMMARY")
    print(f"{'='*60}")
    print(f"Total robots: {len(results)}")
    print(f"Ready for 3D: {ready}")
    print(f"Need more images: {needs_images}")
    print(f"{'='*60}")
    for r in results:
        status = "✓" if not r["needs_more_images"] and r.get("suitable_count", 0) > 0 else "✗"
        print(f"  {status} {r['robot_name']}: {r['image_count']} images, {r.get('suitable_count', 0)} suitable")
        print(f"    → {r['recommendation']}")


if __name__ == "__main__":
    main()
