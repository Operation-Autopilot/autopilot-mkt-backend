"""Robot 3D model business logic service."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from src.core.config import get_settings
from src.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class RobotModelService:
    """Service for managing robot 3D models."""

    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.settings = get_settings()

    async def _execute_sync(self, query):
        """Run synchronous Supabase query in thread pool."""
        return await asyncio.to_thread(query.execute)

    async def list_models(self, robot_id: UUID) -> list[dict[str, Any]]:
        """List all 3D model versions for a robot."""
        query = (
            self.client.table("robot_3d_models")
            .select("*")
            .eq("robot_id", str(robot_id))
            .order("version", desc=True)
        )
        response = await self._execute_sync(query)
        return response.data or []

    async def get_active_model(self, robot_id: UUID) -> dict[str, Any] | None:
        """Get the currently active 3D model for a robot."""
        query = (
            self.client.table("robot_3d_models")
            .select("*")
            .eq("robot_id", str(robot_id))
            .eq("is_active", True)
            .maybe_single()
        )
        response = await self._execute_sync(query)
        return response.data if response and response.data else None

    async def create_model_record(
        self,
        robot_id: UUID,
        source_image_urls: list[str],
        pipeline_version: str,
        generation_params: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new pending 3D model record."""
        # Get next version number
        query = (
            self.client.table("robot_3d_models")
            .select("version")
            .eq("robot_id", str(robot_id))
            .order("version", desc=True)
            .limit(1)
        )
        response = await self._execute_sync(query)
        next_version = (response.data[0]["version"] + 1) if response.data else 1

        record = {
            "robot_id": str(robot_id),
            "version": next_version,
            "source_image_urls": source_image_urls,
            "pipeline_version": pipeline_version,
            "generation_params": generation_params or {},
            "status": "pending",
        }
        query = self.client.table("robot_3d_models").insert(record)
        response = await self._execute_sync(query)
        return response.data[0]

    async def update_model_status(
        self,
        model_id: UUID,
        status: str,
        glb_url: str | None = None,
        usdz_url: str | None = None,
        quality_score: float | None = None,
        glb_file_size_bytes: int | None = None,
        vertex_count: int | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        """Update model status after generation."""
        update_data: dict[str, Any] = {"status": status}
        if glb_url is not None:
            update_data["glb_url"] = glb_url
        if usdz_url is not None:
            update_data["usdz_url"] = usdz_url
        if quality_score is not None:
            update_data["quality_score"] = quality_score
        if glb_file_size_bytes is not None:
            update_data["glb_file_size_bytes"] = glb_file_size_bytes
        if vertex_count is not None:
            update_data["vertex_count"] = vertex_count
        if error_message is not None:
            update_data["error_message"] = error_message

        query = (
            self.client.table("robot_3d_models")
            .update(update_data)
            .eq("id", str(model_id))
        )
        response = await self._execute_sync(query)
        return response.data[0]

    async def activate_model(self, model_id: UUID) -> dict[str, Any]:
        """Set a model as active and update robot_catalog."""
        # Get the model record
        query = (
            self.client.table("robot_3d_models")
            .select("*")
            .eq("id", str(model_id))
            .single()
        )
        response = await self._execute_sync(query)
        model = response.data

        robot_id = model["robot_id"]

        # Deactivate all other models for this robot
        query = (
            self.client.table("robot_3d_models")
            .update({"is_active": False})
            .eq("robot_id", robot_id)
        )
        await self._execute_sync(query)

        # Activate this model
        query = (
            self.client.table("robot_3d_models")
            .update({"is_active": True})
            .eq("id", str(model_id))
        )
        await self._execute_sync(query)

        # Update robot_catalog with model URLs
        catalog_update = {
            "model_glb_url": model.get("glb_url"),
            "model_usdz_url": model.get("usdz_url"),
            "has_3d_model": True,
        }
        query = (
            self.client.table("robot_catalog")
            .update(catalog_update)
            .eq("id", robot_id)
        )
        await self._execute_sync(query)

        return model

    async def upload_model_file(
        self,
        robot_id: UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str = "model/gltf-binary",
    ) -> str:
        """Upload a model file to Supabase storage."""
        bucket = self.settings.robot_models_bucket
        path = f"robots/{robot_id}/{filename}"

        # Upload to storage (run in thread pool since it's sync)
        def _upload():
            self.client.storage.from_(bucket).upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": content_type},
            )
            return self.client.storage.from_(bucket).get_public_url(path)

        public_url = await asyncio.to_thread(_upload)
        return public_url
