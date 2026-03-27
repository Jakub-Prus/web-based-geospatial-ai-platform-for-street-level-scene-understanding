from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.a2d2_parser import A2D2SubsetParser, DatasetValidationError
from app.config import (
    resolve_database_path,
    resolve_default_dataset_path,
    resolve_default_detection_model_path,
    resolve_default_depth_model_path,
    resolve_depth_artifacts_directory,
    resolve_point_cloud_artifacts_directory,
    resolve_preview_archive_path,
)
from app.database import create_connection, initialize_database
from app.inference import (
    DETECTION_RUN_TYPE,
    DEPTH_RUN_TYPE,
    POINT_CLOUD_RUN_TYPE,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_EMPTY,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    DetectionPrediction,
    DepthEstimator,
    DepthPrediction,
    MidasDepthEstimator,
    ObjectDetector,
    UltralyticsObjectDetector,
)
from app.point_cloud import (
    DEFAULT_MAX_POINT_COUNT,
    DEFAULT_POINT_CLOUD_ARTIFACT_FORMAT,
    POINT_CLOUD_COORDINATE_SYSTEM,
    convert_depth_map_to_point_cloud,
    load_point_cloud_artifact,
    persist_point_cloud_artifact,
    resolve_camera_intrinsics,
)
from app.repository import DatasetRepository
from app.schemas import (
    DETECTION_SOURCE_CORRECTED,
    DETECTION_SOURCE_ORIGINAL,
    DEPTH_ARTIFACT_STATE_COMPLETED,
    DEPTH_ARTIFACT_STATE_FAILED,
    DEPTH_ARTIFACT_STATE_MISSING,
    DEPTH_ARTIFACT_STATE_RUNNING,
    POINT_CLOUD_ARTIFACT_STATE_COMPLETED,
    POINT_CLOUD_ARTIFACT_STATE_FAILED,
    POINT_CLOUD_ARTIFACT_STATE_MISSING,
    POINT_CLOUD_ARTIFACT_STATE_RUNNING,
    REVIEW_STATUS_REJECTED,
    DepthArtifactRecord,
    DepthRunRequest,
    DatasetListResponse,
    DatasetLoadRequest,
    DatasetLoadResponse,
    DatasetMetricsRecord,
    DatasetMetricsResponse,
    DatasetRecord,
    DetectionCorrectionRecord,
    DetectionCorrectionResponse,
    DetectionRecord,
    DetectionStateRecord,
    DetectionRunRequest,
    DetectionRunResponse,
    FrameDepthArtifactResponse,
    FrameDetailRecord,
    FrameDetailResponse,
    FramePointCloudResponse,
    FrameCorrectionsResponse,
    FrameDetectionsResponse,
    FrameListResponse,
    InferenceRunRecord,
    PointCloudArtifactRecord,
    PointCloudPayloadRecord,
    PointCloudPointRecord,
    PointCloudRunRequest,
    SaveCorrectionRequest,
)

SERVICE_NAME = "ml-fastapi"
SERVICE_DESCRIPTION = "Machine-learning facing API scaffold for the geospatial scene demo."
SERVICE_STATUS = "ok"
SERVICE_VERSION = "0.1.0"
DEFAULT_DATASET_NAME = "a2d2-subset"
MINIMUM_IMAGE_COORDINATE = 0.0
ZERO_CORRECTION_RATE = 0.0
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
DEPTH_ARTIFACT_FILE_EXTENSION = ".npy"
DEPTH_ARTIFACT_DIRECTORY_PREFIX = "dataset-"

DetectorFactory = Callable[[Path], ObjectDetector]
DepthEstimatorFactory = Callable[[Path], DepthEstimator]


def build_service_payload() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "description": SERVICE_DESCRIPTION,
        "status": SERVICE_STATUS,
        "version": SERVICE_VERSION,
    }


def utc_now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def clip_detection_bbox(
    prediction: DetectionPrediction,
    *,
    image_width: int,
    image_height: int,
) -> dict[str, float]:
    max_x_coordinate = float(image_width)
    max_y_coordinate = float(image_height)
    x_min = min(
        max(float(prediction.x_min), MINIMUM_IMAGE_COORDINATE),
        max_x_coordinate,
    )
    y_min = min(
        max(float(prediction.y_min), MINIMUM_IMAGE_COORDINATE),
        max_y_coordinate,
    )
    x_max = min(
        max(float(prediction.x_max), MINIMUM_IMAGE_COORDINATE),
        max_x_coordinate,
    )
    y_max = min(
        max(float(prediction.y_max), MINIMUM_IMAGE_COORDINATE),
        max_y_coordinate,
    )

    return {
        "x_min": min(x_min, x_max),
        "y_min": min(y_min, y_max),
        "x_max": max(x_min, x_max),
        "y_max": max(y_min, y_max),
    }


def default_detector_factory(model_path: Path) -> ObjectDetector:
    return UltralyticsObjectDetector(model_path)


def default_depth_estimator_factory(model_path: Path) -> DepthEstimator:
    return MidasDepthEstimator(model_path)


