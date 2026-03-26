# 08. APIs And Interfaces

Status: Proposed v1

## FastAPI MVP Surface

### Dataset Endpoints

- `POST /api/datasets/load-demo`
- `POST /api/datasets/upload`
- `GET /api/datasets`
- `GET /api/datasets/{datasetId}`
- `GET /api/datasets/{datasetId}/frames`

### Run Endpoints

- `POST /api/datasets/{datasetId}/runs/detect`
- `POST /api/datasets/{datasetId}/runs/depth`
- `GET /api/runs`
- `GET /api/runs/{runId}`
- `GET /api/runs/{runId}/status`

### Frame And Detection Endpoints

- `GET /api/frames/{frameId}`
- `GET /api/frames/{frameId}/detections`
- `GET /api/frames/{frameId}/depth`
- `GET /api/frames/{frameId}/point-cloud`

### Correction Endpoints

- `POST /api/detections/{detectionId}/corrections`
- `GET /api/detections/{detectionId}/corrections`
- `PATCH /api/detections/{detectionId}/review-status`

### Metrics And Export Endpoints

- `GET /api/metrics/summary`
- `GET /api/metrics/runs/{runId}`
- `GET /api/exports/corrections`
- `GET /api/exports/detections`

## Thin .NET Bridge Surface

The .NET slice should stay intentionally small.

- `GET /bridge/health`
- `GET /bridge/runs/summary`
- `GET /bridge/datasets/summary`

## Interface Contract Principles

- FastAPI is the client-facing backend for the MVP.
- Each run must include explicit run type, model version, and processing status.
- Detection, correction, depth, and point-cloud payloads must be stable enough to support replayable demos.
- The .NET bridge should consume or proxy only summary-level metadata so it proves interoperability without duplicating FastAPI logic.

## Example Flow

1. Frontend loads a demo dataset or uploads a local dataset.
2. Frontend starts a detection run for the dataset.
3. FastAPI processes frames and persists structured detections.
4. Frontend requests detections and overlays them in the viewer.
5. Frontend starts a depth run or fetches an existing depth artifact.
6. Frontend requests a point-cloud artifact for 3D inspection.
7. User edits a detection and saves a correction.
8. Metrics and exports reflect the corrected state.
9. Optional .NET bridge exposes summary endpoints that can be shown as enterprise-facing integration touchpoints.

## Required Payload Contracts

- Dataset frame records must include image path, latitude, longitude, heading, timestamp, width, and height.
- Detection records must include frame id, class label, confidence, and bounding box in image pixel space.
- Depth records must include frame id, depth artifact URI, width, height, and depth scale.
- Point-cloud records must include frame id, point count, coordinate system, and downloadable asset reference.

## External Integrations

- Map tiles and basemaps via Mapbox or equivalent
- Object storage for dataset assets
- Optional post-MVP auth provider if the project later grows beyond local demo mode
