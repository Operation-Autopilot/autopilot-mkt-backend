#!/usr/bin/env python3
"""Upload generated 3D models to Supabase storage and activate them.

Reads from the local output/models/ directory and:
1. Uploads GLB to Supabase bucket robot-models
2. Uploads USDZ if present
3. Uploads poster if present
4. Creates record in robot_3d_models table
5. Activates model (updates robot_catalog)

Usage:
    python upload_models.py --all
    python upload_models.py --robot "CC1 Pro"
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = Path("output/models")
BUCKET_NAME = os.environ.get("ROBOT_MODELS_BUCKET", "robot-models")


def get_supabase_client():
    """Create Supabase client from env vars."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def get_robot_id_by_name(client, name: str) -> str | None:
    """Look up robot_catalog ID by name (exact match first, then fuzzy)."""
    # Try exact match first
    response = client.table("robot_catalog").select("id").eq("name", name).limit(1).execute()
    if response.data:
        return response.data[0]["id"]
    # Fall back to fuzzy match
    response = client.table("robot_catalog").select("id").ilike("name", f"%{name}%").limit(1).execute()
    if response.data:
        return response.data[0]["id"]
    return None


def upload_file(client, robot_id: str, version: int, filepath: Path, content_type: str) -> str:
    """Upload a file to Supabase storage and return public URL."""
    storage_path = f"robots/{robot_id}/v{version}/{filepath.name}"
    file_bytes = filepath.read_bytes()

    logger.info(f"  Uploading {filepath.name} ({len(file_bytes) / 1024:.1f} KB)...")
    client.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    public_url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    logger.info(f"  URL: {public_url}")
    return public_url


def upload_robot_model(client, robot_name: str, robot_dir: Path) -> dict:
    """Upload all model files for a single robot."""
    robot_id = get_robot_id_by_name(client, robot_name)
    if not robot_id:
        logger.error(f"  Robot '{robot_name}' not found in catalog")
        return {"robot_name": robot_name, "status": "not_found"}

    glb_path = robot_dir / "model.glb"
    if not glb_path.exists():
        logger.error(f"  No model.glb found in {robot_dir}")
        return {"robot_name": robot_name, "status": "no_model"}

    # Get next version
    response = (
        client.table("robot_3d_models")
        .select("version")
        .eq("robot_id", robot_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    version = (response.data[0]["version"] + 1) if response.data else 1

    logger.info(f"  Uploading as version {version}...")

    # Upload GLB
    glb_url = upload_file(client, robot_id, version, glb_path, "model/gltf-binary")
    glb_size = glb_path.stat().st_size

    # Upload USDZ if present
    usdz_path = robot_dir / "model.usdz"
    usdz_url = None
    if usdz_path.exists():
        usdz_url = upload_file(client, robot_id, version, usdz_path, "model/vnd.usdz+zip")

    # Upload poster if present
    poster_path = robot_dir / "poster.webp"
    poster_url = None
    if poster_path.exists():
        poster_url = upload_file(client, robot_id, version, poster_path, "image/webp")

    # Load generation report for metadata
    report_path = MODELS_DIR / "generation_report.json"
    gen_params = {}
    vertex_count = None
    quality_score = None
    source_urls = []

    if report_path.exists():
        report = json.loads(report_path.read_text())
        for entry in report:
            if entry.get("robot_name") == robot_name and entry.get("status") == "completed":
                gen_params = entry.get("generation_params", {})
                vertex_count = entry.get("vertex_count")
                source_urls = [entry.get("source_image", "")]
                break

    # Create record in robot_3d_models
    record = {
        "robot_id": robot_id,
        "version": version,
        "source_image_urls": source_urls,
        "pipeline_version": gen_params.get("pipeline_version", "hunyuan3d-2.1"),
        "glb_url": glb_url,
        "usdz_url": usdz_url,
        "glb_file_size_bytes": glb_size,
        "vertex_count": vertex_count,
        "generation_params": gen_params,
        "quality_score": quality_score,
        "status": "completed",
        "is_active": False,
    }

    response = client.table("robot_3d_models").insert(record).execute()
    model_id = response.data[0]["id"]
    logger.info(f"  Created model record: {model_id}")

    # Deactivate previous models
    client.table("robot_3d_models").update({"is_active": False}).eq("robot_id", robot_id).execute()

    # Activate this model
    client.table("robot_3d_models").update({"is_active": True}).eq("id", model_id).execute()

    # Update robot_catalog
    catalog_update = {
        "model_glb_url": glb_url,
        "model_usdz_url": usdz_url,
        "model_poster_url": poster_url,
        "has_3d_model": True,
    }
    client.table("robot_catalog").update(catalog_update).eq("id", robot_id).execute()
    logger.info(f"  Robot catalog updated. 3D model is now active!")

    return {
        "robot_name": robot_name,
        "robot_id": robot_id,
        "version": version,
        "model_id": model_id,
        "glb_url": glb_url,
        "usdz_url": usdz_url,
        "poster_url": poster_url,
        "status": "uploaded",
    }


def main():
    parser = argparse.ArgumentParser(description="Upload 3D models to Supabase")
    parser.add_argument("--robot", help="Upload for a specific robot")
    parser.add_argument("--all", action="store_true", help="Upload all generated models")
    args = parser.parse_args()

    if not args.robot and not args.all:
        parser.error("Specify --robot <name> or --all")

    if not MODELS_DIR.exists():
        logger.error(f"Models directory not found: {MODELS_DIR}")
        logger.error("Run generate_3d.py first.")
        sys.exit(1)

    client = get_supabase_client()

    # Find robot directories with generated models
    if args.robot:
        robot_name = args.robot
        robot_dir = MODELS_DIR / robot_name.replace(" ", "_").lower()
        if not robot_dir.exists():
            logger.error(f"No generated model found for '{robot_name}'")
            sys.exit(1)
        robots_to_upload = [(robot_name, robot_dir)]
    else:
        robots_to_upload = []
        # Load generation report to get robot names
        report_path = MODELS_DIR / "generation_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            for entry in report:
                if entry.get("status") == "completed":
                    name = entry["robot_name"]
                    rdir = MODELS_DIR / name.replace(" ", "_").lower()
                    if rdir.exists():
                        robots_to_upload.append((name, rdir))
        else:
            # Discover from directory structure
            for rdir in sorted(MODELS_DIR.iterdir()):
                if rdir.is_dir() and (rdir / "model.glb").exists():
                    robots_to_upload.append((rdir.name.replace("_", " ").title(), rdir))

    logger.info(f"Uploading {len(robots_to_upload)} model(s)...")

    results = []
    for robot_name, robot_dir in robots_to_upload:
        logger.info(f"\n{'='*60}")
        logger.info(f"Robot: {robot_name}")
        logger.info(f"{'='*60}")
        result = upload_robot_model(client, robot_name, robot_dir)
        results.append(result)

    # Summary
    uploaded = sum(1 for r in results if r["status"] == "uploaded")
    failed = len(results) - uploaded
    print(f"\n{'='*60}")
    print(f"UPLOAD COMPLETE: {uploaded} uploaded, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
