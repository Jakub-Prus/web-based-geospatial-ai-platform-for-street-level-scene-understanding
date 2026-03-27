from __future__ import annotations

import sqlite3
from pathlib import Path

DATASETS_TABLE_NAME = "datasets"
FRAMES_TABLE_NAME = "frames"
INFERENCE_RUNS_TABLE_NAME = "inference_runs"
DETECTIONS_TABLE_NAME = "detections"
FRAME_UNIQUE_INDEX_NAME = "idx_frames_dataset_id_frame_id"
LEGACY_FRAME_PRIMARY_KEY_COLUMN = "frame_id"
FRAME_PRIMARY_KEY_COLUMN = "id"


def create_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database(database_path: Path) -> None:
    with create_connection(database_path) as connection:
        connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS {DATASETS_TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_path TEXT NOT NULL UNIQUE,
                sequence_id TEXT NOT NULL,
                camera_name TEXT NOT NULL,
                frame_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS {FRAMES_TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id TEXT NOT NULL,
                dataset_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                heading_degrees REAL NOT NULL,
                timestamp TEXT NOT NULL,
                image_width INTEGER NOT NULL,
                image_height INTEGER NOT NULL,
                pitch_degrees REAL,
                roll_degrees REAL,
                camera_intrinsics_json TEXT,
                sequence_id TEXT,
                depth_path TEXT,
                UNIQUE (dataset_id, frame_id),
                FOREIGN KEY (dataset_id) REFERENCES {DATASETS_TABLE_NAME}(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_frames_dataset_id
            ON {FRAMES_TABLE_NAME}(dataset_id);

            CREATE INDEX IF NOT EXISTS {FRAME_UNIQUE_INDEX_NAME}
            ON {FRAMES_TABLE_NAME}(dataset_id, frame_id);

            CREATE TABLE IF NOT EXISTS {INFERENCE_RUNS_TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_path TEXT NOT NULL,
                frame_count INTEGER NOT NULL,
                processed_frame_count INTEGER NOT NULL DEFAULT 0,
                detection_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (dataset_id) REFERENCES {DATASETS_TABLE_NAME}(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_inference_runs_dataset_id
            ON {INFERENCE_RUNS_TABLE_NAME}(dataset_id);

            CREATE INDEX IF NOT EXISTS idx_inference_runs_dataset_id_run_type
            ON {INFERENCE_RUNS_TABLE_NAME}(dataset_id, run_type);

            CREATE TABLE IF NOT EXISTS {DETECTIONS_TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inference_run_id INTEGER NOT NULL,
                frame_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                x_min REAL NOT NULL,
                y_min REAL NOT NULL,
                x_max REAL NOT NULL,
                y_max REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (inference_run_id) REFERENCES {INFERENCE_RUNS_TABLE_NAME}(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_detections_inference_run_id
            ON {DETECTIONS_TABLE_NAME}(inference_run_id);

            CREATE INDEX IF NOT EXISTS idx_detections_frame_id
            ON {DETECTIONS_TABLE_NAME}(frame_id);
            """
        )

        if _frames_table_requires_migration(connection):
            _migrate_legacy_frames_table(connection)


def _frames_table_requires_migration(connection: sqlite3.Connection) -> bool:
    frame_columns = connection.execute(
        f"PRAGMA table_info({FRAMES_TABLE_NAME})"
    ).fetchall()
    frame_primary_key_column = next(
        (row["name"] for row in frame_columns if row["pk"] == 1),
        None,
    )

    return frame_primary_key_column == LEGACY_FRAME_PRIMARY_KEY_COLUMN


def _migrate_legacy_frames_table(connection: sqlite3.Connection) -> None:
    legacy_frames_table_name = f"{FRAMES_TABLE_NAME}_legacy"

    connection.executescript(
        f"""
        ALTER TABLE {FRAMES_TABLE_NAME} RENAME TO {legacy_frames_table_name};

        CREATE TABLE {FRAMES_TABLE_NAME} (
            {FRAME_PRIMARY_KEY_COLUMN} INTEGER PRIMARY KEY AUTOINCREMENT,
            frame_id TEXT NOT NULL,
            dataset_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            heading_degrees REAL NOT NULL,
            timestamp TEXT NOT NULL,
            image_width INTEGER NOT NULL,
            image_height INTEGER NOT NULL,
            pitch_degrees REAL,
            roll_degrees REAL,
            camera_intrinsics_json TEXT,
            sequence_id TEXT,
            depth_path TEXT,
            UNIQUE (dataset_id, frame_id),
            FOREIGN KEY (dataset_id) REFERENCES {DATASETS_TABLE_NAME}(id) ON DELETE CASCADE
        );

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
        )
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
        FROM {legacy_frames_table_name};

        DROP TABLE {legacy_frames_table_name};

        CREATE INDEX IF NOT EXISTS idx_frames_dataset_id
        ON {FRAMES_TABLE_NAME}(dataset_id);

        CREATE INDEX IF NOT EXISTS {FRAME_UNIQUE_INDEX_NAME}
        ON {FRAMES_TABLE_NAME}(dataset_id, frame_id);
        """
    )
