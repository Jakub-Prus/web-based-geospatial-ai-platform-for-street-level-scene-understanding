from __future__ import annotations

from contextlib import closing
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.a2d2_parser import A2D2SubsetParser, DatasetValidationError
from app.config import (
    resolve_database_path,
    resolve_default_dataset_path,
    resolve_preview_archive_path,
)
from app.database import create_connection, initialize_database
from app.repository import DatasetRepository
from app.schemas import (
    DatasetListResponse,
    DatasetLoadRequest,
    DatasetLoadResponse,
    DatasetRecord,
    FrameListResponse,
)

SERVICE_NAME = "ml-fastapi"
SERVICE_DESCRIPTION = "Machine-learning facing API scaffold for the geospatial scene demo."
SERVICE_STATUS = "ok"
SERVICE_VERSION = "0.1.0"
DEFAULT_DATASET_NAME = "a2d2-subset"


def build_service_payload() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "description": SERVICE_DESCRIPTION,
        "status": SERVICE_STATUS,
        "version": SERVICE_VERSION,
    }


def create_app() -> FastAPI:
    database_path = resolve_database_path()
    initialize_database(database_path)

    app = FastAPI(
        title="Geospatial Scene ML API",
        version=SERVICE_VERSION,
        description=SERVICE_DESCRIPTION,
    )
    app.state.database_path = database_path

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

    return app


app = create_app()
