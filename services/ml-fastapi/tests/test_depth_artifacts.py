from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.inference import DepthPrediction
from conftest import load_sample_dataset

FRAME_ID = "20190401121727_camera_frontright_000013460"


def test_depth_artifact_persists_for_one_frame_with_matching_dimensions(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
    tmp_path: Path,
) -> None:
    class FakeDepthEstimator:
        def estimate(self, image_path: Path) -> DepthPrediction:
            assert image_path.name == f"{FRAME_ID}.png"
            return DepthPrediction(depth_map=np.array([[0.42]], dtype=np.float32))

    depth_artifacts_directory = tmp_path / "persisted-depth"
    client = test_client_factory(
        depth_estimator_factory=lambda _model_path: FakeDepthEstimator(),
        depth_artifacts_directory=depth_artifacts_directory,
    )
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="depth-test-dataset",
    )

    trigger_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth",
        json={},
    )

    assert trigger_response.status_code == 201
    payload = trigger_response.json()
    assert payload["state"] == "completed"
    assert payload["run"]["run_type"] == "depth"
    assert payload["run"]["frame_id"] == FRAME_ID
    assert payload["run"]["status"] == "completed"
    assert payload["artifact"]["width"] == 1
    assert payload["artifact"]["height"] == 1
    assert payload["artifact"]["depth_format"] == "float32_npy_inverse_depth"
    assert payload["artifact"]["depth_scale"] == 1.0

    stored_depth_path = depth_artifacts_directory / payload["artifact"]["depth_uri"]
    assert stored_depth_path.is_file()

    stored_depth_map = np.load(stored_depth_path)
    assert stored_depth_map.shape == (1, 1)
    assert stored_depth_map[0, 0] == np.float32(0.42)

    get_response = client.get(f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth")

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["state"] == "completed"
    assert get_payload["artifact"]["depth_uri"] == payload["artifact"]["depth_uri"]


def test_depth_artifact_reports_failed_state_for_dimension_mismatch(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class MismatchedDepthEstimator:
        def estimate(self, image_path: Path) -> DepthPrediction:
            assert image_path.name == f"{FRAME_ID}.png"
            return DepthPrediction(depth_map=np.ones((2, 1), dtype=np.float32))

    client = test_client_factory(
        depth_estimator_factory=lambda _model_path: MismatchedDepthEstimator()
    )
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="depth-test-dataset",
    )

    trigger_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth",
        json={},
    )

    assert trigger_response.status_code == 201
    payload = trigger_response.json()
    assert payload["state"] == "failed"
    assert payload["run"]["status"] == "failed"
    assert payload["artifact"] is None
    assert "did not match source image dimensions" in payload["detail"]

    get_response = client.get(f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth")

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["state"] == "failed"
    assert "did not match source image dimensions" in get_payload["detail"]


def test_depth_artifact_endpoint_returns_missing_fallback_when_no_depth_exists(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    client = test_client_factory()
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="depth-test-dataset",
    )

    response = client.get(f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "missing"
    assert payload["run"] is None
    assert payload["artifact"] is None
    assert "No depth artifact has been generated" in payload["detail"]
