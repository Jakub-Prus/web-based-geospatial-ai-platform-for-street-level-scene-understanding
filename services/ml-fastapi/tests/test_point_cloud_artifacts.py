from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.inference import DepthPrediction
from conftest import create_sample_dataset, load_sample_dataset

FRAME_ID = "20190401121727_camera_frontright_000013460"


def test_point_cloud_generation_returns_stable_payload_in_camera_local_coordinates(
    tmp_path: Path,
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDepthEstimator:
        def estimate(self, image_path: Path) -> DepthPrediction:
            assert image_path.name == f"{FRAME_ID}.png"
            return DepthPrediction(
                depth_map=np.array(
                    [
                        [1.0, 2.0, 4.0, 8.0],
                        [1.0, 1.0, 1.0, 1.0],
                    ],
                    dtype=np.float32,
                )
            )

    sample_dataset = create_sample_dataset(
        root_path=tmp_path,
        camera_name="custom",
        image_width=4,
        image_height=2,
    )
    client = test_client_factory(
        depth_estimator_factory=lambda _model_path: FakeDepthEstimator()
    )
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="point-cloud-test-dataset",
    )

    depth_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth",
        json={},
    )
    assert depth_response.status_code == 201
    assert depth_response.json()["state"] == "completed"

    first_point_cloud_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/point-cloud",
        json={"max_point_count": 8},
    )

    assert first_point_cloud_response.status_code == 201
    first_payload = first_point_cloud_response.json()
    assert first_payload["state"] == "completed"
    assert first_payload["run"]["run_type"] == "point_cloud"
    assert first_payload["artifact"]["coordinate_system"] == (
        "camera_local_right_handed_x_right_y_up_z_forward"
    )
    assert first_payload["artifact"]["point_count"] == 8
    assert first_payload["artifact"]["source_point_count"] == 8
    assert first_payload["artifact"]["subsample_step"] == 1
    assert first_payload["artifact"]["intrinsics_source"] == "fallback_pinhole"
    assert first_payload["artifact"]["fx"] == 4.0
    assert first_payload["artifact"]["fy"] == 4.0
    assert first_payload["artifact"]["cx"] == 2.0
    assert first_payload["artifact"]["cy"] == 1.0
    assert len(first_payload["payload"]["points"]) == 8
    assert first_payload["payload"]["points"][0] == {
        "x": -0.375,
        "y": 0.125,
        "z": 1.0,
    }
    assert first_payload["payload"]["points"][-1] == {
        "x": 0.375,
        "y": -0.125,
        "z": 1.0,
    }

    get_response = client.get(f"/datasets/{dataset_id}/frames/{FRAME_ID}/point-cloud")

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["state"] == "completed"
    assert get_payload["payload"]["points"] == first_payload["payload"]["points"]

    second_point_cloud_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/point-cloud",
        json={"max_point_count": 8},
    )

    assert second_point_cloud_response.status_code == 201
    second_payload = second_point_cloud_response.json()
    assert second_payload["payload"]["points"] == first_payload["payload"]["points"]


def test_point_cloud_generation_filters_invalid_inverse_depth_values_and_caps_point_count(
    tmp_path: Path,
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDepthEstimator:
        def estimate(self, image_path: Path) -> DepthPrediction:
            assert image_path.name == f"{FRAME_ID}.png"
            return DepthPrediction(
                depth_map=np.array(
                    [
                        [np.inf, 1.0, 0.0, -1.0],
                        [2.0, 4.0, 8.0, 16.0],
                    ],
                    dtype=np.float32,
                )
            )

    sample_dataset = create_sample_dataset(
        root_path=tmp_path,
        camera_name="custom",
        image_width=4,
        image_height=2,
    )
    client = test_client_factory(
        depth_estimator_factory=lambda _model_path: FakeDepthEstimator()
    )
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="point-cloud-filtering-test-dataset",
    )

    depth_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/depth",
        json={},
    )
    assert depth_response.status_code == 201
    assert depth_response.json()["state"] == "completed"

    point_cloud_response = client.post(
        f"/datasets/{dataset_id}/frames/{FRAME_ID}/point-cloud",
        json={"max_point_count": 2},
    )

    assert point_cloud_response.status_code == 201
    payload = point_cloud_response.json()
    assert payload["state"] == "completed"
    assert payload["artifact"]["source_point_count"] == 5
    assert payload["artifact"]["point_count"] == 2
    assert payload["artifact"]["subsample_step"] == 3
    assert payload["payload"]["points"] == [
        {"x": -0.125, "y": 0.125, "z": 1.0},
        {"x": 0.015625, "y": -0.015625, "z": 0.125},
    ]


def test_point_cloud_endpoint_returns_missing_state_when_depth_artifact_does_not_exist(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    client = test_client_factory()
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="point-cloud-missing-depth-dataset",
    )

    response = client.get(f"/datasets/{dataset_id}/frames/{FRAME_ID}/point-cloud")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "missing"
    assert payload["run"] is None
    assert payload["artifact"] is None
    assert payload["payload"] is None
    assert "Generate depth first" in payload["detail"]
