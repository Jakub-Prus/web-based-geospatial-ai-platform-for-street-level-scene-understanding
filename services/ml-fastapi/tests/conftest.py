from __future__ import annotations

import json
import os
import tarfile
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PNG_PIXEL_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc`\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff"
    b"\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _build_bus_payload() -> dict[str, object]:
    return {
        "latitude_degree": {
            "unit": "degree",
            "values": [
                [1554115910000000, 48.14542],
                [1554115910500000, 48.14555],
                [1554115911000000, 48.14568],
                [1554115911500000, 48.14582],
                [1554115912000000, 48.14595],
            ],
        },
        "longitude_degree": {
            "unit": "degree",
            "values": [
                [1554115910000000, 11.56661],
                [1554115910500000, 11.56671],
                [1554115911000000, 11.56681],
                [1554115911500000, 11.5669],
                [1554115912000000, 11.567],
            ],
        },
        "pitch_angle": {
            "unit": "degree",
            "values": [
                [1554115910000000, -0.15],
                [1554115911000000, -0.1],
                [1554115912000000, -0.05],
            ],
        },
        "roll_angle": {
            "unit": "degree",
            "values": [
                [1554115910000000, 2.4],
                [1554115911000000, 2.45],
                [1554115912000000, 2.5],
            ],
        },
    }


def _write_frame_metadata(camera_directory: Path, frame_id: str, timestamp: int) -> None:
    metadata = {
        "cam_tstamp": timestamp,
        "cam_name": "front_right",
        "image_zoom": 1.0,
        "image_png": f"{frame_id}.png",
        "pcld_npz": f"{frame_id}.npz",
    }
    (camera_directory / f"{frame_id}.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )


def _create_preview_archive(archive_path: Path, sequence_id: str) -> None:
    bus_payload_path = archive_path.parent / f"{sequence_id}-bus-signals.json"
    bus_payload_path.write_text(json.dumps(_build_bus_payload()), encoding="utf-8")

    with tarfile.open(archive_path, "w") as archive:
        archive.add(
            bus_payload_path,
            arcname=f"camera_lidar/{sequence_id}/bus_signals_{sequence_id.replace('_', '')}.json",
        )


@pytest.fixture()
def sample_dataset(tmp_path: Path) -> tuple[Path, Path]:
    sequence_id = "20190401_121727"
    camera_directory = (
        tmp_path
        / "a2d2-subset"
        / "camera_lidar"
        / sequence_id
        / "camera"
        / "cam_front_right"
    )
    camera_directory.mkdir(parents=True)

    frame_timestamps = (
        ("20190401121727_camera_frontright_000013460", 1554115910962784),
        ("20190401121727_camera_frontright_000013461", 1554115911462784),
    )

    for frame_id, timestamp in frame_timestamps:
        (camera_directory / f"{frame_id}.png").write_bytes(PNG_PIXEL_BYTES)
        _write_frame_metadata(camera_directory, frame_id, timestamp)

    preview_archive_path = tmp_path / "a2d2-preview.tar"
    _create_preview_archive(preview_archive_path, sequence_id)

    return camera_directory.parents[3], preview_archive_path


@pytest.fixture()
def test_client_factory(
    tmp_path: Path,
) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []
    client_count = 0

    def _build_test_client(*, detector_factory=None) -> TestClient:
        nonlocal client_count

        database_path = tmp_path / f"test-platform-{client_count}.db"
        client_count += 1
        os.environ["ML_FASTAPI_DB_PATH"] = str(database_path)
        app = create_app(detector_factory=detector_factory)
        client = TestClient(app)
        clients.append(client)
        client.__enter__()

        return client

    yield _build_test_client

    while clients:
        client = clients.pop()
        client.__exit__(None, None, None)

    os.environ.pop("ML_FASTAPI_DB_PATH", None)


@pytest.fixture()
def test_client(test_client_factory: Callable[..., TestClient]) -> Iterator[TestClient]:
    client = test_client_factory()
    yield client
