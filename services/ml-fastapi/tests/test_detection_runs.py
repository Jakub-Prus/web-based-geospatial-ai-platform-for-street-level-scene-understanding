from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from app.inference import DetectionPrediction


def _load_sample_dataset(
    client: TestClient,
    sample_dataset: tuple[Path, Path],
) -> int:
    dataset_path, preview_archive_path = sample_dataset
    response = client.post(
        "/datasets/load",
        json={
            "dataset_path": str(dataset_path),
            "preview_archive_path": str(preview_archive_path),
            "dataset_name": "detection-test-dataset",
        },
    )

    assert response.status_code == 201
    return int(response.json()["dataset"]["id"])


def test_detection_run_persists_run_status_and_frame_detections(
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
                        confidence_score=0.92,
                        x_min=-5.0,
                        y_min=-2.0,
                        x_max=24.0,
                        y_max=14.0,
                    )
                ],
                [],
            ]

    client = test_client_factory(detector_factory=lambda _model_path: FakeDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)

    trigger_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})

    assert trigger_response.status_code == 201
    run_payload = trigger_response.json()["run"]
    assert run_payload["status"] == "completed"
    assert run_payload["frame_count"] == 2
    assert run_payload["processed_frame_count"] == 2
    assert run_payload["detection_count"] == 1
    assert run_payload["model_name"] == "yolo11n"

    run_id = run_payload["id"]
    status_response = client.get(f"/runs/{run_id}/status")

    assert status_response.status_code == 200
    assert status_response.json()["run"]["status"] == "completed"

    frame_id = "20190401121727_camera_frontright_000013460"
    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )

    assert detections_response.status_code == 200
    detections_payload = detections_response.json()
    assert detections_payload["run"]["id"] == run_id
    assert len(detections_payload["detections"]) == 1
    assert detections_payload["detections"][0]["class_name"] == "car"
    assert detections_payload["detections"][0]["x_min"] == 0.0
    assert detections_payload["detections"][0]["y_min"] == 0.0
    assert detections_payload["detections"][0]["x_max"] == 1.0
    assert detections_payload["detections"][0]["y_max"] == 1.0


def test_detection_run_records_empty_state_when_no_objects_are_found(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class EmptyDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            return [[] for _ in image_paths]

    client = test_client_factory(detector_factory=lambda _model_path: EmptyDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)

    trigger_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})

    assert trigger_response.status_code == 201
    run_payload = trigger_response.json()["run"]
    assert run_payload["status"] == "empty"
    assert run_payload["detection_count"] == 0
    assert run_payload["processed_frame_count"] == 2

    frame_id = "20190401121727_camera_frontright_000013460"
    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )

    assert detections_response.status_code == 200
    assert detections_response.json()["run"]["status"] == "empty"
    assert detections_response.json()["detections"] == []


def test_detection_run_records_failed_state_when_detector_raises(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FailingDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            raise RuntimeError("synthetic detector failure")

    client = test_client_factory(detector_factory=lambda _model_path: FailingDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)

    trigger_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})

    assert trigger_response.status_code == 201
    run_payload = trigger_response.json()["run"]
    assert run_payload["status"] == "failed"
    assert run_payload["processed_frame_count"] == 0
    assert run_payload["detection_count"] == 0
    assert "synthetic detector failure" in run_payload["error_message"]

    run_id = run_payload["id"]
    run_response = client.get(f"/runs/{run_id}")

    assert run_response.status_code == 200
    assert run_response.json()["run"]["status"] == "failed"
