from __future__ import annotations

import json
import math
import struct
import tarfile
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import DEFAULT_PREVIEW_ARCHIVE_PATH, REPO_ROOT

BUS_SIGNAL_PREFIX = "bus_signals_"
CAMERA_DIRECTORY_NAME = "camera"
CAMERA_FILE_SUFFIX = ".json"
CAMERA_INTRINSICS_FILE = REPO_ROOT / "external-assets" / "a2d2" / "cams_lidars.json"
HEADING_WINDOW_SAMPLES = (5, 10, 20, 50, 100, 200)
PNG_HEADER_SIZE = 8
PNG_IHDR_CHUNK_NAME = b"IHDR"
REQUIRED_FRAME_FIELDS = (
    "frame_id",
    "image_path",
    "latitude",
    "longitude",
    "heading_degrees",
    "timestamp",
    "image_width",
    "image_height",
)


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDataset:
    name: str
    source_path: str
    sequence_id: str
    camera_name: str
    created_at: str
    frames: list[dict[str, object]]


class A2D2SubsetParser:
    def __init__(self, *, dataset_root: Path, preview_archive_path: Path | None = None) -> None:
        self.dataset_root = dataset_root.resolve()
        self.preview_archive_path = (
            preview_archive_path.resolve()
            if preview_archive_path is not None
            else DEFAULT_PREVIEW_ARCHIVE_PATH.resolve()
        )

    def parse(self, dataset_name: str | None = None) -> ParsedDataset:
        if not self.dataset_root.exists():
            raise DatasetValidationError(f"Dataset path does not exist: {self.dataset_root}")

        camera_root = self._resolve_camera_root()
        sequence_id = camera_root.parents[1].name
        camera_directory_name = camera_root.name
        camera_name = camera_directory_name.removeprefix("cam_")
        bus_signals = self._load_bus_signals(sequence_id)
        camera_intrinsics_json = self._load_camera_intrinsics(camera_name)
        frame_metadata_files = sorted(camera_root.glob(f"*{CAMERA_FILE_SUFFIX}"))

        if not frame_metadata_files:
            raise DatasetValidationError(
                f"No frame metadata JSON files were found under {camera_root}"
            )

        frames: list[dict[str, object]] = []
        frame_ids: set[str] = set()

        for metadata_path in frame_metadata_files:
            frame_record = self._parse_frame(
                metadata_path=metadata_path,
                dataset_root=self.dataset_root,
                sequence_id=sequence_id,
                camera_intrinsics_json=camera_intrinsics_json,
                bus_signals=bus_signals,
            )

            frame_id = str(frame_record["frame_id"])
            if frame_id in frame_ids:
                raise DatasetValidationError(f"Duplicate frame_id detected: {frame_id}")

            self._validate_required_fields(frame_record)
            frame_ids.add(frame_id)
            frames.append(frame_record)

        dataset_timestamp = max(str(frame["timestamp"]) for frame in frames)

        return ParsedDataset(
            name=dataset_name or f"{sequence_id}-{camera_directory_name}",
            source_path=str(self.dataset_root),
            sequence_id=sequence_id,
            camera_name=camera_name,
            created_at=dataset_timestamp,
            frames=frames,
        )

    def _resolve_camera_root(self) -> Path:
        camera_root_candidates = list(
            self.dataset_root.glob(f"camera_lidar/*/{CAMERA_DIRECTORY_NAME}/cam_*")
        )
        if not camera_root_candidates:
            raise DatasetValidationError(
                "Expected A2D2 subset layout camera_lidar/<sequence>/camera/<camera_name>/ was not found."
            )
        if len(camera_root_candidates) != 1:
            raise DatasetValidationError(
                "Expected exactly one camera directory in the subset for Slice 3 loading."
            )

        return camera_root_candidates[0]

    def _parse_frame(
        self,
        *,
        metadata_path: Path,
        dataset_root: Path,
        sequence_id: str,
        camera_intrinsics_json: str | None,
        bus_signals: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        frame_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        frame_timestamp = int(frame_metadata["cam_tstamp"])
        image_file_name = frame_metadata.get("image_png")
        if not image_file_name:
            raise DatasetValidationError(
                f"Metadata file {metadata_path} is missing required field image_png."
            )

        image_path = metadata_path.with_name(str(image_file_name))
        if not image_path.exists():
            raise DatasetValidationError(
                f"Metadata file {metadata_path.name} references missing image {image_path.name}."
            )

        width, height = self._read_png_dimensions(image_path)
        latitude = self._lookup_signal_value(
            bus_signals["latitude_degree"]["values"],
            frame_timestamp,
        )
        longitude = self._lookup_signal_value(
            bus_signals["longitude_degree"]["values"],
            frame_timestamp,
        )
        pitch = self._lookup_signal_value(bus_signals["pitch_angle"]["values"], frame_timestamp)
        roll = self._lookup_signal_value(bus_signals["roll_angle"]["values"], frame_timestamp)
        heading_degrees = self._derive_heading_degrees(
            latitude_signal=bus_signals["latitude_degree"]["values"],
            longitude_signal=bus_signals["longitude_degree"]["values"],
            frame_timestamp=frame_timestamp,
        )
        relative_image_path = image_path.relative_to(dataset_root).as_posix()

        return {
            "frame_id": image_path.stem,
            "image_path": relative_image_path,
            "latitude": latitude,
            "longitude": longitude,
            "heading_degrees": heading_degrees,
            "timestamp": datetime.fromtimestamp(
                frame_timestamp / 1_000_000,
                tz=timezone.utc,
            )
            .isoformat()
            .replace("+00:00", "Z"),
            "image_width": width,
            "image_height": height,
            "pitch_degrees": pitch,
            "roll_degrees": roll,
            "camera_intrinsics_json": camera_intrinsics_json,
            "sequence_id": sequence_id,
            "depth_path": None,
        }

    def _load_bus_signals(self, sequence_id: str) -> dict[str, dict[str, object]]:
        local_matches = list(
            self.dataset_root.glob(f"camera_lidar/{sequence_id}/{BUS_SIGNAL_PREFIX}*.json")
        )
        if local_matches:
            bus_signal_path = local_matches[0]
            return json.loads(bus_signal_path.read_text(encoding="utf-8"))

        if not self.preview_archive_path.exists():
            raise DatasetValidationError(
                "Bus signals were not found in the extracted subset and preview archive "
                f"was not found at {self.preview_archive_path}."
            )

        archive_member_prefix = f"camera_lidar/{sequence_id}/{BUS_SIGNAL_PREFIX}"
        with tarfile.open(self.preview_archive_path, "r") as archive:
            member_name = next(
                (
                    member.name
                    for member in archive
                    if member.name.startswith(archive_member_prefix)
                    and member.name.endswith(".json")
                ),
                None,
            )
            if member_name is None:
                raise DatasetValidationError(
                    f"Bus signals for sequence {sequence_id} were not found in {self.preview_archive_path}."
                )

            extracted_file = archive.extractfile(member_name)
            if extracted_file is None:
                raise DatasetValidationError(
                    f"Bus signals member {member_name} could not be read from {self.preview_archive_path}."
                )

            return json.load(extracted_file)

    def _load_camera_intrinsics(self, camera_name: str) -> str | None:
        if not CAMERA_INTRINSICS_FILE.exists():
            return None

        cameras_payload = json.loads(CAMERA_INTRINSICS_FILE.read_text(encoding="utf-8"))
        camera_payload = cameras_payload.get("cameras", {}).get(camera_name)
        if camera_payload is None:
            return None

        return json.dumps(camera_payload.get("CamMatrix"))

    def _lookup_signal_value(
        self,
        samples: list[list[float | str]],
        timestamp: int,
    ) -> float:
        if not samples:
            raise DatasetValidationError("Required bus signal series is empty.")

        index = self._find_nearest_index(samples, timestamp)
        return float(samples[index][1])

    def _derive_heading_degrees(
        self,
        *,
        latitude_signal: list[list[float | str]],
        longitude_signal: list[list[float | str]],
        frame_timestamp: int,
    ) -> float:
        if len(latitude_signal) != len(longitude_signal):
            raise DatasetValidationError(
                "Latitude and longitude signal series do not have matching lengths."
            )

        center_index = self._find_nearest_index(latitude_signal, frame_timestamp)

        for window_size in HEADING_WINDOW_SAMPLES:
            start_index = max(0, center_index - window_size)
            end_index = min(len(latitude_signal) - 1, center_index + window_size)

            start_latitude = float(latitude_signal[start_index][1])
            start_longitude = float(longitude_signal[start_index][1])
            end_latitude = float(latitude_signal[end_index][1])
            end_longitude = float(longitude_signal[end_index][1])

            if start_latitude == end_latitude and start_longitude == end_longitude:
                continue

            return self._calculate_bearing(
                start_latitude=start_latitude,
                start_longitude=start_longitude,
                end_latitude=end_latitude,
                end_longitude=end_longitude,
            )

        raise DatasetValidationError(
            f"Unable to derive heading_degrees for frame timestamp {frame_timestamp}."
        )

    def _find_nearest_index(
        self,
        samples: list[list[float | str]],
        timestamp: int,
    ) -> int:
        timestamps = [int(sample[0]) for sample in samples]
        insertion_index = bisect_left(timestamps, timestamp)

        if insertion_index <= 0:
            return 0
        if insertion_index >= len(timestamps):
            return len(timestamps) - 1

        previous_index = insertion_index - 1
        if abs(timestamps[insertion_index] - timestamp) < abs(
            timestamps[previous_index] - timestamp
        ):
            return insertion_index

        return previous_index

    def _read_png_dimensions(self, image_path: Path) -> tuple[int, int]:
        with image_path.open("rb") as image_file:
            image_file.read(PNG_HEADER_SIZE)
            chunk_length = struct.unpack(">I", image_file.read(4))[0]
            chunk_name = image_file.read(4)
            if chunk_name != PNG_IHDR_CHUNK_NAME:
                raise DatasetValidationError(
                    f"Image file {image_path} is missing the PNG IHDR chunk."
                )
            width, height = struct.unpack(">II", image_file.read(8))
            if chunk_length <= 0:
                raise DatasetValidationError(
                    f"Image file {image_path} has an invalid IHDR chunk length."
                )
            return width, height

    def _validate_required_fields(self, frame_record: dict[str, object]) -> None:
        missing_fields = [
            field_name
            for field_name in REQUIRED_FRAME_FIELDS
            if frame_record.get(field_name) in (None, "", [])
        ]
        if missing_fields:
            raise DatasetValidationError(
                f"Frame {frame_record.get('frame_id', '<unknown>')} is missing required fields: "
                f"{', '.join(missing_fields)}"
            )

    def _calculate_bearing(
        self,
        *,
        start_latitude: float,
        start_longitude: float,
        end_latitude: float,
        end_longitude: float,
    ) -> float:
        start_latitude_radians = math.radians(start_latitude)
        end_latitude_radians = math.radians(end_latitude)
        delta_longitude_radians = math.radians(end_longitude - start_longitude)

        x_component = math.sin(delta_longitude_radians) * math.cos(end_latitude_radians)
        y_component = (
            math.cos(start_latitude_radians) * math.sin(end_latitude_radians)
            - math.sin(start_latitude_radians)
            * math.cos(end_latitude_radians)
            * math.cos(delta_longitude_radians)
        )

        return round((math.degrees(math.atan2(x_component, y_component)) + 360.0) % 360.0, 6)
