from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from app.database import DATASETS_TABLE_NAME, FRAMES_TABLE_NAME


class DatasetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def replace_dataset(
        self,
        *,
        name: str,
        source_path: str,
        sequence_id: str,
        camera_name: str,
        created_at: str,
        frames: Iterable[dict[str, object]],
    ) -> dict[str, object]:
        frames_to_insert = list(frames)

        with self.connection:
            existing_dataset = self.connection.execute(
                f"SELECT id FROM {DATASETS_TABLE_NAME} WHERE source_path = ?",
                (source_path,),
            ).fetchone()

            if existing_dataset is not None:
                self.connection.execute(
                    f"DELETE FROM {DATASETS_TABLE_NAME} WHERE id = ?",
                    (existing_dataset['id'],),
                )

            cursor = self.connection.execute(
                f"""
                INSERT INTO {DATASETS_TABLE_NAME} (
                    name,
                    source_path,
                    sequence_id,
                    camera_name,
                    frame_count,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    source_path,
                    sequence_id,
                    camera_name,
                    len(frames_to_insert),
                    created_at,
                ),
            )
            dataset_id = int(cursor.lastrowid)

            self.connection.executemany(
                f"""
                INSERT INTO {FRAMES_TABLE_NAME} (
                    frame_id,
                    dataset_id,
                    image_path,
                    latitude,
                    longitude,
                    heading_degrees,
                    timestamp,
                    image_width,
                    image_height,
                    pitch_degrees,
                    roll_degrees,
                    camera_intrinsics_json,
                    sequence_id,
                    depth_path
                ) VALUES (
                    :frame_id,
                    :dataset_id,
                    :image_path,
                    :latitude,
                    :longitude,
                    :heading_degrees,
                    :timestamp,
                    :image_width,
                    :image_height,
                    :pitch_degrees,
                    :roll_degrees,
                    :camera_intrinsics_json,
                    :sequence_id,
                    :depth_path
                )
                """,
                [{**frame, 'dataset_id': dataset_id} for frame in frames_to_insert],
            )

        return self.get_dataset(dataset_id)

    def list_datasets(self) -> list[dict[str, object]]:
        rows = self.connection.execute(
            f"""
            SELECT id, name, source_path, sequence_id, camera_name, frame_count, created_at
            FROM {DATASETS_TABLE_NAME}
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def get_dataset(self, dataset_id: int) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT id, name, source_path, sequence_id, camera_name, frame_count, created_at
            FROM {DATASETS_TABLE_NAME}
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()
        if row is None:
            raise KeyError(dataset_id)

        return dict(row)

    def list_frames_for_dataset(self, dataset_id: int) -> list[dict[str, object]]:
        rows = self.connection.execute(
            f"""
            SELECT
                frame_id,
                dataset_id,
                image_path,
                latitude,
                longitude,
                heading_degrees,
                timestamp,
                image_width,
                image_height,
                pitch_degrees,
                roll_degrees,
                camera_intrinsics_json,
                sequence_id,
                depth_path
            FROM {FRAMES_TABLE_NAME}
            WHERE dataset_id = ?
            ORDER BY timestamp ASC, frame_id ASC
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(row) for row in rows]
