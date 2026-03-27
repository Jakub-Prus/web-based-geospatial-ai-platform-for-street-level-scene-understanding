# Web-Based Geospatial AI Platform for Street-Level Scene Understanding

Slice 11 point-cloud conversion workspace for the planned geospatial AI demo platform.

Slices `0` through `11` are now implemented:

- dataset contract and geometry contract are frozen
- React, FastAPI, and .NET service skeletons are in place
- Docker Compose starts the local stack
- A2D2 subset metadata can be loaded and browsed on the map
- the .NET bridge exposes dataset summary endpoints
- detection runs are persisted in FastAPI
- stored detections render in the frontend image viewer with run-state feedback
- human review corrections are persisted separately from original detections in FastAPI
- one selected detection can now be relabeled, moved, resized, redrawn, clipped to image bounds, and saved from the frontend
- one selected frame can now produce a persisted depth artifact with validated source-image dimensions and clear missing-depth fallback state
- one selected frame can now return a stable stored point-cloud payload in a documented local camera coordinate system

## Specification Docs

Project planning templates live under [`docs/specification`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/README.md).

This specification now contains a Cyclomedia-aligned portfolio project plan covering geospatial ingestion, ML inference, visualization, human review, and phased delivery.

External sources and downloaded model assets are frozen before implementation in [`docs/specification/19-external-assets-inventory.md`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/19-external-assets-inventory.md).

## Repository Layout

- `frontend/`: Vite + React + TypeScript scaffold
- `services/ml-fastapi/`: FastAPI scaffold for ML-facing APIs
- `services/bridge-dotnet/`: .NET 8 Web API scaffold for bridge endpoints
- `infra/`: infrastructure placeholders for Docker and deployment assets

## Run Locally

### Prerequisites

For the standard local setup, install:

- Docker Desktop with `docker compose`
- `bash`
- `curl`
- `tar`

If you want to run the apps outside containers for development, also install:

- Node.js 20
- Python 3.12
- .NET 8 SDK

### 1. One-command bootstrap

To create `.env`, download the pinned assets, extract the default A2D2 subset when needed, start Docker Compose, wait for the services, load the dataset automatically, and trigger Slice 6 detection when needed, run:

```bash
bash ./scripts/start_local.sh
```

The script is idempotent for the normal local workflow:

- it reuses an existing `.env`
- it skips downloads for files already present in `data/raw/`
- it skips extraction when `data/raw/a2d2-subset/` already contains files
- it starts the stack in detached mode
- it finishes by calling `POST /datasets/load`
- it triggers `POST /datasets/{dataset_id}/runs/detect` when the loaded dataset has no detection run yet or the latest persisted run ended `empty` or `failed`

Set `START_LOCAL_RUN_DETECTION=0` before running the script if you want to skip the automatic detection step and start faster while debugging unrelated parts of the stack.

On a fresh machine, the first run can take a while because it may download the pinned model files and the `a2d2-preview.tar` archive before extracting the subset.

Use the manual steps below if you want to troubleshoot or run only part of the setup.

### 2. Create local environment overrides

Copy the example environment file before starting the stack:

```bash
cp .env.example .env
```

The defaults in [`.env.example`](.env.example) are enough for a first run. Edit `.env` only if you need different ports, credentials, or service URLs.

### 3. Start the full stack with Docker

From the repository root, run:

```bash
docker compose up --build
```

Core endpoints after startup:

- frontend: `http://localhost:3000`
- frontend health: `http://localhost:3000/health`
- FastAPI root: `http://localhost:8000/`
- FastAPI health: `http://localhost:8000/health`
- .NET bridge root: `http://localhost:8080/`
- .NET bridge health: `http://localhost:8080/health`
- MinIO API: `http://localhost:9000`
- MinIO console: `http://localhost:9001`
- PostGIS: `localhost:5432`

Stop the stack with:

```bash
docker compose down
```

### 4. Prepare local data assets

The runtime starts without seeded data, but the dataset and detection flows expect assets under `data/raw/`.

Download the pinned model files:

```bash
pwsh ./scripts/download_external_assets.ps1
```

If you also want the A2D2 preview archive needed for local dataset extraction, include the optional flag:

```bash
pwsh ./scripts/download_external_assets.ps1 -DownloadA2D2Preview
```

Extract a small local subset from the preview archive:

```bash
pwsh ./scripts/extract_a2d2_subset.ps1
```

After the stack is running and the subset exists, load it through FastAPI:

```bash
curl -X POST http://localhost:8000/datasets/load \
  -H "Content-Type: application/json" \
  -d '{}'
```

Trigger one Slice 10 depth artifact for a selected frame:

