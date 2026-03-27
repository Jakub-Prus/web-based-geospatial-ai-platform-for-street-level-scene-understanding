# 08. APIs And Interfaces

Status: Updated for implemented Slices 3-11

## FastAPI Surface Implemented Today

### Health

- `GET /`
- `GET /health`

### Dataset Endpoints

- `POST /datasets/load`
- `GET /datasets`
- `GET /datasets/{dataset_id}/frames`
- `GET /datasets/{dataset_id}/frames/{frame_id}`
- `GET /datasets/{dataset_id}/frames/{frame_id}/preview`

### Detection Run Endpoints

- `POST /datasets/{dataset_id}/runs/detect`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/status`
- `GET /datasets/{dataset_id}/frames/{frame_id}/detections`

The frame-detections endpoint returns the latest detection run for the dataset by default and can optionally be filtered with `run_id`.

### Correction Endpoints

- `POST /datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction`
- `GET /datasets/{dataset_id}/frames/{frame_id}/corrections`

The save-correction endpoint accepts a `review_status` of `pending`, `approved`, or `rejected` plus an optional corrected label and/or corrected bounding box.

The frame-corrections endpoint defaults to the latest detection run for the dataset, accepts optional `run_id` filtering, and returns the selected run plus the original detection, optional corrected detection, and resolved effective detection state.

The Slice 9 frontend consumes both correction endpoints to load effective detection state for a selected frame and then saves one edited detection at a time after clipping the box to image bounds.

### Depth Endpoints

- `POST /datasets/{dataset_id}/frames/{frame_id}/depth`
- `GET /datasets/{dataset_id}/frames/{frame_id}/depth`

The POST depth endpoint runs MiDaS inference for one selected frame, persists one depth artifact when validation succeeds, and still records a frame-scoped failed run when inference or dimension validation fails.

The GET depth endpoint returns a `missing`, `running`, `completed`, or `failed` state plus optional run and artifact metadata so later UI slices can render a clear fallback instead of assuming a depth artifact exists.

### Point-Cloud Endpoints

- `POST /datasets/{dataset_id}/frames/{frame_id}/point-cloud`
- `GET /datasets/{dataset_id}/frames/{frame_id}/point-cloud`

The POST point-cloud endpoint reads the latest stored depth artifact for one frame, converts valid inverse-depth pixels into local XYZ coordinates, deterministically subsamples the result to a caller-provided or default cap, and persists one compressed point-cloud artifact plus inline payload metadata.

The GET point-cloud endpoint returns a `missing`, `running`, `completed`, or `failed` state plus optional run metadata, artifact metadata, and inline sampled `points` data for the latest frame-scoped point-cloud conversion run.

## Thin .NET Bridge Surface

The bridge remains intentionally small in Slice 5:

- `GET /bridge/health`
- `GET /bridge/datasets/summary`

## Planned Next Surface

These interfaces remain planned but are not implemented yet:

- metrics endpoints
- export endpoints

## Interface Contract Principles

- FastAPI is the client-facing backend for the current MVP slices.
- Detection runs include explicit run type, model version, processing counts, and status.
- Depth runs reuse the shared run metadata model and add optional frame scope through `run.frame_id`.
- Point-cloud runs reuse the shared run metadata model, remain frame-scoped, and record the source stored-depth artifact URI in `run.model_path`.
- Detection payloads remain stable enough for replayable frontend overlays.
- Correction payloads preserve original model detections and never overwrite raw detection rows.
- Depth payloads expose width, height, `depth_format`, and `depth_scale` so later 3D slices do not need to infer artifact semantics from file names.
- Point-cloud payloads expose a documented local coordinate system, stored intrinsics, deterministic `subsample_step`, `point_count`, `source_point_count`, and inline XYZ point records so the Three.js slice can stay thin.
- The .NET bridge consumes summary-level metadata only and does not duplicate FastAPI write ownership.

## Example Flow

1. Frontend requests `GET /datasets` and selects a loaded dataset.
2. Frontend requests `GET /datasets/{dataset_id}/frames` to render map markers.
3. User selects a frame marker and the frontend requests frame detail and preview.
4. Frontend requests `GET /datasets/{dataset_id}/frames/{frame_id}/detections`.
5. The image viewer renders stored boxes using the persisted pixel-space contract and displays the latest run status.
6. Frontend requests `GET /datasets/{dataset_id}/frames/{frame_id}/corrections` to resolve effective detection state for the editor.
7. User edits one selected box in the image viewer and the frontend clips the box to image bounds before save.
8. Frontend posts the updated label and bounding box to `POST /datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction`.
9. Frontend or a script can trigger `POST /datasets/{dataset_id}/frames/{frame_id}/depth` for one selected frame and read the current depth state through `GET /datasets/{dataset_id}/frames/{frame_id}/depth`.
10. Frontend or a script can trigger `POST /datasets/{dataset_id}/frames/{frame_id}/point-cloud` and read the latest inline XYZ payload through `GET /datasets/{dataset_id}/frames/{frame_id}/point-cloud`.
11. Future slices add Three.js rendering, metrics, and export.

## Required Payload Contracts

- Dataset frame records include image path, latitude, longitude, heading, timestamp, width, and height.
- Detection records include frame id, class label, confidence, and bounding box in image pixel space.
- Bounding boxes remain in `x_min`, `y_min`, `x_max`, `y_max` image coordinates until the frontend scales them for display.
- Correction records include review status plus separate original, corrected, and effective detection state.
- Depth artifact records include `depth_uri`, `width`, `height`, `depth_format`, and `depth_scale`, and the backend rejects artifacts whose stored shape does not match the source frame dimensions.
- Point-cloud artifact records include `point_cloud_uri`, `point_format`, `coordinate_system`, `source_point_count`, `point_count`, `subsample_step`, and the exact `fx`, `fy`, `cx`, and `cy` values used for generation.

## External Integrations

- local file-backed dataset storage for the current demo slices
- Ultralytics YOLO weights for detection
- MiDaS `dpt_swin2_tiny_256.pt` weights plus the official MiDaS model code path for depth
- optional map tiles or richer basemaps remain deferred