def validate_depth_prediction(
    prediction: DepthPrediction,
    *,
    image_width: int,
    image_height: int,
) -> np.ndarray:
    depth_map = np.asarray(prediction.depth_map, dtype=np.float32)
    if depth_map.ndim != 2:
        raise ValueError("Depth output must be a single-channel map.")

    depth_height, depth_width = depth_map.shape
    if depth_width != image_width or depth_height != image_height:
        raise ValueError(
            "Depth output dimensions "
            f"{depth_width}x{depth_height} did not match source image dimensions "
            f"{image_width}x{image_height}."
        )

    if not np.isfinite(depth_map).any():
        raise ValueError("Depth output did not contain any finite values.")

    return depth_map


def build_depth_artifact_uri(
    *,
    dataset_id: int,
    frame_id: str,
    run_id: int,
) -> str:
    safe_frame_id = frame_id.replace("/", "_").replace("\\", "_")
    return (
        Path(f"{DEPTH_ARTIFACT_DIRECTORY_PREFIX}{dataset_id}")
        / safe_frame_id
        / f"run-{run_id}{DEPTH_ARTIFACT_FILE_EXTENSION}"
    ).as_posix()


def persist_depth_artifact(
    *,
    depth_artifacts_directory: Path,
    dataset_id: int,
    frame_id: str,
    run_id: int,
    depth_map: np.ndarray,
) -> str:
    depth_uri = build_depth_artifact_uri(
        dataset_id=dataset_id,
        frame_id=frame_id,
        run_id=run_id,
    )
    artifact_path = depth_artifacts_directory / depth_uri
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(artifact_path, depth_map.astype(np.float32, copy=False))

    return depth_uri


def validate_bbox_coordinates(
    *,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    image_width: int,
    image_height: int,
) -> None:
    if x_min > x_max or y_min > y_max:
        raise ValueError(
            "Corrected bounding-box coordinates must preserve x_min <= x_max and y_min <= y_max."
        )

    max_x_coordinate = float(image_width)
    max_y_coordinate = float(image_height)
    for coordinate_name, coordinate_value, maximum_value in (
        ("x_min", x_min, max_x_coordinate),
        ("y_min", y_min, max_y_coordinate),
        ("x_max", x_max, max_x_coordinate),
        ("y_max", y_max, max_y_coordinate),
    ):
        if not MINIMUM_IMAGE_COORDINATE <= coordinate_value <= maximum_value:
            raise ValueError(
                f"Corrected {coordinate_name} must be between "
                f"{MINIMUM_IMAGE_COORDINATE} and {maximum_value}."
            )


def build_detection_state(
    *,
    detection_id: int,
    inference_run_id: int,
    frame_id: str,
    class_name: str,
    confidence_score: float,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    source: str,
) -> DetectionStateRecord:
    return DetectionStateRecord(
        detection_id=detection_id,
        inference_run_id=inference_run_id,
        frame_id=frame_id,
        class_name=class_name,
        confidence_score=confidence_score,
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max,
        source=source,
    )


def build_original_detection_state(correction_record: dict[str, object]) -> DetectionStateRecord:
    return build_detection_state(
        detection_id=int(correction_record["original_detection_id"]),
        inference_run_id=int(correction_record["original_inference_run_id"]),
        frame_id=str(correction_record["original_frame_id"]),
        class_name=str(correction_record["original_class_name"]),
        confidence_score=float(correction_record["original_confidence_score"]),
        x_min=float(correction_record["original_x_min"]),
        y_min=float(correction_record["original_y_min"]),
        x_max=float(correction_record["original_x_max"]),
        y_max=float(correction_record["original_y_max"]),
        source=DETECTION_SOURCE_ORIGINAL,
    )


def build_corrected_detection_state(
    correction_record: dict[str, object],
) -> DetectionStateRecord | None:
    corrected_class_name = correction_record["corrected_class_name"]
    corrected_x_min = correction_record["corrected_x_min"]
    corrected_y_min = correction_record["corrected_y_min"]
    corrected_x_max = correction_record["corrected_x_max"]
    corrected_y_max = correction_record["corrected_y_max"]

    if (
        corrected_class_name is None
        and corrected_x_min is None
        and corrected_y_min is None
        and corrected_x_max is None
        and corrected_y_max is None
    ):
        return None

    return build_detection_state(
        detection_id=int(correction_record["original_detection_id"]),
        inference_run_id=int(correction_record["original_inference_run_id"]),
        frame_id=str(correction_record["original_frame_id"]),
        class_name=str(corrected_class_name),
        confidence_score=float(correction_record["original_confidence_score"]),
        x_min=float(corrected_x_min),
        y_min=float(corrected_y_min),
        x_max=float(corrected_x_max),
        y_max=float(corrected_y_max),
        source=DETECTION_SOURCE_CORRECTED,
    )


def build_correction_response_record(
    correction_record: dict[str, object],
) -> DetectionCorrectionRecord:
    original_detection = build_original_detection_state(correction_record)
    corrected_detection = build_corrected_detection_state(correction_record)
    review_status = str(correction_record["review_status"])
    effective_detection = (
        None
        if review_status == REVIEW_STATUS_REJECTED
        else corrected_detection or original_detection
    )

    return DetectionCorrectionRecord(
        id=int(correction_record["correction_id"]),
        detection_id=int(correction_record["detection_id"]),
        review_status=review_status,
        created_at=str(correction_record["correction_created_at"]),
        updated_at=str(correction_record["correction_updated_at"]),
        original_detection=original_detection,
        corrected_detection=corrected_detection,
        effective_detection=effective_detection,
    )