```bash
curl -X POST http://localhost:8000/datasets/{dataset_id}/frames/{frame_id}/depth \
  -H "Content-Type: application/json" \
  -d '{}'
```

Check the current depth state for a frame:

```bash
curl http://localhost:8000/datasets/{dataset_id}/frames/{frame_id}/depth
```

Trigger one Slice 11 point-cloud payload from the latest stored depth artifact:

```bash
curl -X POST http://localhost:8000/datasets/{dataset_id}/frames/{frame_id}/point-cloud \
  -H "Content-Type: application/json" \
  -d '{}'
```

Check the current point-cloud state and inline payload for a frame:

```bash
curl http://localhost:8000/datasets/{dataset_id}/frames/{frame_id}/point-cloud
```

### 5. Run services outside Docker

If you prefer live-reload development, start the infrastructure services first:

```bash
docker compose up postgis object-storage
```

Then run each app in a separate terminal.

Frontend:

```bash
cd frontend
export VITE_FASTAPI_BASE_URL="http://localhost:8000"
export VITE_BRIDGE_BASE_URL="http://localhost:8080"
export VITE_OBJECT_STORAGE_CONSOLE_URL="http://localhost:9001"
npm ci
npm run dev -- --port 3000
```

FastAPI:

```bash
cd services/ml-fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

.NET bridge:

```bash
cd services/bridge-dotnet
export ASPNETCORE_URLS="http://localhost:8080"
export MLApi__BaseUrl="http://localhost:8000"
dotnet restore
dotnet run
```

## Slice 3 Dataset API

FastAPI now supports the Slice 3 dataset-loading flow:

- `POST /datasets/load`
- `GET /datasets`
- `GET /datasets/{dataset_id}/frames`

By default, the loader targets `data/raw/a2d2-subset/` and supplements missing GPS and orientation metadata from `data/raw/a2d2-preview.tar` when needed for the extracted A2D2 subset.

## Slice 4 Spatial Browsing

The frontend now loads stored datasets and renders frame markers from persisted coordinates so you can browse the dataset spatially before ML overlays are added.

Additional browsing endpoints:

- `GET /datasets/{dataset_id}/frames/{frame_id}`
- `GET /datasets/{dataset_id}/frames/{frame_id}/preview`

The preview panel is driven from the selected map marker and displays the stored image plus key metadata for the chosen frame.

## Slice 5 .NET Bridge

The `.NET` bridge now exposes a minimal interoperability surface backed by a live read from FastAPI dataset metadata.

Bridge endpoints:

- `GET /bridge/health`
- `GET /bridge/datasets/summary`

The dataset summary endpoint proxies FastAPI `GET /datasets`, returning dataset counts, total frame counts, and per-dataset summary metadata without introducing write behavior or duplicate data ownership in `.NET`.

## Slice 6 Detection Backend

FastAPI now supports persisted detection runs backed by `data/raw/models/yolo11n.pt`.

The Docker image for `services/ml-fastapi` now includes the native runtime libraries Ultralytics needs for local inference, including `libxcb1`, so Slice 6 detection can execute inside the Compose stack.

Detection endpoints:

- `POST /datasets/{dataset_id}/runs/detect`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/status`
- `GET /datasets/{dataset_id}/frames/{frame_id}/detections`

Each run persists explicit `running`, `completed`, `empty`, or `failed` state plus stored bounding boxes in image pixel coordinates for later overlay and correction slices.

## Slice 7 Detection Overlay UI

The selected-frame panel renders stored detections directly over the frame image.

The viewer includes:

- bounding-box overlays scaled from persisted image pixel coordinates
- class-label and confidence chips inside each rendered box
- a run-status summary with model name, processed frames, detection counts, and timestamps
- useful empty states for no selected frame, no run yet, failed run, running run, and no detections for the chosen frame

## Slice 8 Correction Persistence Backend

FastAPI now persists reviewer decisions separately from model detections so the original output remains queryable after a correction is saved.

Correction endpoints:

- `POST /datasets/{dataset_id}/frames/{frame_id}/detections/{detection_id}/correction`
- `GET /datasets/{dataset_id}/frames/{frame_id}/corrections`

Each correction stores:

- the linked original detection id
- a review status of `pending`, `approved`, or `rejected`
- an optional corrected label and corrected bounding-box state
- timestamps for initial save and latest update

The correction response includes the `original_detection`, optional `corrected_detection`, and the resolved `effective_detection` so the backend can preserve both states without mutating the raw detection row.

## Slice 9 Annotation Editing UI

The frontend review workspace now includes a focused single-annotation editor for existing detections.

The editor now supports:

