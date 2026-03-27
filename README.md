# Web-Based Geospatial AI Platform for Street-Level Scene Understanding

Slice 4 spatial browsing workspace for the planned geospatial AI demo platform.

## Specification Docs

Project planning templates live under [`docs/specification`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/README.md).

This specification now contains a Cyclomedia-aligned portfolio project plan covering geospatial ingestion, ML inference, visualization, human review, and phased delivery.

External sources and downloaded model assets are frozen before implementation in [`docs/specification/19-external-assets-inventory.md`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/19-external-assets-inventory.md).

## Repository Layout

- `frontend/`: Vite + React + TypeScript scaffold
- `services/ml-fastapi/`: FastAPI scaffold for ML-facing APIs
- `services/bridge-dotnet/`: .NET 8 Web API scaffold for bridge endpoints
- `infra/`: infrastructure placeholders for Docker and deployment assets

## Local Runtime

Start the full empty stack with one command:

```powershell
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

Compose runs with built-in defaults, and [`.env.example`](.env.example) documents every supported override for ports, credentials, and service URLs.

Stop the stack with:

```powershell
docker compose down
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

Detection endpoints:

- `POST /datasets/{dataset_id}/runs/detect`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/status`
- `GET /datasets/{dataset_id}/frames/{frame_id}/detections`

Each run persists explicit `running`, `completed`, `empty`, or `failed` state plus stored bounding boxes in image pixel coordinates for later overlay and correction slices.
