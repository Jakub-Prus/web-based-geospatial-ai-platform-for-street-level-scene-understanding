# 07. Data Model

Status: Proposed v1

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
- bbox_json
- geometry

### Correction

- id
- detection_id
- corrected_label
- corrected_bbox_json
- review_status
- created_at

### DepthArtifact

- id
- inference_run_id
- frame_id
- depth_uri
- depth_format
- width
- height
- depth_scale

### PointCloudArtifact

- id
- depth_artifact_id
- frame_id
- point_cloud_uri
- point_count
- coordinate_system

## Relationships

- One dataset has many camera frames.
- One dataset has many inference runs.
- One inference run has many detections.
- One inference run can have many depth artifacts.
- One depth artifact can produce one or more point-cloud artifacts.
- One detection can have zero or many corrections.
- One model version can be referenced by many inference runs.

## Storage Notes

- Geospatial coordinates and derived geometry should live in PostGIS-enabled columns.
- Large binary assets such as images, masks, depth maps, and point clouds should live in object storage, with database references.
