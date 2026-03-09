#!/usr/bin/env python3
"""Generate 3D models from robot product images using Hunyuan3D 2.1.

Uses the Hunyuan3D-2.1 pipeline for shape generation + PBR texture painting.
Runs sequentially with explicit VRAM management to fit in 12GB (3080Ti).

Usage:
    python generate_3d.py --robot "CC1 Pro"
    python generate_3d.py --all
    python generate_3d.py --all --skip-existing
    python generate_3d.py --robot "CC1 Pro" --steps 50 --seed 42
"""

import argparse
import gc
import json
import logging
import os
import sys
import time
from pathlib import Path

import types

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Apply compatibility fixes early (before any torch imports)
# 1. Mock bpy (Blender Python) — only used by convert_obj_to_glb which we skip
if 'bpy' not in sys.modules:
    sys.modules['bpy'] = types.ModuleType('bpy')

# 2. Fix torchvision.transforms.functional_tensor removal (needed by basicsr/realesrgan)
try:
    import torchvision.transforms.functional_tensor  # noqa
except (ImportError, ModuleNotFoundError):
    import torchvision.transforms.functional as _F
    _mock = types.ModuleType('torchvision.transforms.functional_tensor')
    _mock.rgb_to_grayscale = getattr(_F, 'rgb_to_grayscale', lambda x, nc=1: x)
    sys.modules['torchvision.transforms.functional_tensor'] = _mock

# Hunyuan3D-2.1 repo paths
HUNYUAN_ROOT = Path(os.environ.get(
    "HUNYUAN3D_PATH",
    "/workspace/autopilot/product/marketplace/Hunyuan3D-2.1"
))

OUTPUT_DIR = Path("output/models")
ASSESSMENT_FILE = Path("output/image_assessment.json")
ENHANCED_DIR = Path("output/enhanced")

# Generation defaults
DEFAULT_STEPS = 50
DEFAULT_SEED = 42
MAX_TRIANGLES = 100_000
MAX_FILE_SIZE_MB = 5


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


def _setup_hunyuan_paths():
    """Add Hunyuan3D-2.1 source directories to Python path."""
    shape_path = str(HUNYUAN_ROOT / "hy3dshape")
    paint_path = str(HUNYUAN_ROOT / "hy3dpaint")
    root_path = str(HUNYUAN_ROOT)
    for p in [shape_path, paint_path, root_path]:
        if p not in sys.path:
            sys.path.insert(0, p)


def generate_shape(image_path: str, output_dir: Path, steps: int, seed: int) -> Path | None:
    """Generate untextured 3D mesh using Hunyuan3D-2.1 shape pipeline.

    Loads model, generates, then explicitly frees VRAM for texture step.
    """
    import torch
    from PIL import Image
    _setup_hunyuan_paths()

    try:
        from torchvision_fix import apply_fix
        apply_fix()
    except Exception:
        pass

    from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline

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

    # Load shape generation pipeline
    logger.info("  Loading Hunyuan3D-2.1 shape generation model...")
    model_path = "tencent/Hunyuan3D-2.1"
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)

    logger.info(f"  Generating shape (steps={steps}, seed={seed})...")
    start = time.time()
    mesh = pipeline(image=img, num_inference_steps=steps, seed=seed)[0]
    elapsed = time.time() - start
    logger.info(f"  Shape generation took {elapsed:.1f}s")

    # Save raw shape GLB
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "model_shape.glb"
    mesh.export(str(raw_path))
    logger.info(f"  Raw shape saved: {raw_path}")

    # Free VRAM for texture step
    logger.info("  Unloading shape model to free VRAM...")
    del pipeline
    del mesh
    gc.collect()
    torch.cuda.empty_cache()

    return raw_path


