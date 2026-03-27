# 07. Data Model

Status: Updated after Slice 11

## Core Entities

- Dataset
- CameraFrame
- InferenceRun
- Detection
- Correction
- DepthArtifact
- PointCloudArtifact
- ModelVersion
- ExportBundle

## Key Entity Definitions

### Dataset

- id
- name
- source_type
- uploaded_at
- capture_date_range
- coordinate_reference_system

### CameraFrame

- id
- dataset_id
- image_uri
- image_width
- image_height
- latitude
- longitude
- heading
- pitch
- roll
- timestamp
- camera_intrinsics_json
- local_pose_json

### InferenceRun

- id
- dataset_id
- optional frame_id
- model_version_id
- run_type
- status
- started_at
- completed_at

### Detection

- id
- inference_run_id
- frame_id
- class_name
- confidence_score
- x_min
- y_min
- x_max
- y_max
- created_at

### Correction

- id
- detection_id
- review_status
- corrected_class_name
- corrected_x_min
- corrected_y_min
- corrected_x_max
- corrected_y_max
- created_at
- updated_at

### DepthArtifact

- id
- inference_run_id
- frame_id
- depth_uri
- depth_format
- width
- height
- depth_scale
- created_at

### PointCloudArtifact

- id
- inference_run_id
- source_depth_artifact_id
- frame_id
- point_cloud_uri
- point_format
- coordinate_system
- source_point_count
- point_count
- subsample_step
- intrinsics_source
- fx
- fy
- cx
- cy
- created_at

## Relationships

- One dataset has many camera frames.
- One dataset has many inference runs.
- One inference run has many detections.
- One inference run can have many depth artifacts.
- In the current Slice 10 implementation, depth inference runs are frame-scoped and store `frame_id` on `inference_runs`.
- One depth artifact can produce one or more point-cloud artifacts.
- In the current Slice 11 implementation, point-cloud conversion runs are also frame-scoped and store `frame_id` on `inference_runs`.
- In the current Slice 8 implementation, one detection can have zero or one active correction record.
- The original model detection remains stored separately in `detections`, so review can return both original and corrected state without mutating the model output row.
- One model version can be referenced by many inference runs.

## Storage Notes

- Geospatial coordinates and derived geometry should live in PostGIS-enabled columns.
- Large binary assets such as images, masks, depth maps, and point clouds should live in object storage, with database references.
- The current local MVP stores detection and correction bounding boxes as explicit numeric columns so the overlay and correction flows stay simple in SQLite.
- The current local MVP stores depth artifact metadata in SQLite and writes the artifact payload itself as a local `.npy` file, with `frames.depth_path` caching the latest stored artifact URI for the frame.
- The current local MVP stores point-cloud artifact metadata in SQLite and writes the sampled payload itself as a local compressed `.npz` file that contains one `Nx3` float32 `points` array.
