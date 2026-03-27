from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.a2d2_parser import A2D2SubsetParser, DatasetValidationError
from app.config import (
    resolve_database_path,
    resolve_default_dataset_path,
    resolve_default_detection_model_path,
    resolve_preview_archive_path,
)
from app.database import create_connection, initialize_database
from app.inference import (
    DETECTION_RUN_TYPE,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_EMPTY,
    RUN_STATUS_RUNNING,
    DetectionPrediction,
    ObjectDetector,
    UltralyticsObjectDetector,
)
from app.repository import DatasetRepository
from app.schemas import (
    DatasetListResponse,
    DatasetLoadRequest,
    DatasetLoadResponse,
    DatasetRecord,
    DetectionRecord,
    DetectionRunRequest,
    DetectionRunResponse,
    FrameDetailRecord,
    FrameDetailResponse,
    FrameDetectionsResponse,
    FrameListResponse,
    InferenceRunRecord,
)

SERVICE_NAME = "ml-fastapi"
SERVICE_DESCRIPTION = "Machine-learning facing API scaffold for the geospatial scene demo."
SERVICE_STATUS = "ok"
SERVICE_VERSION = "0.1.0"
DEFAULT_DATASET_NAME = "a2d2-subset"
MINIMUM_IMAGE_COORDINATE = 0.0
DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

DetectorFactory = Callable[[Path], ObjectDetector]


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


def create_app(detector_factory: DetectorFactory | None = None) -> FastAPI:
    database_path = resolve_database_path()
    initialize_database(database_path)

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
