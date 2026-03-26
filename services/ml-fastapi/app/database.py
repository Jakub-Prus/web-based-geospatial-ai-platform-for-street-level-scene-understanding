from __future__ import annotations

import sqlite3
from pathlib import Path

DATASETS_TABLE_NAME = "datasets"
FRAMES_TABLE_NAME = "frames"


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
                frame_id TEXT PRIMARY KEY,
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
                FOREIGN KEY (dataset_id) REFERENCES {DATASETS_TABLE_NAME}(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_frames_dataset_id
            ON {FRAMES_TABLE_NAME}(dataset_id);
            """
        )