def build_dataset_metrics_response(
    *,
    dataset_id: int,
    run_record: dict[str, object] | None,
    metrics_record: dict[str, object] | None,
) -> DatasetMetricsResponse:
    detection_count = (
        int(metrics_record["detection_count"])
        if metrics_record is not None
        else 0
    )
    correction_count = (
        int(metrics_record["correction_count"])
        if metrics_record is not None
        else 0
    )
    average_confidence_score = (
        None
        if metrics_record is None or metrics_record["average_confidence_score"] is None
        else float(metrics_record["average_confidence_score"])
    )
    correction_rate = (
        correction_count / detection_count
        if detection_count > 0
        else ZERO_CORRECTION_RATE
    )

    return DatasetMetricsResponse(
        dataset_id=dataset_id,
        run=(
            InferenceRunRecord.model_validate(run_record)
            if run_record is not None
            else None
        ),
        metrics=DatasetMetricsRecord(
            detection_count=detection_count,
            average_confidence_score=average_confidence_score,
            correction_count=correction_count,
            correction_rate=correction_rate,
        ),
    )


def build_frame_depth_artifact_response(
    *,
    frame_id: str,
    state: str,
    detail: str | None,
    run_record: dict[str, object] | None,
    artifact_record: dict[str, object] | None,
) -> FrameDepthArtifactResponse:
    return FrameDepthArtifactResponse(
        frame_id=frame_id,
        state=state,
        detail=detail,
        run=(
            InferenceRunRecord.model_validate(run_record)
            if run_record is not None
            else None
        ),
        artifact=(
            DepthArtifactRecord.model_validate(artifact_record)
            if artifact_record is not None
            else None
        ),
    )


def load_depth_artifact(
    *,
    depth_artifacts_directory: Path,
    depth_uri: str,
    image_width: int,
    image_height: int,
) -> np.ndarray:
    depth_artifact_path = (depth_artifacts_directory / depth_uri).resolve()
    if not depth_artifact_path.is_file():
        raise FileNotFoundError(
            f"Stored depth artifact file was not found: {depth_artifact_path}"
        )

    stored_depth_map = np.load(depth_artifact_path)
    return validate_depth_prediction(
        DepthPrediction(depth_map=stored_depth_map),
        image_width=image_width,
        image_height=image_height,
    )


def build_point_cloud_payload_record(points: np.ndarray) -> PointCloudPayloadRecord:
    point_records = [
        PointCloudPointRecord(
            x=float(point[0]),
            y=float(point[1]),
            z=float(point[2]),
        )
        for point in np.asarray(points, dtype=np.float32)
    ]

    return PointCloudPayloadRecord(points=point_records)


def build_frame_point_cloud_response(
    *,
    frame_id: str,
    state: str,
    detail: str | None,
    run_record: dict[str, object] | None,
    artifact_record: dict[str, object] | None,
    points: np.ndarray | None,
) -> FramePointCloudResponse:
    return FramePointCloudResponse(
        frame_id=frame_id,
        state=state,
        detail=detail,
        run=(
            InferenceRunRecord.model_validate(run_record)
            if run_record is not None
            else None
        ),
        artifact=(
            PointCloudArtifactRecord.model_validate(artifact_record)
            if artifact_record is not None
            else None
        ),
        payload=(
            build_point_cloud_payload_record(points)
            if points is not None
            else None
        ),
    )


def build_point_cloud_missing_response_from_depth_state(
    *,
    frame_id: str,
    depth_run_record: dict[str, object] | None,
    depth_artifact_record: dict[str, object] | None,
) -> FramePointCloudResponse:
    if depth_run_record is None:
        return build_frame_point_cloud_response(
            frame_id=frame_id,
            state=POINT_CLOUD_ARTIFACT_STATE_MISSING,
            detail=(
                "No stored depth artifact exists for this frame yet. "
                "Generate depth first before requesting a point cloud."
            ),
            run_record=None,
            artifact_record=None,
            points=None,
        )

    depth_run_status = str(depth_run_record["status"])
    if depth_artifact_record is None:
        if depth_run_status == RUN_STATUS_RUNNING:
            return build_frame_point_cloud_response(
                frame_id=frame_id,
                state=POINT_CLOUD_ARTIFACT_STATE_RUNNING,
                detail="Depth inference is still running for this frame.",
                run_record=depth_run_record,
                artifact_record=None,
                points=None,
            )
        if depth_run_status == RUN_STATUS_FAILED:
            return build_frame_point_cloud_response(
                frame_id=frame_id,
                state=POINT_CLOUD_ARTIFACT_STATE_FAILED,
                detail=str(
                    depth_run_record["error_message"]
                    or "Depth inference failed for this frame."
                ),
                run_record=depth_run_record,
                artifact_record=None,
                points=None,
            )

    return build_frame_point_cloud_response(
        frame_id=frame_id,
        state=POINT_CLOUD_ARTIFACT_STATE_MISSING,
        detail=(
            "A completed depth run was found, but no stored depth artifact is available "
            "for point-cloud conversion."
        ),
        run_record=depth_run_record,
        artifact_record=None,
        points=None,
    )