def generate_texture(
    shape_glb_path: Path,
    image_path: str,
    output_dir: Path,
) -> Path | None:
    """Generate PBR texture for an existing mesh using Hunyuan3D-2.1 paint pipeline.

    Expects shape model to already be unloaded from VRAM.
    The paint pipeline outputs OBJ with PBR textures (albedo, metallic, roughness),
    which we then convert to GLB with proper PBR materials.
    """
    import torch
    _setup_hunyuan_paths()

    try:
        from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
        from hy3dpaint.convert_utils import create_glb_with_pbr_materials
    except ImportError as e:
        logger.error(
            f"Hunyuan3D-2.1 paint pipeline import failed: {e}\n"
            "Ensure hy3dpaint is on sys.path and custom_rasterizer + DifferentiableRenderer are compiled."
        )
        return None

    try:
        logger.info("  Loading Hunyuan3D-2.1 texture generation model...")
        max_num_view = 6
        resolution = 512  # Use 512 to fit in 12GB VRAM (768 needs more)
        conf = Hunyuan3DPaintConfig(max_num_view, resolution)
        conf.realesrgan_ckpt_path = str(HUNYUAN_ROOT / "hy3dpaint/ckpt/RealESRGAN_x4plus.pth")
        conf.multiview_cfg_path = str(HUNYUAN_ROOT / "hy3dpaint/cfgs/hunyuan-paint-pbr.yaml")
        conf.custom_pipeline = str(HUNYUAN_ROOT / "hy3dpaint/hunyuanpaintpbr")
        paint_pipeline = Hunyuan3DPaintPipeline(conf)

        logger.info("  Generating PBR texture...")
        start = time.time()

        # Resolve image for paint pipeline (it accepts str path or PIL Image)
        if image_path.startswith(("http://", "https://")):
            import requests
            from io import BytesIO
            from PIL import Image
            resp = requests.get(image_path, timeout=60)
            resp.raise_for_status()
            paint_image = Image.open(BytesIO(resp.content)).convert("RGBA")
        else:
            paint_image = image_path  # Local path — pipeline handles it

        # Paint pipeline outputs OBJ + texture maps (albedo, metallic, roughness JPGs)
        output_obj_path = str(output_dir / "model_textured.obj")
        textured_obj = paint_pipeline(
            mesh_path=str(shape_glb_path),
            image_path=paint_image,
            output_mesh_path=output_obj_path,
            save_glb=False,  # We'll convert ourselves with PBR materials
        )
        elapsed = time.time() - start
        logger.info(f"  Texture generation took {elapsed:.1f}s")
        logger.info(f"  Textured OBJ at: {textured_obj}")

        # Free VRAM before conversion
        del paint_pipeline
        gc.collect()
        torch.cuda.empty_cache()

        # Convert OBJ → GLB with PBR materials (albedo + metallic + roughness)
        textured_glb = output_dir / "model_textured.glb"
        textures = {
            'albedo': output_obj_path.replace('.obj', '.jpg'),
            'metallic': output_obj_path.replace('.obj', '_metallic.jpg'),
            'roughness': output_obj_path.replace('.obj', '_roughness.jpg'),
        }
        logger.info("  Converting textured OBJ to GLB with PBR materials...")
        create_glb_with_pbr_materials(output_obj_path, textures, str(textured_glb))

        if textured_glb.exists():
            logger.info(f"  Textured GLB saved: {textured_glb}")
            return textured_glb

        logger.warning("  No textured output found")
        return None

    except Exception as e:
        logger.error(f"  Texture generation failed: {e}")
        gc.collect()
        torch.cuda.empty_cache()
        return None


def postprocess_mesh(glb_path: Path, output_dir: Path) -> Path | None:
    """Post-process GLB: decimate, optimize for web delivery."""
    try:
        import trimesh

        logger.info("  Post-processing mesh...")
        scene = trimesh.load(str(glb_path))

        if isinstance(scene, trimesh.Scene):
            meshes = list(scene.geometry.values())
            if not meshes:
                logger.error("  No geometry found in GLB")
                return None
            mesh = trimesh.util.concatenate(meshes)
        else:
            mesh = scene

        logger.info(f"  Original: {len(mesh.faces)} triangles, {len(mesh.vertices)} vertices")

        if len(mesh.faces) > MAX_TRIANGLES:
            logger.info(f"  Decimating from {len(mesh.faces)} to ~{MAX_TRIANGLES} triangles...")
            mesh = mesh.simplify_quadric_decimation(face_count=MAX_TRIANGLES)
            logger.info(f"  After decimation: {len(mesh.faces)} triangles")

        output_path = output_dir / "model.glb"
        mesh.export(str(output_path), file_type="glb")

        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"  Output: {size_mb:.1f} MB, {len(mesh.faces)} triangles, {len(mesh.vertices)} vertices")

        if size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"  File exceeds {MAX_FILE_SIZE_MB}MB target.")

        return output_path

    except Exception as e:
        logger.error(f"  Post-processing failed: {e}")
        return None


