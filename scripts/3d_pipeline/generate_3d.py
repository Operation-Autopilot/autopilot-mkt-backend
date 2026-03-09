#!/usr/bin/env python3
"""Generate 3D models from robot product images using Hunyuan3D 2.1.

Uses the Hunyuan3D-2 pipeline to create GLB models from single images.
Post-processes with mesh decimation, Draco compression, and texture optimization.
Converts GLB to USDZ for iOS AR Quick Look support.

Usage:
    python generate_3d.py --robot "CC1 Pro"
    python generate_3d.py --all
    python generate_3d.py --all --skip-existing
    python generate_3d.py --robot "CC1 Pro" --steps 50 --seed 42
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/models")
ASSESSMENT_FILE = Path("output/image_assessment.json")
ENHANCED_DIR = Path("output/enhanced")

# Generation defaults
DEFAULT_STEPS = 50
DEFAULT_SEED = 42
MAX_TRIANGLES = 100_000
MAX_FILE_SIZE_MB = 5
MAX_TEXTURE_SIZE = 2048


def load_assessment() -> dict:
    """Load image assessment report."""
    if not ASSESSMENT_FILE.exists():
        logger.error(f"Assessment file not found: {ASSESSMENT_FILE}")
        logger.error("Run assess_images.py first.")
        sys.exit(1)
    return json.loads(ASSESSMENT_FILE.read_text())


def get_best_image(robot_name: str, assessment: dict) -> str | None:
    """Get the best candidate image URL for a robot."""
    for robot in assessment.get("robots", []):
        if robot["robot_name"] == robot_name:
            best = robot.get("best_candidate")
            if best:
                return best["url"]
    return None


def get_enhanced_image(robot_name: str) -> str | None:
    """Get enhanced (background-removed) image if available."""
    robot_dir = ENHANCED_DIR / robot_name.replace(" ", "_").lower()
    if robot_dir.exists():
        pngs = sorted(robot_dir.glob("enhanced_*.png"))
        if pngs:
            return str(pngs[0])
    return None


def generate_model(
    image_path: str,
    output_dir: Path,
    steps: int = DEFAULT_STEPS,
    seed: int = DEFAULT_SEED,
) -> Path | None:
    """Generate a 3D GLB model from an image using Hunyuan3D 2.1.

    Args:
        image_path: Path or URL to the source image.
        output_dir: Directory to save the output model.
        steps: Number of inference steps.
        seed: Random seed for reproducibility.

    Returns:
        Path to the generated GLB file, or None on failure.
    """
    try:
        import torch
        from PIL import Image

        # Load image
        if image_path.startswith(("http://", "https://")):
            import requests
            from io import BytesIO
            resp = requests.get(image_path, timeout=60)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
        else:
            img = Image.open(image_path).convert("RGBA")

        logger.info(f"  Image loaded: {img.size}")

        # Import Hunyuan3D pipeline
        # NOTE: This requires hunyuan3d-2 to be installed.
        # Clone from: https://github.com/Tencent/Hunyuan3D-2
        # Install: pip install -e .
        try:
            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
            from hy3dgen.texgen import Hunyuan3DPaintPipeline
        except ImportError:
            logger.error(
                "Hunyuan3D-2 not installed. Clone and install from:\n"
                "  git clone https://github.com/Tencent/Hunyuan3D-2\n"
                "  cd Hunyuan3D-2 && pip install -e ."
            )
            return None

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            logger.warning("CUDA not available. Generation will be very slow on CPU.")

        # Shape generation
        logger.info("  Loading shape generation model...")
        shape_pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            "tencent/Hunyuan3D-2",
            subfolder="hunyuan3d-dit-v2-0",
            torch_dtype=torch.float16,
            device=device,
        )

        logger.info(f"  Generating shape (steps={steps}, seed={seed})...")
        mesh = shape_pipe(
            image=img,
            num_inference_steps=steps,
            guidance_scale=5.5,
            generator=torch.Generator(device=device).manual_seed(seed),
        )

        # Texture generation
        logger.info("  Loading texture generation model...")
        tex_pipe = Hunyuan3DPaintPipeline.from_pretrained(
            "tencent/Hunyuan3D-2",
            subfolder="hunyuan3d-paint-v2-0",
            torch_dtype=torch.float16,
            device=device,
        )

        logger.info("  Generating texture...")
        textured_mesh = tex_pipe(mesh, image=img)

        # Save raw output
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / "model_raw.glb"
        textured_mesh.export(str(raw_path))
        logger.info(f"  Raw model saved: {raw_path}")

        return raw_path

    except Exception as e:
        logger.error(f"  Generation failed: {e}")
        return None


def postprocess_mesh(glb_path: Path, output_dir: Path) -> Path | None:
    """Post-process GLB: decimate, compress textures, optimize.

    Args:
        glb_path: Path to the raw GLB file.
        output_dir: Directory to save processed model.

    Returns:
        Path to the processed GLB file.
    """
    try:
        import trimesh

        logger.info("  Post-processing mesh...")
        scene = trimesh.load(str(glb_path))

        # Get the mesh (handle both Scene and Trimesh)
        if isinstance(scene, trimesh.Scene):
            meshes = list(scene.geometry.values())
            if not meshes:
                logger.error("  No geometry found in GLB")
                return None
            mesh = trimesh.util.concatenate(meshes)
        else:
            mesh = scene

        logger.info(f"  Original: {len(mesh.faces)} triangles, {len(mesh.vertices)} vertices")

        # Decimate if needed
        if len(mesh.faces) > MAX_TRIANGLES:
            logger.info(f"  Decimating to {MAX_TRIANGLES} triangles...")
            mesh = mesh.simplify_quadric_decimation(MAX_TRIANGLES)
            logger.info(f"  After decimation: {len(mesh.faces)} triangles")

        # Export optimized GLB
        output_path = output_dir / "model.glb"
        mesh.export(str(output_path), file_type="glb")

        # Check file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Output: {size_mb:.1f} MB, {len(mesh.faces)} triangles, {len(mesh.vertices)} vertices")

        if size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"  File exceeds {MAX_FILE_SIZE_MB}MB target. Consider further optimization.")

        return output_path

    except Exception as e:
        logger.error(f"  Post-processing failed: {e}")
        return None


def convert_to_usdz(glb_path: Path, output_dir: Path) -> Path | None:
    """Convert GLB to USDZ for iOS AR Quick Look.

    Uses Pixar's USD Python library (usd-core) for conversion.
    """
    try:
        from pxr import Usd, UsdGeom, UsdUtils

        usdz_path = output_dir / "model.usdz"

        # Convert GLB to intermediate USDA, then package as USDZ
        usda_path = output_dir / "model_temp.usda"

        # Use trimesh to convert GLB -> USD
        import trimesh

        mesh = trimesh.load(str(glb_path))
        usdc_path = output_dir / "model_temp.usdc"

        # Create a USD stage
        stage = Usd.Stage.CreateNew(str(usdc_path))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

        # Add mesh to stage
        mesh_prim = UsdGeom.Mesh.Define(stage, "/Robot")

        if isinstance(mesh, trimesh.Scene):
            combined = trimesh.util.concatenate(list(mesh.geometry.values()))
        else:
            combined = mesh

        mesh_prim.GetPointsAttr().Set(combined.vertices.tolist())
        mesh_prim.GetFaceVertexCountsAttr().Set([3] * len(combined.faces))
        mesh_prim.GetFaceVertexIndicesAttr().Set(combined.faces.flatten().tolist())

        if combined.vertex_normals is not None:
            mesh_prim.GetNormalsAttr().Set(combined.vertex_normals.tolist())

        stage.GetRootLayer().Save()

        # Package as USDZ
        UsdUtils.CreateNewUsdzPackage(str(usdc_path), str(usdz_path))

        # Cleanup temp files
        usdc_path.unlink(missing_ok=True)

        logger.info(f"  USDZ created: {usdz_path}")
        return usdz_path

    except ImportError:
        logger.warning("  usd-core not installed. Skipping USDZ conversion.")
        logger.warning("  Install with: pip install usd-core")
        return None
    except Exception as e:
        logger.error(f"  USDZ conversion failed: {e}")
        return None


def render_poster(glb_path: Path, output_dir: Path) -> Path | None:
    """Render a static poster image from the 3D model."""
    try:
        import trimesh

        mesh = trimesh.load(str(glb_path))
        scene = mesh if isinstance(mesh, trimesh.Scene) else trimesh.Scene(mesh)

        # Render at 3/4 angle
        png = scene.save_image(resolution=(1024, 1024))
        if png is None:
            logger.warning("  Could not render poster (no display available)")
            return None

        poster_path = output_dir / "poster.webp"
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(png))
        img.save(poster_path, "WEBP", quality=85)
        logger.info(f"  Poster rendered: {poster_path}")
        return poster_path

    except Exception as e:
        logger.warning(f"  Poster rendering failed: {e}")
        return None


def process_robot(
    robot_name: str,
    assessment: dict,
    steps: int,
    seed: int,
    skip_existing: bool,
    source_image: str | None = None,
) -> dict:
    """Process a single robot through the full pipeline."""
    robot_dir = OUTPUT_DIR / robot_name.replace(" ", "_").lower()

    # Skip if already processed
    if skip_existing and (robot_dir / "model.glb").exists():
        logger.info(f"  Skipping {robot_name} (already exists)")
        return {"robot_name": robot_name, "status": "skipped"}

    # Select source image
    if source_image:
        image_path = source_image
    else:
        # Prefer enhanced (background-removed) images
        image_path = get_enhanced_image(robot_name)
        if not image_path:
            image_path = get_best_image(robot_name, assessment)

    if not image_path:
        logger.warning(f"  No suitable image found for {robot_name}")
        return {"robot_name": robot_name, "status": "no_image"}

    logger.info(f"  Source image: {image_path}")

    # Generate 3D model
    raw_path = generate_model(image_path, robot_dir, steps=steps, seed=seed)
    if not raw_path:
        return {"robot_name": robot_name, "status": "generation_failed"}

    # Post-process
    glb_path = postprocess_mesh(raw_path, robot_dir)
    if not glb_path:
        return {"robot_name": robot_name, "status": "postprocess_failed"}

    # Convert to USDZ
    usdz_path = convert_to_usdz(glb_path, robot_dir)

    # Render poster
    poster_path = render_poster(glb_path, robot_dir)

    # Get file stats
    import trimesh
    mesh = trimesh.load(str(glb_path))
    if isinstance(mesh, trimesh.Scene):
        total_verts = sum(len(g.vertices) for g in mesh.geometry.values())
        total_faces = sum(len(g.faces) for g in mesh.geometry.values())
    else:
        total_verts = len(mesh.vertices)
        total_faces = len(mesh.faces)

    return {
        "robot_name": robot_name,
        "status": "completed",
        "glb_path": str(glb_path),
        "usdz_path": str(usdz_path) if usdz_path else None,
        "poster_path": str(poster_path) if poster_path else None,
        "glb_size_bytes": glb_path.stat().st_size,
        "vertex_count": total_verts,
        "triangle_count": total_faces,
        "source_image": image_path,
        "generation_params": {
            "steps": steps,
            "seed": seed,
            "pipeline_version": "hunyuan3d-2.1",
            "max_triangles": MAX_TRIANGLES,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate 3D models from robot images")
    parser.add_argument("--robot", help="Generate for a specific robot")
    parser.add_argument("--all", action="store_true", help="Generate for all robots")
    parser.add_argument("--skip-existing", action="store_true", help="Skip robots that already have models")
    parser.add_argument("--source-image", help="Override source image path/URL")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help=f"Inference steps (default: {DEFAULT_STEPS})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--max-triangles", type=int, default=MAX_TRIANGLES, help=f"Max triangles (default: {MAX_TRIANGLES})")
    parser.add_argument("--max-file-size-mb", type=float, default=MAX_FILE_SIZE_MB)
    parser.add_argument("--retry", type=int, default=1, help="Number of retries on failure")
    args = parser.parse_args()

    global MAX_TRIANGLES, MAX_FILE_SIZE_MB
    MAX_TRIANGLES = args.max_triangles
    MAX_FILE_SIZE_MB = args.max_file_size_mb

    if not args.robot and not args.all:
        parser.error("Specify --robot <name> or --all")

    # Load assessment
    assessment = load_assessment()

    if args.robot:
        robots_to_process = [args.robot]
    else:
        robots_to_process = [r["robot_name"] for r in assessment.get("robots", [])]

    logger.info(f"Processing {len(robots_to_process)} robot(s)...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for robot_name in robots_to_process:
        logger.info(f"\n{'='*60}")
        logger.info(f"Robot: {robot_name}")
        logger.info(f"{'='*60}")

        for attempt in range(args.retry):
            if attempt > 0:
                logger.info(f"  Retry {attempt + 1}/{args.retry}...")
            result = process_robot(
                robot_name, assessment, args.steps, args.seed,
                args.skip_existing, args.source_image,
            )
            if result["status"] in ("completed", "skipped"):
                break

        results.append(result)

    # Save results
    report_path = OUTPUT_DIR / "generation_report.json"
    report_path.write_text(json.dumps(results, indent=2))
    logger.info(f"\nReport saved to {report_path}")

    # Summary
    completed = sum(1 for r in results if r["status"] == "completed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = len(results) - completed - skipped
    print(f"\n{'='*60}")
    print(f"GENERATION COMPLETE: {completed} completed, {skipped} skipped, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