def resolve_depth_artifact_for_frame(
    *,
    repository: DatasetRepository,
    dataset_id: int,
    frame_id: str,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    try:
        depth_run_record = repository.get_latest_inference_run_for_frame(
            dataset_id,
            frame_id,
            DEPTH_RUN_TYPE,
        )
    except KeyError:
        return None, None

    depth_artifact_record = repository.get_depth_artifact_for_run(
        inference_run_id=int(depth_run_record["id"]),
        frame_id=frame_id,
    )
    return depth_run_record, depth_artifact_record


def create_app(
    detector_factory: DetectorFactory | None = None,
    depth_estimator_factory: DepthEstimatorFactory | None = None,
) -> FastAPI:
    database_path = resolve_database_path()
    initialize_database(database_path)
    depth_artifacts_directory = resolve_depth_artifacts_directory()
    point_cloud_artifacts_directory = resolve_point_cloud_artifacts_directory()
    depth_artifacts_directory.mkdir(parents=True, exist_ok=True)
    point_cloud_artifacts_directory.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Geospatial Scene ML API",
        version=SERVICE_VERSION,
        description=SERVICE_DESCRIPTION,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DEFAULT_ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.database_path = database_path
    app.state.detector_factory = detector_factory or default_detector_factory
    app.state.depth_estimator_factory = (
        depth_estimator_factory or default_depth_estimator_factory
    )
    app.state.depth_artifacts_directory = depth_artifacts_directory
    app.state.point_cloud_artifacts_directory = point_cloud_artifacts_directory

    @app.get("/", status_code=HTTPStatus.OK)
    async def read_root() -> dict[str, str]:
        return build_service_payload()

    @app.get("/health", status_code=HTTPStatus.OK)
    async def read_health() -> dict[str, str]:
        return build_service_payload()

    @app.post(
        "/datasets/load",
        response_model=DatasetLoadResponse,
        status_code=HTTPStatus.CREATED,
    )
    async def load_dataset(request: DatasetLoadRequest) -> DatasetLoadResponse:
        dataset_path = (
            Path(request.dataset_path).resolve()
            if request.dataset_path
            else resolve_default_dataset_path()
        )
        preview_archive_path = (
            Path(request.preview_archive_path).resolve()
            if request.preview_archive_path
            else resolve_preview_archive_path()
        )
        parser = A2D2SubsetParser(
            dataset_root=dataset_path,
            preview_archive_path=preview_archive_path,
        )

        try:
            parsed_dataset = parser.parse(
                dataset_name=request.dataset_name or DEFAULT_DATASET_NAME
            )
        except DatasetValidationError as error:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=str(error),
            ) from error

        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            dataset_record = repository.replace_dataset(
                name=parsed_dataset.name,
                source_path=parsed_dataset.source_path,
                sequence_id=parsed_dataset.sequence_id,
                camera_name=parsed_dataset.camera_name,
                created_at=parsed_dataset.created_at,
                frames=parsed_dataset.frames,
            )

        return DatasetLoadResponse(
            dataset=DatasetRecord.model_validate(dataset_record),
            loaded_frame_count=len(parsed_dataset.frames),
        )

    @app.get("/datasets", response_model=DatasetListResponse, status_code=HTTPStatus.OK)
    async def list_datasets() -> DatasetListResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            dataset_records = repository.list_datasets()

        return DatasetListResponse(
            datasets=[DatasetRecord.model_validate(record) for record in dataset_records]
        )

    @app.get(
        "/datasets/{dataset_id}/metrics",
        response_model=DatasetMetricsResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_dataset_metrics(dataset_id: int) -> DatasetMetricsResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_dataset(dataset_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Dataset {dataset_id} was not found.",
                ) from error

            try:
                run_record = repository.get_latest_detection_run_for_dataset(
                    dataset_id,
                    DETECTION_RUN_TYPE,
                )
            except KeyError:
                return build_dataset_metrics_response(
                    dataset_id=dataset_id,
                    run_record=None,
                    metrics_record=None,
                )

            metrics_record = repository.summarize_detection_metrics_for_run(
                int(run_record["id"])
            )

        return build_dataset_metrics_response(
            dataset_id=dataset_id,
            run_record=run_record,
            metrics_record=metrics_record,
        )

    @app.get(
        "/datasets/{dataset_id}/frames",
        response_model=FrameListResponse,
        status_code=HTTPStatus.OK,
    )
    async def list_dataset_frames(dataset_id: int) -> FrameListResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                dataset_record = repository.get_dataset(dataset_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Dataset {dataset_id} was not found.",
                ) from error
            frame_records = repository.list_frames_for_dataset(dataset_id)

        return FrameListResponse(
            dataset=DatasetRecord.model_validate(dataset_record),
            frames=frame_records,
        )

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}",
        response_model=FrameDetailResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_frame_detail(dataset_id: int, frame_id: str) -> FrameDetailResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                frame_record = repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

        return FrameDetailResponse(
            frame=FrameDetailRecord(
                **{
                    key: value
                    for key, value in frame_record.items()
                    if key != "dataset_source_path"
                },
                preview_url=str(
                    app.url_path_for(
                        "get_frame_preview",
                        dataset_id=str(dataset_id),
                        frame_id=frame_id,
                    )
                ),
            )
        )

    @app.post(
        "/datasets/{dataset_id}/frames/{frame_id}/depth",
        response_model=FrameDepthArtifactResponse,
        status_code=HTTPStatus.CREATED,
    )
    async def trigger_depth_inference(
        dataset_id: int,
        frame_id: str,
        request: DepthRunRequest | None = None,
    ) -> FrameDepthArtifactResponse:
        resolved_request = request or DepthRunRequest()
        model_path = (
            Path(resolved_request.model_path).resolve()
            if resolved_request.model_path
            else resolve_default_depth_model_path()
        )
        started_at = utc_now_isoformat()
        processed_frame_count = 0

        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                frame_record = repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            run_record = repository.create_inference_run(
                dataset_id=dataset_id,
                run_type=DEPTH_RUN_TYPE,
                frame_id=frame_id,
                status=RUN_STATUS_RUNNING,
                model_name=model_path.stem,
                model_path=str(model_path),
                frame_count=1,
                started_at=started_at,
            )
            depth_estimator = app.state.depth_estimator_factory(model_path)

            try:
                image_path = (
                    Path(str(frame_record["dataset_source_path"])).resolve()
                    / str(frame_record["image_path"])
                )
                prediction = depth_estimator.estimate(image_path)
                processed_frame_count = 1
                depth_map = validate_depth_prediction(
                    prediction,
                    image_width=int(frame_record["image_width"]),
                    image_height=int(frame_record["image_height"]),
                )
                depth_uri = persist_depth_artifact(
                    depth_artifacts_directory=app.state.depth_artifacts_directory,
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    run_id=int(run_record["id"]),
                    depth_map=depth_map,
                )
                artifact_record = repository.save_depth_artifact(
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    inference_run_id=int(run_record["id"]),
                    depth_uri=depth_uri,
                    width=int(frame_record["image_width"]),
                    height=int(frame_record["image_height"]),
                    depth_format=prediction.depth_format,
                    depth_scale=prediction.depth_scale,
                    created_at=utc_now_isoformat(),
                )
                completed_run_record = repository.finalize_inference_run(
                    run_id=int(run_record["id"]),
                    status=RUN_STATUS_COMPLETED,
                    processed_frame_count=processed_frame_count,
                    detection_count=0,
                    completed_at=utc_now_isoformat(),
                    detections=[],
                )
            except Exception as error:
                failed_run_record = repository.mark_inference_run_failed(
                    run_id=int(run_record["id"]),
                    processed_frame_count=processed_frame_count,
                    completed_at=utc_now_isoformat(),
                    error_message=str(error),
                )
                return build_frame_depth_artifact_response(
                    frame_id=frame_id,
                    state=DEPTH_ARTIFACT_STATE_FAILED,
                    detail=str(error),
                    run_record=failed_run_record,
                    artifact_record=None,
                )

        return build_frame_depth_artifact_response(
            frame_id=frame_id,
            state=DEPTH_ARTIFACT_STATE_COMPLETED,
            detail=None,
            run_record=completed_run_record,
            artifact_record=artifact_record,
        )

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}/depth",
        response_model=FrameDepthArtifactResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_frame_depth_artifact(
        dataset_id: int,
        frame_id: str,
    ) -> FrameDepthArtifactResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            try:
                run_record = repository.get_latest_inference_run_for_frame(
                    dataset_id,
                    frame_id,
                    DEPTH_RUN_TYPE,
                )
            except KeyError:
                return build_frame_depth_artifact_response(
                    frame_id=frame_id,
                    state=DEPTH_ARTIFACT_STATE_MISSING,
                    detail="No depth artifact has been generated for this frame yet.",
                    run_record=None,
                    artifact_record=None,
                )

            artifact_record = repository.get_depth_artifact_for_run(
                inference_run_id=int(run_record["id"]),
                frame_id=frame_id,
            )

        run_status = str(run_record["status"])
        if artifact_record is None:
            if run_status == RUN_STATUS_RUNNING:
                state = DEPTH_ARTIFACT_STATE_RUNNING
                detail = "Depth inference is still running for this frame."
            elif run_status == RUN_STATUS_FAILED:
                state = DEPTH_ARTIFACT_STATE_FAILED
                detail = str(run_record["error_message"] or "Depth inference failed.")
            else:
                state = DEPTH_ARTIFACT_STATE_MISSING
                detail = "The latest depth run did not persist an artifact."

            return build_frame_depth_artifact_response(
                frame_id=frame_id,
                state=state,
                detail=detail,
                run_record=run_record,
                artifact_record=None,
            )

        return build_frame_depth_artifact_response(
            frame_id=frame_id,
            state=DEPTH_ARTIFACT_STATE_COMPLETED,
            detail=None,
            run_record=run_record,
            artifact_record=artifact_record,
        )

    @app.post(
        "/datasets/{dataset_id}/frames/{frame_id}/point-cloud",
        response_model=FramePointCloudResponse,
        status_code=HTTPStatus.CREATED,
    )
    async def trigger_point_cloud_generation(
        dataset_id: int,
        frame_id: str,
        request: PointCloudRunRequest | None = None,
    ) -> FramePointCloudResponse:
        resolved_request = request or PointCloudRunRequest()
        max_point_count = resolved_request.max_point_count or DEFAULT_MAX_POINT_COUNT
        started_at = utc_now_isoformat()

        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                frame_record = repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            depth_run_record, depth_artifact_record = resolve_depth_artifact_for_frame(
                repository=repository,
                dataset_id=dataset_id,
                frame_id=frame_id,
            )
            if depth_artifact_record is None:
                return build_point_cloud_missing_response_from_depth_state(
                    frame_id=frame_id,
                    depth_run_record=depth_run_record,
                    depth_artifact_record=depth_artifact_record,
                )

            run_record = repository.create_inference_run(
                dataset_id=dataset_id,
                run_type=POINT_CLOUD_RUN_TYPE,
                frame_id=frame_id,
                status=RUN_STATUS_RUNNING,
                model_name="stored-depth-conversion",
                model_path=str(depth_artifact_record["depth_uri"]),
                frame_count=1,
                started_at=started_at,
            )

            try:
                stored_depth_map = load_depth_artifact(
                    depth_artifacts_directory=app.state.depth_artifacts_directory,
                    depth_uri=str(depth_artifact_record["depth_uri"]),
                    image_width=int(frame_record["image_width"]),
                    image_height=int(frame_record["image_height"]),
                )
                intrinsics = resolve_camera_intrinsics(
                    camera_intrinsics_json=(
                        None
                        if frame_record["camera_intrinsics_json"] is None
                        else str(frame_record["camera_intrinsics_json"])
                    ),
                    image_width=int(frame_record["image_width"]),
                    image_height=int(frame_record["image_height"]),
                )
                conversion_result = convert_depth_map_to_point_cloud(
                    depth_map=stored_depth_map,
                    intrinsics=intrinsics,
                    max_point_count=max_point_count,
                )
                point_cloud_uri = persist_point_cloud_artifact(
                    point_cloud_artifacts_directory=app.state.point_cloud_artifacts_directory,
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    run_id=int(run_record["id"]),
                    points=conversion_result.points,
                )
                artifact_record = repository.save_point_cloud_artifact(
                    inference_run_id=int(run_record["id"]),
                    frame_id=frame_id,
                    source_depth_artifact_id=int(depth_artifact_record["id"]),
                    point_cloud_uri=point_cloud_uri,
                    point_format=DEFAULT_POINT_CLOUD_ARTIFACT_FORMAT,
                    coordinate_system=POINT_CLOUD_COORDINATE_SYSTEM,
                    source_point_count=conversion_result.source_point_count,
                    point_count=conversion_result.point_count,
                    subsample_step=conversion_result.subsample_step,
                    intrinsics_source=conversion_result.intrinsics.source,
                    fx=conversion_result.intrinsics.fx,
                    fy=conversion_result.intrinsics.fy,
                    cx=conversion_result.intrinsics.cx,
                    cy=conversion_result.intrinsics.cy,
                    created_at=utc_now_isoformat(),
                )
                completed_run_record = repository.finalize_inference_run(
                    run_id=int(run_record["id"]),
                    status=RUN_STATUS_COMPLETED,
                    processed_frame_count=1,
                    detection_count=0,
                    completed_at=utc_now_isoformat(),
                    detections=[],
                )
            except Exception as error:
                failed_run_record = repository.mark_inference_run_failed(
                    run_id=int(run_record["id"]),
                    processed_frame_count=1,
                    completed_at=utc_now_isoformat(),
                    error_message=str(error),
                )
                return build_frame_point_cloud_response(
                    frame_id=frame_id,
                    state=POINT_CLOUD_ARTIFACT_STATE_FAILED,
                    detail=str(error),
                    run_record=failed_run_record,
                    artifact_record=None,
                    points=None,
                )

        return build_frame_point_cloud_response(
            frame_id=frame_id,
            state=POINT_CLOUD_ARTIFACT_STATE_COMPLETED,
            detail=None,
            run_record=completed_run_record,
            artifact_record=artifact_record,
            points=conversion_result.points,
        )

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}/point-cloud",
        response_model=FramePointCloudResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_frame_point_cloud(
        dataset_id: int,
        frame_id: str,
    ) -> FramePointCloudResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            try:
                run_record = repository.get_latest_inference_run_for_frame(
                    dataset_id,
                    frame_id,
                    POINT_CLOUD_RUN_TYPE,
                )
            except KeyError:
                depth_run_record, depth_artifact_record = resolve_depth_artifact_for_frame(
                    repository=repository,
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                )
                return build_point_cloud_missing_response_from_depth_state(
                    frame_id=frame_id,
                    depth_run_record=depth_run_record,
                    depth_artifact_record=depth_artifact_record,
                )

            artifact_record = repository.get_point_cloud_artifact_for_run(
                inference_run_id=int(run_record["id"]),
                frame_id=frame_id,
            )

        run_status = str(run_record["status"])
        if artifact_record is None:
            if run_status == RUN_STATUS_RUNNING:
                state = POINT_CLOUD_ARTIFACT_STATE_RUNNING
                detail = "Point-cloud generation is still running for this frame."
            elif run_status == RUN_STATUS_FAILED:
                state = POINT_CLOUD_ARTIFACT_STATE_FAILED
                detail = str(
                    run_record["error_message"] or "Point-cloud generation failed."
                )
            else:
                state = POINT_CLOUD_ARTIFACT_STATE_MISSING
                detail = "The latest point-cloud run did not persist an artifact."

            return build_frame_point_cloud_response(
                frame_id=frame_id,
                state=state,
                detail=detail,
                run_record=run_record,
                artifact_record=None,
                points=None,
            )

        try:
            points = load_point_cloud_artifact(
                point_cloud_artifacts_directory=app.state.point_cloud_artifacts_directory,
                point_cloud_uri=str(artifact_record["point_cloud_uri"]),
            )
        except Exception as error:
            return build_frame_point_cloud_response(
                frame_id=frame_id,
                state=POINT_CLOUD_ARTIFACT_STATE_FAILED,
                detail=str(error),
                run_record=run_record,
                artifact_record=artifact_record,
                points=None,
            )

        return build_frame_point_cloud_response(
            frame_id=frame_id,
            state=POINT_CLOUD_ARTIFACT_STATE_COMPLETED,
            detail=None,
            run_record=run_record,
            artifact_record=artifact_record,
            points=points,
        )

    @app.post(
        "/datasets/{dataset_id}/runs/detect",
        response_model=DetectionRunResponse,
        status_code=HTTPStatus.CREATED,
    )
    async def trigger_detection_run(
        dataset_id: int,
        request: DetectionRunRequest | None = None,
    ) -> DetectionRunResponse:
        resolved_request = request or DetectionRunRequest()
        model_path = (
            Path(resolved_request.model_path).resolve()
            if resolved_request.model_path
            else resolve_default_detection_model_path()
        )
        started_at = utc_now_isoformat()
        processed_frame_count = 0

        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_dataset(dataset_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Dataset {dataset_id} was not found.",
                ) from error

            frame_records = repository.list_frames_for_inference(dataset_id)
            run_record = repository.create_inference_run(
                dataset_id=dataset_id,
                run_type=DETECTION_RUN_TYPE,
                frame_id=None,
                status=RUN_STATUS_RUNNING,
                model_name=model_path.stem,
                model_path=str(model_path),
                frame_count=len(frame_records),
                started_at=started_at,
            )
            detector = app.state.detector_factory(model_path)

            try:
                image_paths = [
                    Path(str(frame_record["dataset_source_path"])).resolve()
                    / str(frame_record["image_path"])
                    for frame_record in frame_records
                ]
                predictions_by_frame = detector.detect(image_paths)
                if len(predictions_by_frame) != len(frame_records):
                    raise RuntimeError(
                        "Detector returned a result count that does not match the dataset frames."
                    )

                detections_to_insert: list[dict[str, object]] = []
                created_at = utc_now_isoformat()
                for frame_record, frame_predictions in zip(
                    frame_records,
                    predictions_by_frame,
                ):
                    processed_frame_count += 1
                    for prediction in frame_predictions:
                        clipped_bbox = clip_detection_bbox(
                            prediction,
                            image_width=int(frame_record["image_width"]),
                            image_height=int(frame_record["image_height"]),
                        )
                        detections_to_insert.append(
                            {
                                "inference_run_id": int(run_record["id"]),
                                "frame_id": str(frame_record["frame_id"]),
                                "class_name": prediction.class_name,
                                "confidence_score": prediction.confidence_score,
                                "x_min": clipped_bbox["x_min"],
                                "y_min": clipped_bbox["y_min"],
                                "x_max": clipped_bbox["x_max"],
                                "y_max": clipped_bbox["y_max"],
                                "created_at": created_at,
                            }
                        )

                final_status = (
                    RUN_STATUS_COMPLETED if detections_to_insert else RUN_STATUS_EMPTY
                )
                completed_run_record = repository.finalize_inference_run(
                    run_id=int(run_record["id"]),
                    status=final_status,
                    processed_frame_count=processed_frame_count,
                    detection_count=len(detections_to_insert),
                    completed_at=utc_now_isoformat(),
                    detections=detections_to_insert,
                )
            except Exception as error:
                completed_run_record = repository.mark_inference_run_failed(
                    run_id=int(run_record["id"]),
                    processed_frame_count=processed_frame_count,
                    completed_at=utc_now_isoformat(),
                    error_message=str(error),
                )

        return DetectionRunResponse(
            run=InferenceRunRecord.model_validate(completed_run_record)
        )

    @app.get(
        "/runs/{run_id}",
        response_model=DetectionRunResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_run(run_id: int) -> DetectionRunResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                run_record = repository.get_detection_run(run_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Run {run_id} was not found.",
                ) from error

        return DetectionRunResponse(run=InferenceRunRecord.model_validate(run_record))

    @app.get(
        "/runs/{run_id}/status",
        response_model=DetectionRunResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_run_status(run_id: int) -> DetectionRunResponse:
        return await get_run(run_id)

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}/detections",
        response_model=FrameDetectionsResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_frame_detections(
        dataset_id: int,
        frame_id: str,
        run_id: int | None = None,
    ) -> FrameDetectionsResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            try:
                run_record, detections = repository.list_detections_for_frame(
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    run_id=run_id,
                    run_type=DETECTION_RUN_TYPE,
                )
            except KeyError as error:
                missing_run_id = run_id if run_id is not None else "latest"
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=(
                        f"Detection run {missing_run_id} was not found for dataset "
                        f"{dataset_id}."
                    ),
                ) from error

        return FrameDetectionsResponse(
            frame_id=frame_id,
            run=InferenceRunRecord.model_validate(run_record),
            detections=[
                DetectionRecord.model_validate(detection) for detection in detections
            ],
        )

    @app.post(
        "/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        response_model=DetectionCorrectionResponse,
        status_code=HTTPStatus.OK,
    )
    async def save_detection_correction(
        dataset_id: int,
        frame_id: str,
        detection_id: int,
        request: SaveCorrectionRequest,
    ) -> DetectionCorrectionResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                frame_record = repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            try:
                original_detection = repository.get_detection(
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    detection_id=detection_id,
                )
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=(
                        f"Detection {detection_id} was not found in frame {frame_id} "
                        f"for dataset {dataset_id}."
                    ),
                ) from error

            corrected_class_name: str | None = None
            corrected_x_min: float | None = None
            corrected_y_min: float | None = None
            corrected_x_max: float | None = None
            corrected_y_max: float | None = None

            if request.corrected_detection is not None:
                corrected_class_name = (
                    request.corrected_detection.class_name
                    or str(original_detection["class_name"])
                )
                corrected_x_min = (
                    float(request.corrected_detection.x_min)
                    if request.corrected_detection.x_min is not None
                    else float(original_detection["x_min"])
                )
                corrected_y_min = (
                    float(request.corrected_detection.y_min)
                    if request.corrected_detection.y_min is not None
                    else float(original_detection["y_min"])
                )
                corrected_x_max = (
                    float(request.corrected_detection.x_max)
                    if request.corrected_detection.x_max is not None
                    else float(original_detection["x_max"])
                )
                corrected_y_max = (
                    float(request.corrected_detection.y_max)
                    if request.corrected_detection.y_max is not None
                    else float(original_detection["y_max"])
                )

                try:
                    validate_bbox_coordinates(
                        x_min=corrected_x_min,
                        y_min=corrected_y_min,
                        x_max=corrected_x_max,
                        y_max=corrected_y_max,
                        image_width=int(frame_record["image_width"]),
                        image_height=int(frame_record["image_height"]),
                    )
                except ValueError as error:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail=str(error),
                    ) from error

            correction_record = repository.save_correction(
                dataset_id=dataset_id,
                frame_id=frame_id,
                detection_id=detection_id,
                review_status=request.review_status,
                corrected_class_name=corrected_class_name,
                corrected_x_min=corrected_x_min,
                corrected_y_min=corrected_y_min,
                corrected_x_max=corrected_x_max,
                corrected_y_max=corrected_y_max,
                saved_at=utc_now_isoformat(),
            )

        return DetectionCorrectionResponse(
            correction=build_correction_response_record(correction_record)
        )

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}/corrections",
        response_model=FrameCorrectionsResponse,
        status_code=HTTPStatus.OK,
    )
    async def get_frame_corrections(
        dataset_id: int,
        frame_id: str,
        run_id: int | None = None,
    ) -> FrameCorrectionsResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

            try:
                run_record, correction_records = repository.list_corrections_for_frame(
                    dataset_id=dataset_id,
                    frame_id=frame_id,
                    run_id=run_id,
                    run_type=DETECTION_RUN_TYPE,
                )
            except KeyError as error:
                missing_run_id = run_id if run_id is not None else "latest"
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=(
                        f"Detection run {missing_run_id} was not found for dataset "
                        f"{dataset_id}."
                    ),
                ) from error

        return FrameCorrectionsResponse(
            frame_id=frame_id,
            run=InferenceRunRecord.model_validate(run_record),
            corrections=[
                build_correction_response_record(correction_record)
                for correction_record in correction_records
            ],
        )

    @app.get(
        "/datasets/{dataset_id}/frames/{frame_id}/preview",
        name="get_frame_preview",
        status_code=HTTPStatus.OK,
    )
    async def get_frame_preview(dataset_id: int, frame_id: str) -> FileResponse:
        with closing(create_connection(app.state.database_path)) as connection:
            repository = DatasetRepository(connection)
            try:
                frame_record = repository.get_frame(dataset_id, frame_id)
            except KeyError as error:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Frame {frame_id} was not found in dataset {dataset_id}.",
                ) from error

        dataset_source_path = Path(str(frame_record["dataset_source_path"])).resolve()
        preview_path = dataset_source_path.joinpath(str(frame_record["image_path"])).resolve()

        if dataset_source_path not in preview_path.parents:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Frame {frame_id} preview path is invalid for dataset {dataset_id}.",
            )

        if not preview_path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Frame {frame_id} preview image was not found in dataset {dataset_id}.",
            )

        return FileResponse(preview_path)

    return app


app = create_app()
