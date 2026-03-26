from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetLoadRequest(BaseModel):
    dataset_path: str | None = None
    dataset_name: str | None = None
    preview_archive_path: str | None = None


class DatasetRecord(BaseModel):
    id: int
    name: str
    source_path: str
    sequence_id: str
    camera_name: str
    frame_count: int
    created_at: str


class DatasetLoadResponse(BaseModel):
    dataset: DatasetRecord
    loaded_frame_count: int


class DatasetListResponse(BaseModel):
    datasets: list[DatasetRecord]


class FrameRecord(BaseModel):
    frame_id: str
    dataset_id: int
    image_path: str
    latitude: float
    longitude: float
    heading_degrees: float
    timestamp: str
    image_width: int
    image_height: int
    pitch_degrees: float | None = None
    roll_degrees: float | None = None
    camera_intrinsics_json: str | None = None
    sequence_id: str | None = None
    depth_path: str | None = None


class FrameListResponse(BaseModel):
    dataset: DatasetRecord
    frames: list[FrameRecord] = Field(default_factory=list)


class FrameDetailRecord(FrameRecord):
    preview_url: str


class FrameDetailResponse(BaseModel):
    frame: FrameDetailRecord
