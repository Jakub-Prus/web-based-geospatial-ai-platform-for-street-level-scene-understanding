from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_POINT_CLOUD_ARTIFACT_FORMAT = "float32_npz_xyz"
POINT_CLOUD_COORDINATE_SYSTEM = "camera_local_right_handed_x_right_y_up_z_forward"
INTRINSICS_SOURCE_FRAME_METADATA = "frame_metadata"
INTRINSICS_SOURCE_FALLBACK_PINHOLE = "fallback_pinhole"
DEFAULT_MAX_POINT_COUNT = 20_000
MAX_POINT_COUNT = 100_000
MINIMUM_INVERSE_DEPTH_VALUE = 1e-6
PIXEL_CENTER_OFFSET = 0.5
CAMERA_INTRINSICS_MATRIX_ROWS = 3
CAMERA_INTRINSICS_MATRIX_COLUMNS = 3


@dataclass(frozen=True)
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    source: str


@dataclass(frozen=True)
class PointCloudConversionResult:
    points: np.ndarray
    source_point_count: int
    point_count: int
    subsample_step: int
    intrinsics: CameraIntrinsics


def resolve_camera_intrinsics(
    *,
    camera_intrinsics_json: str | None,
    image_width: int,
    image_height: int,
) -> CameraIntrinsics:
    if camera_intrinsics_json:
        parsed_intrinsics = _parse_camera_intrinsics(camera_intrinsics_json)
        if parsed_intrinsics is not None:
            return parsed_intrinsics

    return CameraIntrinsics(
        fx=float(image_width),
        fy=float(image_width),
        cx=float(image_width) / 2.0,
        cy=float(image_height) / 2.0,
        source=INTRINSICS_SOURCE_FALLBACK_PINHOLE,
    )


def convert_depth_map_to_point_cloud(
    *,
    depth_map: np.ndarray,
    intrinsics: CameraIntrinsics,
    max_point_count: int = DEFAULT_MAX_POINT_COUNT,
) -> PointCloudConversionResult:
    depth_values = np.asarray(depth_map, dtype=np.float32)
    if depth_values.ndim != 2:
        raise ValueError("Point-cloud conversion requires a single-channel depth map.")

    valid_mask = np.isfinite(depth_values) & (depth_values > MINIMUM_INVERSE_DEPTH_VALUE)
    source_point_count = int(np.count_nonzero(valid_mask))
    if source_point_count == 0:
        raise ValueError(
            "Stored depth artifact did not contain any positive finite inverse-depth values."
        )

    resolved_max_point_count = max(1, min(int(max_point_count), MAX_POINT_COUNT))
    subsample_step = max(1, math.ceil(source_point_count / resolved_max_point_count))

    valid_rows, valid_columns = np.nonzero(valid_mask)
    sampled_indices = slice(None, None, subsample_step)
    sampled_rows = valid_rows[sampled_indices].astype(np.float32, copy=False)
    sampled_columns = valid_columns[sampled_indices].astype(np.float32, copy=False)
    sampled_inverse_depth = depth_values[
        valid_rows[sampled_indices],
        valid_columns[sampled_indices],
    ].astype(np.float32, copy=False)

    z_coordinates = np.float32(1.0) / sampled_inverse_depth
    u_coordinates = sampled_columns + np.float32(PIXEL_CENTER_OFFSET)
    v_coordinates = sampled_rows + np.float32(PIXEL_CENTER_OFFSET)
    x_coordinates = ((u_coordinates - intrinsics.cx) * z_coordinates) / intrinsics.fx
    y_coordinates = ((intrinsics.cy - v_coordinates) * z_coordinates) / intrinsics.fy

    points = np.column_stack(
        (
            x_coordinates.astype(np.float32, copy=False),
            y_coordinates.astype(np.float32, copy=False),
            z_coordinates.astype(np.float32, copy=False),
        )
    )

    return PointCloudConversionResult(
        points=points.astype(np.float32, copy=False),
        source_point_count=source_point_count,
        point_count=int(points.shape[0]),
        subsample_step=subsample_step,
        intrinsics=intrinsics,
    )


