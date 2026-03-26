from __future__ import annotations

import shutil
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


def test_frame_detail_returns_preview_url_and_preview_asset(
    sample_dataset: tuple[Path, Path],
    test_client,
) -> None:
    dataset_path, preview_archive_path = sample_dataset

    load_response = test_client.post(
        "/datasets/load",
        json={
            "dataset_path": str(dataset_path),
            "preview_archive_path": str(preview_archive_path),
        },
    )

    assert load_response.status_code == 201

    dataset_id = load_response.json()["dataset"]["id"]
    frame_id = "20190401121727_camera_frontright_000013460"
    detail_response = test_client.get(f"/datasets/{dataset_id}/frames/{frame_id}")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["frame"]["frame_id"] == frame_id
    assert (
        detail_payload["frame"]["preview_url"]
        == f"/datasets/{dataset_id}/frames/{frame_id}/preview"
    )

    preview_response = test_client.get(detail_payload["frame"]["preview_url"])

    assert preview_response.status_code == 200
    assert preview_response.headers["content-type"] == "image/png"
    assert preview_response.content.startswith(b"\x89PNG")


def test_frame_detail_and_preview_return_not_found_for_missing_frame(test_client) -> None:
    missing_dataset_id = 999
    missing_frame_id = "missing-frame"

    detail_response = test_client.get(
        f"/datasets/{missing_dataset_id}/frames/{missing_frame_id}"
    )
    preview_response = test_client.get(
        f"/datasets/{missing_dataset_id}/frames/{missing_frame_id}/preview"
    )

    assert detail_response.status_code == 404
    assert (
        detail_response.json()["detail"]
        == f"Frame {missing_frame_id} was not found in dataset {missing_dataset_id}."
    )
    assert preview_response.status_code == 404
    assert (
        preview_response.json()["detail"]
        == f"Frame {missing_frame_id} was not found in dataset {missing_dataset_id}."
    )


def test_multiple_loaded_datasets_remain_independently_queryable(
    sample_dataset: tuple[Path, Path],
    test_client,
    tmp_path: Path,
) -> None:
    dataset_path, preview_archive_path = sample_dataset
    second_dataset_path = tmp_path / "a2d2-subset-copy"
    shutil.copytree(dataset_path, second_dataset_path)

    first_load_response = test_client.post(
        "/datasets/load",
        json={
            "dataset_path": str(dataset_path),
            "preview_archive_path": str(preview_archive_path),
            "dataset_name": "dataset-one",
        },
    )
    second_load_response = test_client.post(
        "/datasets/load",
        json={
            "dataset_path": str(second_dataset_path),
            "preview_archive_path": str(preview_archive_path),
            "dataset_name": "dataset-two",
        },
    )

    assert first_load_response.status_code == 201
    assert second_load_response.status_code == 201

    datasets_response = test_client.get("/datasets")
    datasets_payload = datasets_response.json()

    assert datasets_response.status_code == 200
    assert [dataset["name"] for dataset in datasets_payload["datasets"]] == [
        "dataset-one",
        "dataset-two",
    ]

    first_dataset_id = first_load_response.json()["dataset"]["id"]
    second_dataset_id = second_load_response.json()["dataset"]["id"]
    first_frames_response = test_client.get(f"/datasets/{first_dataset_id}/frames")
    second_frames_response = test_client.get(f"/datasets/{second_dataset_id}/frames")

    assert first_frames_response.status_code == 200
    assert second_frames_response.status_code == 200
    assert first_frames_response.json()["dataset"]["name"] == "dataset-one"
    assert second_frames_response.json()["dataset"]["name"] == "dataset-two"
    assert len(first_frames_response.json()["frames"]) == 2
    assert len(second_frames_response.json()["frames"]) == 2


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
