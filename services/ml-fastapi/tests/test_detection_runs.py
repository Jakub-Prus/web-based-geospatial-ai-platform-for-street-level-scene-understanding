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


def test_detection_correction_persists_across_reload_and_preserves_original_detection(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
    tmp_path: Path,
) -> None:
    class FakeDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            assert len(image_paths) == 2
            return [
                [
                    DetectionPrediction(
                        class_name="car",
                        confidence_score=0.92,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
                [],
            ]

    database_path = tmp_path / "slice-8-persistence.db"
    client = test_client_factory(
        detector_factory=lambda _model_path: FakeDetector(),
        database_path=database_path,
    )
    dataset_id = _load_sample_dataset(client, sample_dataset)
    frame_id = "20190401121727_camera_frontright_000013460"

    run_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})
    assert run_response.status_code == 201
    run_id = int(run_response.json()["run"]["id"])

    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )
    assert detections_response.status_code == 200
    original_detection = detections_response.json()["detections"][0]
    detection_id = int(original_detection["id"])

    save_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={
            "review_status": "approved",
            "corrected_detection": {
                "class_name": "van",
                "x_min": 0.1,
                "y_min": 0.2,
                "x_max": 0.9,
                "y_max": 0.95,
            },
        },
    )

    assert save_response.status_code == 200
    correction_payload = save_response.json()["correction"]
    assert correction_payload["review_status"] == "approved"
    assert correction_payload["original_detection"]["source"] == "original"
    assert correction_payload["original_detection"]["class_name"] == "car"
    assert correction_payload["corrected_detection"]["source"] == "corrected"
    assert correction_payload["corrected_detection"]["class_name"] == "van"
    assert correction_payload["effective_detection"]["source"] == "corrected"
    assert correction_payload["effective_detection"]["x_min"] == 0.1
    assert correction_payload["effective_detection"]["y_max"] == 0.95

    reloaded_client = test_client_factory(database_path=database_path)
    corrections_response = reloaded_client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/corrections",
        params={"run_id": run_id},
    )

    assert corrections_response.status_code == 200
    corrections_payload = corrections_response.json()
    assert corrections_payload["run"]["id"] == run_id
    assert len(corrections_payload["corrections"]) == 1
    reloaded_correction = corrections_payload["corrections"][0]
    assert reloaded_correction["detection_id"] == detection_id
    assert reloaded_correction["corrected_detection"]["class_name"] == "van"
    assert reloaded_correction["effective_detection"]["class_name"] == "van"
    assert reloaded_correction["original_detection"]["class_name"] == "car"

    original_after_reload = reloaded_client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections",
        params={"run_id": run_id},
    )

    assert original_after_reload.status_code == 200
    assert original_after_reload.json()["detections"][0]["class_name"] == "car"


def test_detection_correction_supports_review_status_updates_without_losing_original_bbox(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            return [
                [
                    DetectionPrediction(
                        class_name="car",
                        confidence_score=0.92,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
                [],
            ]

    client = test_client_factory(detector_factory=lambda _model_path: FakeDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)
    frame_id = "20190401121727_camera_frontright_000013460"

    run_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})
    assert run_response.status_code == 201

    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )
    detection_id = int(detections_response.json()["detections"][0]["id"])

    rejected_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={"review_status": "rejected"},
    )

    assert rejected_response.status_code == 200
    rejected_payload = rejected_response.json()["correction"]
    correction_id = rejected_payload["id"]
    assert rejected_payload["review_status"] == "rejected"
    assert rejected_payload["corrected_detection"] is None
    assert rejected_payload["effective_detection"] is None
    assert rejected_payload["original_detection"]["class_name"] == "car"

    pending_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={
            "review_status": "pending",
            "corrected_detection": {
                "class_name": "truck",
            },
        },
    )

    assert pending_response.status_code == 200
    pending_payload = pending_response.json()["correction"]
    assert pending_payload["id"] == correction_id
    assert pending_payload["review_status"] == "pending"
    assert pending_payload["corrected_detection"]["class_name"] == "truck"
    assert pending_payload["corrected_detection"]["x_min"] == 0.0
    assert pending_payload["corrected_detection"]["y_min"] == 0.0
    assert pending_payload["corrected_detection"]["x_max"] == 1.0
    assert pending_payload["corrected_detection"]["y_max"] == 1.0
    assert pending_payload["effective_detection"]["source"] == "corrected"


def test_detection_correction_rejects_invalid_bbox_coordinates(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            return [
                [
                    DetectionPrediction(
                        class_name="car",
                        confidence_score=0.92,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
                [],
            ]

    client = test_client_factory(detector_factory=lambda _model_path: FakeDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)
    frame_id = "20190401121727_camera_frontright_000013460"

    run_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})
    assert run_response.status_code == 201

    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )
    detection_id = int(detections_response.json()["detections"][0]["id"])

    invalid_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={
            "review_status": "approved",
            "corrected_detection": {
                "x_min": 0.9,
                "y_min": 0.2,
                "x_max": 0.4,
                "y_max": 0.8,
            },
        },
    )

    assert invalid_response.status_code == 400
    assert "x_min <= x_max" in invalid_response.json()["detail"]


def test_detection_correction_rejects_empty_pending_payload(
    sample_dataset: tuple[Path, Path],
    test_client_factory: Callable[..., TestClient],
) -> None:
    class FakeDetector:
        def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
            return [
                [
                    DetectionPrediction(
                        class_name="car",
                        confidence_score=0.92,
                        x_min=0.0,
                        y_min=0.0,
                        x_max=1.0,
                        y_max=1.0,
                    )
                ],
                [],
            ]

    client = test_client_factory(detector_factory=lambda _model_path: FakeDetector())
    dataset_id = _load_sample_dataset(client, sample_dataset)
    frame_id = "20190401121727_camera_frontright_000013460"

    run_response = client.post(f"/datasets/{dataset_id}/runs/detect", json={})
    assert run_response.status_code == 201

    detections_response = client.get(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections"
    )
    detection_id = int(detections_response.json()["detections"][0]["id"])

    empty_response = client.post(
        f"/datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction",
        json={},
    )

    assert empty_response.status_code == 422
    assert "explicit non-pending review status" in str(empty_response.json()["detail"])
