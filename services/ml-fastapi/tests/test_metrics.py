from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.inference import DetectionPrediction
from conftest import load_sample_dataset


def test_dataset_metrics_are_empty_before_a_detection_run(
    sample_dataset: tuple[Path, Path],
    test_client: TestClient,
) -> None:
    dataset_id = load_sample_dataset(
        test_client,
        sample_dataset,
        dataset_name="metrics-test-dataset",
    )

    response = test_client.get(f"/datasets/{dataset_id}/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["run"] is None
    assert payload["metrics"]["detection_count"] == 0
    assert payload["metrics"]["average_confidence_score"] is None
    assert payload["metrics"]["correction_count"] == 0
    assert payload["metrics"]["correction_rate"] == 0.0


def test_dataset_metrics_change_after_detection_run_and_correction(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            assert len(image_paths) == 2
            return [
                [
                    DetectionPrediction(
                        class_name="car",
                        confidence_score=0.9,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
                [
                    DetectionPrediction(
                        class_name="traffic_sign",
                        confidence_score=0.6,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
            ]

    client = test_client_factory(detector_factory=lambda _model_path: FakeDetector())
    dataset_id = load_sample_dataset(
        client,
        sample_dataset,
        dataset_name="metrics-test-dataset",
    )
    frame_id = "20190401121727_camera_frontright_000013460"

    before_run_response = client.get(f"/datasets/{dataset_id}/metrics")

    assert before_run_response.status_code == 200
    assert before_run_response.json()["metrics"]["detection_count"] == 0
    assert before_run_response.json()["metrics"]["correction_count"] == 0

    run_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})

    assert run_response.status_code == 201
    run_id = int(run_response.json()["run"]["id"])

    after_run_response = client.get(f"/datasets/{dataset_id}/metrics")

    assert after_run_response.status_code == 200
    after_run_payload = after_run_response.json()
    assert after_run_payload["run"]["id"] == run_id
    assert after_run_payload["metrics"]["detection_count"] == 2
    assert after_run_payload["metrics"]["average_confidence_score"] == pytest.approx(
        0.75
    )
    assert after_run_payload["metrics"]["correction_count"] == 0
    assert after_run_payload["metrics"]["correction_rate"] == 0.0

    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )

    assert detections_response.status_code == 200
    detection_id = int(detections_response.json()["detections"][0]["id"])

    correction_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={
            "review_status": "approved",
            "corrected_detection": {
                "class_name": "van",
                "x_min": 0.0,
                "y_min": 0.0,
                "x_max": 1.0,
                "y_max": 1.0,
            },
        },
    )

    assert correction_response.status_code == 200

    after_correction_response = client.get(f"/datasets/{dataset_id}/metrics")

    assert after_correction_response.status_code == 200
    after_correction_payload = after_correction_response.json()
    assert after_correction_payload["run"]["id"] == run_id
    assert after_correction_payload["metrics"]["detection_count"] == 2
    assert after_correction_payload["metrics"][
        "average_confidence_score"
    ] == pytest.approx(0.75)
    assert after_correction_payload["metrics"]["correction_count"] == 1
    assert after_correction_payload["metrics"]["correction_rate"] == pytest.approx(
        0.5
    )
