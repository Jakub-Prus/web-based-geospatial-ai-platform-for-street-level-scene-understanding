from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
SERVICE_DIR = APP_DIR.parent
SERVICES_DIR = SERVICE_DIR.parent
REPO_ROOT = SERVICES_DIR.parent

DEFAULT_DATASET_PATH = REPO_ROOT / "data" / "raw" / "a2d2-subset"
DEFAULT_PREVIEW_ARCHIVE_PATH = REPO_ROOT / "data" / "raw" / "a2d2-preview.tar"
DEFAULT_DETECTION_MODEL_PATH = REPO_ROOT / "data" / "raw" / "models" / "yolo11n.pt"
DEFAULT_DEPTH_MODEL_PATH = REPO_ROOT / "data" / "raw" / "models" / "dpt_swin2_tiny_256.pt"
DEFAULT_DB_DIRECTORY = SERVICE_DIR / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIRECTORY / "platform.db"
DEFAULT_DEPTH_ARTIFACTS_DIRECTORY = DEFAULT_DB_DIRECTORY / "depth-artifacts"
DEFAULT_POINT_CLOUD_ARTIFACTS_DIRECTORY = DEFAULT_DB_DIRECTORY / "point-cloud-artifacts"


def resolve_database_path() -> Path:
    configured_path = os.getenv("ML_FASTAPI_DB_PATH")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_DB_PATH


def resolve_default_dataset_path() -> Path:
    configured_path = os.getenv("A2D2_SUBSET_PATH")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_DATASET_PATH


def resolve_preview_archive_path() -> Path:
    configured_path = os.getenv("A2D2_PREVIEW_ARCHIVE_PATH")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_PREVIEW_ARCHIVE_PATH


def resolve_default_detection_model_path() -> Path:
    configured_path = os.getenv("YOLO_DETECTION_MODEL_PATH")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_DETECTION_MODEL_PATH


def resolve_default_depth_model_path() -> Path:
    configured_path = os.getenv("MIDAS_DEPTH_MODEL_PATH")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_DEPTH_MODEL_PATH


def resolve_depth_artifacts_directory() -> Path:
    configured_path = os.getenv("ML_FASTAPI_DEPTH_ARTIFACTS_DIR")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_DEPTH_ARTIFACTS_DIRECTORY


def resolve_point_cloud_artifacts_directory() -> Path:
    configured_path = os.getenv("ML_FASTAPI_POINT_CLOUD_ARTIFACTS_DIR")
    if configured_path:
        return Path(configured_path).resolve()

    return DEFAULT_POINT_CLOUD_ARTIFACTS_DIRECTORY
