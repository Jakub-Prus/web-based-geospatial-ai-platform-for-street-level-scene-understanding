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
