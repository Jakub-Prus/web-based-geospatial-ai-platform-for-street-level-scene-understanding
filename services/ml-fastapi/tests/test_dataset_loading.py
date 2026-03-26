from __future__ import annotations

from pathlib import Path


def test_load_dataset_persists_and_returns_frame_metadata(
    sample_dataset: tuple[Path, Path],
    test_client,
) -> None:
    dataset_path, preview_archive_path = sample_dataset

    load_response = test_client.post(
        "/datasets/load",
        json={
            "dataset_path": str(dataset_path),
            "preview_archive_path": str(preview_archive_path),
            "dataset_name": "test-a2d2-subset",
        },
    )

    assert load_response.status_code == 201
    payload = load_response.json()
    assert payload["loaded_frame_count"] == 2
    assert payload["dataset"]["frame_count"] == 2
    assert payload["dataset"]["camera_name"] == "front_right"

    datasets_response = test_client.get("/datasets")

    assert datasets_response.status_code == 200
    datasets_payload = datasets_response.json()
    assert len(datasets_payload["datasets"]) == 1

    dataset_id = payload["dataset"]["id"]
    frames_response = test_client.get(f"/datasets/{dataset_id}/frames")

    assert frames_response.status_code == 200
    frames_payload = frames_response.json()
    assert len(frames_payload["frames"]) == 2
    assert frames_payload["frames"][0]["latitude"] > 48.145
    assert frames_payload["frames"][0]["longitude"] > 11.566
    assert frames_payload["frames"][0]["image_width"] == 1
    assert frames_payload["frames"][0]["image_height"] == 1
    assert frames_payload["frames"][0]["heading_degrees"] > 0
    assert frames_payload["frames"][0]["camera_intrinsics_json"] is not None


def test_load_dataset_rejects_missing_image_with_clear_error(
    sample_dataset: tuple[Path, Path],
    test_client,
) -> None:
    dataset_path, preview_archive_path = sample_dataset
    missing_image_path = (
        dataset_path
        / "camera_lidar"
        / "20190401_121727"
        / "camera"
        / "cam_front_right"
        / "20190401121727_camera_frontright_000013460.png"
    )
    missing_image_path.unlink()

    response = test_client.post(
        "/datasets/load",
        json={
            "dataset_path": str(dataset_path),
            "preview_archive_path": str(preview_archive_path),
        },
    )

    assert response.status_code == 400
    assert "references missing image" in response.json()["detail"]
