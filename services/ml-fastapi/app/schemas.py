from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
DETECTION_SOURCE_ORIGINAL = "original"
DETECTION_SOURCE_CORRECTED = "corrected"

ReviewStatus = Literal[
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_REJECTED,
]
DetectionStateSource = Literal[
    DETECTION_SOURCE_ORIGINAL,
    DETECTION_SOURCE_CORRECTED,
]


class DatasetLoadRequest(BaseModel):
    dataset_path: str | None = None
    dataset_name: str | None = None
    preview_archive_path: str | None = None


class DetectionRunRequest(BaseModel):
    model_path: str | None = None


class CorrectionPatchInput(BaseModel):
    class_name: str | None = Field(default=None, min_length=1)
    x_min: float | None = None
    y_min: float | None = None
    x_max: float | None = None
    y_max: float | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "CorrectionPatchInput":
        bbox_values = (self.x_min, self.y_min, self.x_max, self.y_max)
        has_any_bbox_value = any(value is not None for value in bbox_values)
        has_full_bbox = all(value is not None for value in bbox_values)

        if has_any_bbox_value and not has_full_bbox:
            raise ValueError(
                "Corrected bounding boxes must include x_min, y_min, x_max, and y_max together."
            )

        if self.class_name is None and not has_full_bbox:
            raise ValueError(
                "Correction payloads must include a corrected label, a corrected bounding box, or both."
            )

        return self


class SaveCorrectionRequest(BaseModel):
    review_status: ReviewStatus = REVIEW_STATUS_PENDING
    corrected_detection: CorrectionPatchInput | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "SaveCorrectionRequest":
        if (
            self.corrected_detection is None
            and self.review_status == REVIEW_STATUS_PENDING
        ):
            raise ValueError(
                "Correction requests must include corrected detection data or an explicit non-pending review status."
            )

        return self


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


class InferenceRunRecord(BaseModel):
    id: int
    dataset_id: int
    run_type: str
    status: str
    model_name: str
    model_path: str
    frame_count: int
    processed_frame_count: int
    detection_count: int
    error_message: str | None = None
    started_at: str
    completed_at: str | None = None


class DetectionRunResponse(BaseModel):
    run: InferenceRunRecord


class DetectionRecord(BaseModel):
    id: int
    inference_run_id: int
    frame_id: str
    class_name: str
    confidence_score: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    created_at: str


class FrameDetectionsResponse(BaseModel):
    frame_id: str
    run: InferenceRunRecord
    detections: list[DetectionRecord] = Field(default_factory=list)


class DetectionStateRecord(BaseModel):
    detection_id: int
    inference_run_id: int
    frame_id: str
    class_name: str
    confidence_score: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    source: DetectionStateSource


class DetectionCorrectionRecord(BaseModel):
    id: int
    detection_id: int
    review_status: ReviewStatus
    created_at: str
    updated_at: str
    original_detection: DetectionStateRecord
    corrected_detection: DetectionStateRecord | None = None
    effective_detection: DetectionStateRecord | None = None


class DetectionCorrectionResponse(BaseModel):
    correction: DetectionCorrectionRecord


class FrameCorrectionsResponse(BaseModel):
    frame_id: str
    run: InferenceRunRecord
    corrections: list[DetectionCorrectionRecord] = Field(default_factory=list)
