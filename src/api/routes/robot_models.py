"""Robot 3D model API routes."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.schemas.robot_model import (
    RobotModelListResponse,
    RobotModelResponse,
    UploadModelRequest,
)
from src.services.robot_model_service import RobotModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/robots", tags=["robot-models"])


@router.get("/{robot_id}/models", response_model=RobotModelListResponse)
async def list_robot_models(robot_id: UUID):
    """List all 3D model versions for a robot."""
    service = RobotModelService()
    models = await service.list_models(robot_id)
    return RobotModelListResponse(
        items=[RobotModelResponse(**m) for m in models],
        total=len(models),
    )


@router.get("/{robot_id}/models/active", response_model=RobotModelResponse | None)
async def get_active_model(robot_id: UUID):
    """Get the currently active 3D model for a robot."""
    service = RobotModelService()
    model = await service.get_active_model(robot_id)
    if not model:
        return None
    return RobotModelResponse(**model)


@router.post("/{robot_id}/models/upload", response_model=RobotModelResponse)
async def upload_model(
    robot_id: UUID,
    glb_file: UploadFile = File(...),
    usdz_file: UploadFile | None = File(None),
    poster_file: UploadFile | None = File(None),
    pipeline_version: str = Form(default="hunyuan3d-2.1"),
    quality_score: float | None = Form(default=None),
    vertex_count: int | None = Form(default=None),
):
    """Upload GLB/USDZ model files and activate."""
    service = RobotModelService()

    # Create model record
    record = await service.create_model_record(
        robot_id=robot_id,
        source_image_urls=[],
        pipeline_version=pipeline_version,
    )
    model_id = UUID(record["id"])
    version = record["version"]

    try:
        # Upload GLB
        glb_bytes = await glb_file.read()
        glb_url = await service.upload_model_file(
            robot_id=robot_id,
            file_bytes=glb_bytes,
            filename=f"v{version}/model.glb",
            content_type="model/gltf-binary",
        )

        # Upload USDZ if provided
        usdz_url = None
        if usdz_file:
            usdz_bytes = await usdz_file.read()
            usdz_url = await service.upload_model_file(
                robot_id=robot_id,
                file_bytes=usdz_bytes,
                filename=f"v{version}/model.usdz",
                content_type="model/vnd.usdz+zip",
            )

        # Upload poster if provided
        poster_url = None
        if poster_file:
            poster_bytes = await poster_file.read()
            poster_url = await service.upload_model_file(
                robot_id=robot_id,
                file_bytes=poster_bytes,
                filename=f"v{version}/poster.webp",
                content_type="image/webp",
            )

        # Update model status
        updated = await service.update_model_status(
            model_id=model_id,
            status="completed",
            glb_url=glb_url,
            usdz_url=usdz_url,
            quality_score=quality_score,
            glb_file_size_bytes=len(glb_bytes),
            vertex_count=vertex_count,
        )

        # Activate the model
        await service.activate_model(model_id)

        # Update poster URL on robot_catalog if provided
        if poster_url:
            import asyncio
            from src.core.supabase import get_supabase_client
            client = get_supabase_client()
            query = client.table("robot_catalog").update(
                {"model_poster_url": poster_url}
            ).eq("id", str(robot_id))
            await asyncio.to_thread(query.execute)

        return RobotModelResponse(**updated)

    except Exception as e:
        logger.error(f"Failed to upload model for robot {robot_id}: {e}")
        await service.update_model_status(
            model_id=model_id,
            status="failed",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Model upload failed: {e}")
