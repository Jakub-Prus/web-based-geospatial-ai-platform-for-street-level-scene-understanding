from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from app.database import (
    CORRECTIONS_TABLE_NAME,
    DATASETS_TABLE_NAME,
    DETECTIONS_TABLE_NAME,
    FRAMES_TABLE_NAME,
    INFERENCE_RUNS_TABLE_NAME,
)
from app.inference import RUN_STATUS_FAILED


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

    def get_detection_run(self, run_id: int) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT
                id,
                dataset_id,
                run_type,
                status,
                model_name,
                model_path,
                frame_count,
                processed_frame_count,
                detection_count,
                error_message,
                started_at,
                completed_at
            FROM {INFERENCE_RUNS_TABLE_NAME}
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(run_id)

        return dict(row)

    def get_detection(
        self,
        *,
        dataset_id: int,
        frame_id: str,
        detection_id: int,
    ) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT
                detections.id,
                detections.inference_run_id,
                detections.frame_id,
                detections.class_name,
                detections.confidence_score,
                detections.x_min,
                detections.y_min,
                detections.x_max,
                detections.y_max,
                detections.created_at
            FROM {DETECTIONS_TABLE_NAME} AS detections
            INNER JOIN {INFERENCE_RUNS_TABLE_NAME} AS runs
                ON runs.id = detections.inference_run_id
            WHERE detections.id = ?
              AND detections.frame_id = ?
              AND runs.dataset_id = ?
            """,
            (detection_id, frame_id, dataset_id),
        ).fetchone()
        if row is None:
            raise KeyError((dataset_id, frame_id, detection_id))

        return dict(row)

    def get_latest_detection_run_for_dataset(
        self,
        dataset_id: int,
        run_type: str,
    ) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT
                id,
                dataset_id,
                run_type,
                status,
                model_name,
                model_path,
                frame_count,
                processed_frame_count,
                detection_count,
                error_message,
                started_at,
                completed_at
            FROM {INFERENCE_RUNS_TABLE_NAME}
            WHERE dataset_id = ?
              AND run_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (dataset_id, run_type),
        ).fetchone()
        if row is None:
            raise KeyError((dataset_id, run_type))

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

    def list_frames_for_inference(self, dataset_id: int) -> list[dict[str, object]]:
        rows = self.connection.execute(
            f"""
            SELECT
                frames.frame_id,
                frames.image_path,
                frames.image_width,
                frames.image_height,
                datasets.source_path AS dataset_source_path
            FROM {FRAMES_TABLE_NAME} AS frames
            INNER JOIN {DATASETS_TABLE_NAME} AS datasets
                ON datasets.id = frames.dataset_id
            WHERE frames.dataset_id = ?
            ORDER BY frames.timestamp ASC, frames.frame_id ASC
            """,
            (dataset_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_frame(self, dataset_id: int, frame_id: str) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT
                frames.frame_id,
                frames.dataset_id,
                frames.image_path,
                frames.latitude,
                frames.longitude,
                frames.heading_degrees,
                frames.timestamp,
                frames.image_width,
                frames.image_height,
                frames.pitch_degrees,
                frames.roll_degrees,
                frames.camera_intrinsics_json,
                frames.sequence_id,
                frames.depth_path,
                datasets.source_path AS dataset_source_path
            FROM {FRAMES_TABLE_NAME} AS frames
            INNER JOIN {DATASETS_TABLE_NAME} AS datasets
                ON datasets.id = frames.dataset_id
            WHERE frames.dataset_id = ?
              AND frames.frame_id = ?
            """,
            (dataset_id, frame_id),
        ).fetchone()
        if row is None:
            raise KeyError((dataset_id, frame_id))

        return dict(row)

    def create_inference_run(
        self,
        *,
        dataset_id: int,
        run_type: str,
        status: str,
        model_name: str,
        model_path: str,
        frame_count: int,
        started_at: str,
    ) -> dict[str, object]:
        with self.connection:
            cursor = self.connection.execute(
                f"""
                INSERT INTO {INFERENCE_RUNS_TABLE_NAME} (
                    dataset_id,
                    run_type,
                    status,
                    model_name,
                    model_path,
                    frame_count,
                    processed_frame_count,
                    detection_count,
                    started_at,
                    completed_at,
                    error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    run_type,
                    status,
                    model_name,
                    model_path,
                    frame_count,
                    0,
                    0,
                    started_at,
                    None,
                    None,
                ),
            )

        return self.get_detection_run(int(cursor.lastrowid))

    def finalize_inference_run(
        self,
        *,
        run_id: int,
        status: str,
        processed_frame_count: int,
        detection_count: int,
        completed_at: str,
        detections: Iterable[dict[str, object]],
    ) -> dict[str, object]:
        detections_to_insert = list(detections)

        with self.connection:
            if detections_to_insert:
                self.connection.executemany(
                    f"""
                    INSERT INTO {DETECTIONS_TABLE_NAME} (
                        inference_run_id,
                        frame_id,
                        class_name,
                        confidence_score,
                        x_min,
                        y_min,
                        x_max,
                        y_max,
                        created_at
                    ) VALUES (
                        :inference_run_id,
                        :frame_id,
                        :class_name,
                        :confidence_score,
                        :x_min,
                        :y_min,
                        :x_max,
                        :y_max,
                        :created_at
                    )
                    """,
                    detections_to_insert,
                )

            self.connection.execute(
                f"""
                UPDATE {INFERENCE_RUNS_TABLE_NAME}
                SET
                    status = ?,
                    processed_frame_count = ?,
                    detection_count = ?,
                    completed_at = ?,
                    error_message = NULL
                WHERE id = ?
                """,
                (
                    status,
                    processed_frame_count,
                    detection_count,
                    completed_at,
                    run_id,
                ),
            )

        return self.get_detection_run(run_id)

    def mark_inference_run_failed(
        self,
        *,
        run_id: int,
        processed_frame_count: int,
        completed_at: str,
        error_message: str,
    ) -> dict[str, object]:
        with self.connection:
            self.connection.execute(
                f"""
                UPDATE {INFERENCE_RUNS_TABLE_NAME}
                SET
                    status = ?,
                    processed_frame_count = ?,
                    detection_count = 0,
                    completed_at = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    RUN_STATUS_FAILED,
                    processed_frame_count,
                    completed_at,
                    error_message,
                    run_id,
                ),
            )

        return self.get_detection_run(run_id)

    def list_detections_for_frame(
        self,
        *,
        dataset_id: int,
        frame_id: str,
        run_id: int | None = None,
        run_type: str,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        run_record = (
            self.get_detection_run(run_id)
            if run_id is not None
            else self.get_latest_detection_run_for_dataset(dataset_id, run_type)
        )
        if (
            int(run_record["dataset_id"]) != dataset_id
            or run_record["run_type"] != run_type
        ):
            raise KeyError((dataset_id, frame_id, run_id))

        rows = self.connection.execute(
            f"""
            SELECT
                id,
                inference_run_id,
                frame_id,
                class_name,
                confidence_score,
                x_min,
                y_min,
                x_max,
                y_max,
                created_at
            FROM {DETECTIONS_TABLE_NAME}
            WHERE inference_run_id = ?
              AND frame_id = ?
            ORDER BY confidence_score DESC, id ASC
            """,
            (run_record["id"], frame_id),
        ).fetchall()

        return dict(run_record), [dict(row) for row in rows]

    def save_correction(
        self,
        *,
        dataset_id: int,
        frame_id: str,
        detection_id: int,
        review_status: str,
        corrected_class_name: str | None,
        corrected_x_min: float | None,
        corrected_y_min: float | None,
        corrected_x_max: float | None,
        corrected_y_max: float | None,
        saved_at: str,
    ) -> dict[str, object]:
        self.get_detection(
            dataset_id=dataset_id,
            frame_id=frame_id,
            detection_id=detection_id,
        )

        with self.connection:
            existing_correction = self.connection.execute(
                f"""
                SELECT id, created_at
                FROM {CORRECTIONS_TABLE_NAME}
                WHERE detection_id = ?
                """,
                (detection_id,),
            ).fetchone()

            if existing_correction is None:
                self.connection.execute(
                    f"""
                    INSERT INTO {CORRECTIONS_TABLE_NAME} (
                        detection_id,
                        review_status,
                        corrected_class_name,
                        corrected_x_min,
                        corrected_y_min,
                        corrected_x_max,
                        corrected_y_max,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        detection_id,
                        review_status,
                        corrected_class_name,
                        corrected_x_min,
                        corrected_y_min,
                        corrected_x_max,
                        corrected_y_max,
                        saved_at,
                        saved_at,
                    ),
                )
            else:
                self.connection.execute(
                    f"""
                    UPDATE {CORRECTIONS_TABLE_NAME}
                    SET
                        review_status = ?,
                        corrected_class_name = ?,
                        corrected_x_min = ?,
                        corrected_y_min = ?,
                        corrected_x_max = ?,
                        corrected_y_max = ?,
                        updated_at = ?
                    WHERE detection_id = ?
                    """,
                    (
                        review_status,
                        corrected_class_name,
                        corrected_x_min,
                        corrected_y_min,
                        corrected_x_max,
                        corrected_y_max,
                        saved_at,
                        detection_id,
                    ),
                )

        return self.get_correction(
            dataset_id=dataset_id,
            frame_id=frame_id,
            detection_id=detection_id,
        )

    def get_correction(
        self,
        *,
        dataset_id: int,
        frame_id: str,
        detection_id: int,
    ) -> dict[str, object]:
        row = self.connection.execute(
            f"""
            SELECT
                corrections.id AS correction_id,
                corrections.detection_id,
                corrections.review_status,
                corrections.corrected_class_name,
                corrections.corrected_x_min,
                corrections.corrected_y_min,
                corrections.corrected_x_max,
                corrections.corrected_y_max,
                corrections.created_at AS correction_created_at,
                corrections.updated_at AS correction_updated_at,
                detections.id AS original_detection_id,
                detections.inference_run_id AS original_inference_run_id,
                detections.frame_id AS original_frame_id,
                detections.class_name AS original_class_name,
                detections.confidence_score AS original_confidence_score,
                detections.x_min AS original_x_min,
                detections.y_min AS original_y_min,
                detections.x_max AS original_x_max,
                detections.y_max AS original_y_max,
                detections.created_at AS original_created_at
            FROM {CORRECTIONS_TABLE_NAME} AS corrections
            INNER JOIN {DETECTIONS_TABLE_NAME} AS detections
                ON detections.id = corrections.detection_id
            INNER JOIN {INFERENCE_RUNS_TABLE_NAME} AS runs
                ON runs.id = detections.inference_run_id
            WHERE corrections.detection_id = ?
              AND detections.frame_id = ?
              AND runs.dataset_id = ?
            """,
            (detection_id, frame_id, dataset_id),
        ).fetchone()
        if row is None:
            raise KeyError((dataset_id, frame_id, detection_id))

        return dict(row)

    def list_corrections_for_frame(
        self,
        *,
        dataset_id: int,
        frame_id: str,
        run_id: int | None = None,
        run_type: str,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        run_record = (
            self.get_detection_run(run_id)
            if run_id is not None
            else self.get_latest_detection_run_for_dataset(dataset_id, run_type)
        )
        if (
            int(run_record["dataset_id"]) != dataset_id
            or run_record["run_type"] != run_type
        ):
            raise KeyError((dataset_id, frame_id, run_id))

        rows = self.connection.execute(
            f"""
            SELECT
                corrections.id AS correction_id,
                corrections.detection_id,
                corrections.review_status,
                corrections.corrected_class_name,
                corrections.corrected_x_min,
                corrections.corrected_y_min,
                corrections.corrected_x_max,
                corrections.corrected_y_max,
                corrections.created_at AS correction_created_at,
                corrections.updated_at AS correction_updated_at,
                detections.id AS original_detection_id,
                detections.inference_run_id AS original_inference_run_id,
                detections.frame_id AS original_frame_id,
                detections.class_name AS original_class_name,
                detections.confidence_score AS original_confidence_score,
                detections.x_min AS original_x_min,
                detections.y_min AS original_y_min,
                detections.x_max AS original_x_max,
                detections.y_max AS original_y_max,
                detections.created_at AS original_created_at
            FROM {CORRECTIONS_TABLE_NAME} AS corrections
            INNER JOIN {DETECTIONS_TABLE_NAME} AS detections
                ON detections.id = corrections.detection_id
            WHERE detections.inference_run_id = ?
              AND detections.frame_id = ?
            ORDER BY corrections.updated_at DESC, corrections.id DESC
            """,
            (run_record["id"], frame_id),
        ).fetchall()

        return dict(run_record), [dict(row) for row in rows]
