# 08. APIs And Interfaces

Status: Updated for implemented Slices 3-7

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

## Thin .NET Bridge Surface

The bridge remains intentionally small in Slice 5:

- `GET /bridge/health`
- `GET /bridge/datasets/summary`

## Planned Next Surface

These interfaces remain planned but are not implemented yet:

- correction endpoints
- depth and point-cloud endpoints
- metrics endpoints
- export endpoints

## Interface Contract Principles

- FastAPI is the client-facing backend for the current MVP slices.
- Detection runs include explicit run type, model version, processing counts, and status.
- Detection payloads remain stable enough for replayable frontend overlays.
- The .NET bridge consumes summary-level metadata only and does not duplicate FastAPI write ownership.

## Example Flow

1. Frontend requests `GET /datasets` and selects a loaded dataset.
2. Frontend requests `GET /datasets/{dataset_id}/frames` to render map markers.
3. User selects a frame marker and the frontend requests frame detail and preview.
4. Frontend requests `GET /datasets/{dataset_id}/frames/{frame_id}/detections`.
5. The image viewer renders stored boxes using the persisted pixel-space contract and displays the latest run status.
6. Future slices add correction persistence, depth, 3D, metrics, and export.

## Required Payload Contracts

- Dataset frame records include image path, latitude, longitude, heading, timestamp, width, and height.
- Detection records include frame id, class label, confidence, and bounding box in image pixel space.
- Bounding boxes remain in `x_min`, `y_min`, `x_max`, `y_max` image coordinates until the frontend scales them for display.

## External Integrations

- local file-backed dataset storage for the current demo slices
- Ultralytics YOLO weights for detection
- optional map tiles or richer basemaps remain deferred
