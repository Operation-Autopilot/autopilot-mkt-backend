"""Robot 3D model Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RobotModelResponse(BaseModel):
    """Schema for robot 3D model API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    robot_id: UUID
    version: int
    glb_url: str | None = None
    usdz_url: str | None = None
    status: str = "pending"
    quality_score: float | None = None
    pipeline_version: str | None = None
    glb_file_size_bytes: int | None = None
    vertex_count: int | None = None
    is_active: bool = False
    created_at: datetime | None = None


class RobotModelListResponse(BaseModel):
    """Schema for robot 3D model list responses."""
    model_config = ConfigDict(from_attributes=True)

    items: list[RobotModelResponse] = Field(default_factory=list)
    total: int = 0


class UploadModelRequest(BaseModel):
    """Metadata for model upload."""
    pipeline_version: str = Field(default="hunyuan3d-2.1")
    source_image_urls: list[str] = Field(default_factory=list)
    generation_params: dict = Field(default_factory=dict)
    quality_score: float | None = None
    vertex_count: int | None = None