def convert_to_usdz(glb_path: Path, output_dir: Path) -> Path | None:
    """Convert GLB to USDZ for iOS AR Quick Look."""
    try:
        from pxr import Usd, UsdGeom, UsdUtils
        import trimesh

        usdz_path = output_dir / "model.usdz"
        usdc_path = output_dir / "model_temp.usdc"

        mesh = trimesh.load(str(glb_path))
        stage = Usd.Stage.CreateNew(str(usdc_path))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

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
        UsdUtils.CreateNewUsdzPackage(str(usdc_path), str(usdz_path))
        usdc_path.unlink(missing_ok=True)

        logger.info(f"  USDZ created: {usdz_path}")
        return usdz_path

    except ImportError:
        logger.warning("  usd-core not installed. Skipping USDZ conversion.")
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
    skip_texture: bool = False,
) -> dict:
    """Process a single robot: shape → texture → postprocess → USDZ → poster."""
    robot_dir = OUTPUT_DIR / robot_name.replace(" ", "_").lower()

    if skip_existing and (robot_dir / "model.glb").exists():
        logger.info(f"  Skipping {robot_name} (already exists)")
        return {"robot_name": robot_name, "status": "skipped"}

    # Select source image (prefer enhanced bg-removed, then best from assessment)
    if source_image:
        image_path = source_image
    else:
        image_path = get_enhanced_image(robot_name)
        if not image_path:
            image_path = get_best_image(robot_name, assessment)

    if not image_path:
        logger.warning(f"  No suitable image found for {robot_name}")
        return {"robot_name": robot_name, "status": "no_image"}

    logger.info(f"  Source image: {image_path}")

    # Step 1: Shape generation
    shape_path = generate_shape(image_path, robot_dir, steps=steps, seed=seed)
    if not shape_path:
        return {"robot_name": robot_name, "status": "shape_failed"}

    # Step 2: Texture generation (sequential, after shape model is unloaded)
    best_glb = shape_path
    if not skip_texture:
        textured_path = generate_texture(shape_path, image_path, robot_dir)
        if textured_path:
            best_glb = textured_path
        else:
            logger.warning("  Falling back to untextured shape model")

    # Step 3: Post-process (decimate for web)
    glb_path = postprocess_mesh(best_glb, robot_dir)
    if not glb_path:
        return {"robot_name": robot_name, "status": "postprocess_failed"}

    # Step 4: USDZ conversion
    usdz_path = convert_to_usdz(glb_path, robot_dir)

    # Step 5: Poster render
    poster_path = render_poster(glb_path, robot_dir)

    # Collect stats
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
        "textured": best_glb != shape_path,
        "generation_params": {
            "steps": steps,
            "seed": seed,
            "pipeline_version": "hunyuan3d-2.1",
            "max_triangles": MAX_TRIANGLES,
        },
    }


def main():
    global MAX_TRIANGLES, MAX_FILE_SIZE_MB, HUNYUAN_ROOT

    parser = argparse.ArgumentParser(description="Generate 3D models from robot images using Hunyuan3D 2.1")
    parser.add_argument("--robot", help="Generate for a specific robot")
    parser.add_argument("--all", action="store_true", help="Generate for all robots")
    parser.add_argument("--skip-existing", action="store_true", help="Skip robots with existing models")
    parser.add_argument("--skip-texture", action="store_true", help="Shape only, no texture (faster, less VRAM)")
    parser.add_argument("--source-image", help="Override source image path/URL")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-triangles", type=int, default=MAX_TRIANGLES)
    parser.add_argument("--max-file-size-mb", type=float, default=MAX_FILE_SIZE_MB)
    parser.add_argument("--retry", type=int, default=1, help="Retries on failure")
    parser.add_argument("--hunyuan-path", help="Path to Hunyuan3D-2.1 repo")
    args = parser.parse_args()

    MAX_TRIANGLES = args.max_triangles
    MAX_FILE_SIZE_MB = args.max_file_size_mb
    if args.hunyuan_path:
        HUNYUAN_ROOT = Path(args.hunyuan_path)

    if not args.robot and not args.all:
        parser.error("Specify --robot <name> or --all")

    if not HUNYUAN_ROOT.exists():
        logger.error(f"Hunyuan3D-2.1 repo not found at {HUNYUAN_ROOT}")
        logger.error("Clone it: git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1")
        sys.exit(1)

    assessment = load_assessment()

    if args.robot:
        robots_to_process = [args.robot]
    else:
        robots_to_process = [r["robot_name"] for r in assessment.get("robots", [])]

    logger.info(f"Processing {len(robots_to_process)} robot(s) with Hunyuan3D-2.1...")
    logger.info(f"  Texture generation: {'DISABLED' if args.skip_texture else 'ENABLED (sequential low-VRAM)'}")
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
                args.skip_existing, args.source_image, args.skip_texture,
            )
            if result["status"] in ("completed", "skipped"):
                break

        results.append(result)

    report_path = OUTPUT_DIR / "generation_report.json"
    report_path.write_text(json.dumps(results, indent=2))
    logger.info(f"\nReport saved to {report_path}")

    completed = sum(1 for r in results if r["status"] == "completed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = len(results) - completed - skipped
    textured = sum(1 for r in results if r.get("textured"))
    print(f"\n{'='*60}")
    print(f"GENERATION COMPLETE: {completed} done ({textured} textured), {skipped} skipped, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