- selecting one stored detection at a time from the overlay or the editor list
- dragging the selected box to move it within the image bounds
- resizing from the four corner handles
- redrawing the box directly on the image stage
- changing the label before save
- clipping coordinates to image bounds while preserving `x_min`, `y_min`, `x_max`, and `y_max`
- readable validation errors when a clipped edit collapses to an invalid box

Saved edits post to the existing Slice 8 correction endpoint and update the effective detection state without overwriting the original model output.

## Slice 10 Depth Artifact Backend

FastAPI now supports one frame-scoped depth inference run backed by `data/raw/models/dpt_swin2_tiny_256.pt`.

The service uses the official MiDaS `DPT_SwinV2_T_256` architecture with the pinned local weight file and persists each successful artifact as a local `.npy` file containing single-channel float32 inverse-depth values.

Depth endpoints:

- `POST /datasets/{dataset_id}/frames/{frame_id}/depth`
- `GET /datasets/{dataset_id}/frames/{frame_id}/depth`

The depth response returns a clear `missing`, `running`, `completed`, or `failed` state plus the latest frame-scoped run metadata and optional artifact metadata.

Each stored artifact includes:

- `frame_id`
- `depth_uri`
- `width`
- `height`
- `depth_format`
- `depth_scale`

The backend validates the persisted depth map shape against the source image dimensions before saving and updates the frame record with the latest stored `depth_path`.

## Slice 11 Point-Cloud Conversion

FastAPI now supports deterministic point-cloud conversion from the latest stored depth artifact for one selected frame.

Point-cloud endpoints:

- `POST /datasets/{dataset_id}/frames/{frame_id}/point-cloud`
- `GET /datasets/{dataset_id}/frames/{frame_id}/point-cloud`

The backend reads the latest stored inverse-depth `.npy`, filters invalid values, converts pixel centers into a right-handed local camera coordinate system, and persists one compressed `.npz` artifact containing an `Nx3` float32 `points` array.

The chosen coordinate convention is:

- `+X` right
- `+Y` up
- `+Z` forward

Each point-cloud artifact includes:

- `point_cloud_uri`
- `point_format`
- `coordinate_system`
- `source_point_count`
- `point_count`
- `subsample_step`
- `intrinsics_source`
- `fx`
- `fy`
- `cx`
- `cy`

Point payload generation is deterministic for a given stored depth artifact. The service uses row-major subsampling with a default browser-safe cap of `20,000` points, and `GET /datasets/{dataset_id}/frames/{frame_id}/point-cloud` returns the latest inline sampled XYZ payload for the frame.

## Local Verification

Frontend checks:

```bash
cd frontend
npm install
npm test
npm run build
```

Frontend coverage currently runs through Vitest with V8 coverage and passes at `75.19%` total coverage while exercising dataset selection, correction-aware overlay rendering, annotation geometry helpers, and correction-save behavior.

FastAPI checks:

```bash
cd services/ml-fastapi
.\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-report=term-missing
```

The current FastAPI suite passes at `82%` total coverage, including Slice 10 depth-artifact coverage plus Slice 11 point-cloud success, deterministic payload, filtering, and missing-depth fallback coverage.

Slice 10 real-asset verification:

- dataset: `data/raw/a2d2-subset/`
- model: `data/raw/models/dpt_swin2_tiny_256.pt`
- verified frame: `20190401121727_camera_frontright_000013460`
- stored artifact: `services/ml-fastapi/data/slice10-verify-depth/dataset-1/20190401121727_camera_frontright_000013460/run-1.npy`
- source dimensions: `1920x1208`
- stored array shape: `1208x1920`
- result: stored depth artifact dimensions match the source image dimensions exactly

Slice 11 real-asset verification:

- dataset: `data/raw/a2d2-subset/`
- verified frame: `20190401121727_camera_frontright_000013460`
- source depth artifact: `services/ml-fastapi/data/slice10-verify-depth/dataset-1/20190401121727_camera_frontright_000013460/run-1.npy`
- stored point-cloud artifact: `services/ml-fastapi/data/slice11-verify-point-cloud/dataset-1/20190401121727_camera_frontright_000013460/run-2.npz`
- source valid depth pixels: `1,938,775`
- returned point count: `19,988`
- subsample step: `97`
- coordinate system: `camera_local_right_handed_x_right_y_up_z_forward`
- intrinsics source: `frame_metadata`
- stability check: two consecutive conversions returned identical ordered XYZ payloads for the same stored depth artifact

.NET bridge tests require a local `.NET` SDK, not just the runtime. In the current environment `dotnet.exe` is present, but `dotnet --list-sdks` returns no installed SDKs.
