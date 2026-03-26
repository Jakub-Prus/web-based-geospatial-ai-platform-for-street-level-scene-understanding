# Web-Based Geospatial AI Platform for Street-Level Scene Understanding

Slice 1 repository skeleton for the planned geospatial AI demo platform.

## Specification Docs

Project planning templates live under [`docs/specification`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/README.md).

This specification now contains a Cyclomedia-aligned portfolio project plan covering geospatial ingestion, ML inference, visualization, human review, and phased delivery.

External sources and downloaded model assets are frozen before implementation in [`docs/specification/19-external-assets-inventory.md`](C:/Github/my-projects/web-Based%20Geospatial%20AI%20Platform%20for%20Street-Level%20Scene%20Understanding/docs/specification/19-external-assets-inventory.md).

## Repository Layout

- `frontend/`: Vite + React + TypeScript scaffold
- `services/ml-fastapi/`: FastAPI scaffold for ML-facing APIs
- `services/bridge-dotnet/`: .NET 8 Web API scaffold for bridge endpoints
- `infra/`: infrastructure placeholders for Docker and deployment assets

## Local Boot Commands

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

FastAPI:

```powershell
cd services/ml-fastapi
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

.NET bridge:

```powershell
cd services/bridge-dotnet
dotnet run
```

The current development environment used for this slice does not have the .NET SDK installed, so the bridge scaffold is present but was not executed locally here.