def build_point_cloud_artifact_uri(
    *,
    dataset_id: int,
    frame_id: str,
    run_id: int,
) -> str:
    safe_frame_id = frame_id.replace("/", "_").replace("\\", "_")
    return (
        Path(f"dataset-{dataset_id}")
        / safe_frame_id
        / f"run-{run_id}.npz"
    ).as_posix()


def persist_point_cloud_artifact(
    *,
    point_cloud_artifacts_directory: Path,
    dataset_id: int,
    frame_id: str,
    run_id: int,
    points: np.ndarray,
) -> str:
    point_cloud_uri = build_point_cloud_artifact_uri(
        dataset_id=dataset_id,
        frame_id=frame_id,
        run_id=run_id,
    )
    artifact_path = point_cloud_artifacts_directory / point_cloud_uri
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        artifact_path,
        points=np.asarray(points, dtype=np.float32),
    )
    return point_cloud_uri


def load_point_cloud_artifact(
    *,
    point_cloud_artifacts_directory: Path,
    point_cloud_uri: str,
) -> np.ndarray:
    artifact_path = (point_cloud_artifacts_directory / point_cloud_uri).resolve()
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Point-cloud artifact file was not found: {artifact_path}"
        )

    with np.load(artifact_path) as loaded_artifact:
        points = np.asarray(loaded_artifact["points"], dtype=np.float32)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("Stored point-cloud artifact must contain an Nx3 float32 array.")
    if not np.isfinite(points).all():
        raise ValueError("Stored point-cloud artifact contains non-finite coordinates.")

    return points


def _parse_camera_intrinsics(camera_intrinsics_json: str) -> CameraIntrinsics | None:
    try:
        parsed_payload = json.loads(camera_intrinsics_json)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed_payload, dict):
        return _parse_camera_intrinsics_dict(parsed_payload)
    if isinstance(parsed_payload, list):
        return _parse_camera_intrinsics_matrix(parsed_payload)

    return None


def _parse_camera_intrinsics_dict(
    intrinsics_payload: dict[str, Any],
) -> CameraIntrinsics | None:
    if {"fx", "fy", "cx", "cy"}.issubset(intrinsics_payload):
        return _build_camera_intrinsics(
            fx=intrinsics_payload["fx"],
            fy=intrinsics_payload["fy"],
            cx=intrinsics_payload["cx"],
            cy=intrinsics_payload["cy"],
        )

    camera_matrix = intrinsics_payload.get("CamMatrix")
    if isinstance(camera_matrix, list):
        return _parse_camera_intrinsics_matrix(camera_matrix)

    return None


def _parse_camera_intrinsics_matrix(
    intrinsics_matrix: list[Any],
) -> CameraIntrinsics | None:
    if len(intrinsics_matrix) != CAMERA_INTRINSICS_MATRIX_ROWS:
        return None

    if not all(isinstance(row, list) for row in intrinsics_matrix):
        return None

    if not all(len(row) == CAMERA_INTRINSICS_MATRIX_COLUMNS for row in intrinsics_matrix):
        return None

    return _build_camera_intrinsics(
        fx=intrinsics_matrix[0][0],
        fy=intrinsics_matrix[1][1],
        cx=intrinsics_matrix[0][2],
        cy=intrinsics_matrix[1][2],
    )


def _build_camera_intrinsics(
    *,
    fx: Any,
    fy: Any,
    cx: Any,
    cy: Any,
) -> CameraIntrinsics | None:
    try:
        resolved_fx = float(fx)
        resolved_fy = float(fy)
        resolved_cx = float(cx)
        resolved_cy = float(cy)
    except (TypeError, ValueError):
        return None

    if resolved_fx <= 0.0 or resolved_fy <= 0.0:
        return None

    if not np.isfinite(
        np.array([resolved_fx, resolved_fy, resolved_cx, resolved_cy], dtype=np.float32)
    ).all():
        return None

    return CameraIntrinsics(
        fx=resolved_fx,
        fy=resolved_fy,
        cx=resolved_cx,
        cy=resolved_cy,
        source=INTRINSICS_SOURCE_FRAME_METADATA,
    )
