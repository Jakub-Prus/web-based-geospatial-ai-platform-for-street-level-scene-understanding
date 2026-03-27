# 06. System Architecture

Status: Updated after Slice 10

## High-Level Components

- React + TypeScript frontend for map, image, annotation, dashboard, and 3D views
- Thin .NET 8 bridge service for dataset metadata, run summaries, or orchestration-facing endpoints
- Python FastAPI service for inference, depth or segmentation generation, dataset loading, and processing APIs
- PostgreSQL with PostGIS for geospatial, annotation, and run metadata
- Object storage for imagery, derived artifacts, and export bundles
- Lightweight background job handling for batch ingestion and inference processing

## Service Responsibilities

### Frontend

- Presents map and street-level viewer workflows
- Renders overlays and focused single-box annotation tools
- Displays monitoring dashboards and job state
- Renders point-cloud-style 3D output from depth-derived data

### Python Service

- Loads model artifacts and executes inference
- Produces detections, segmentation masks, or depth maps
- Generates derived outputs for visualization, annotation review, and monitoring
- Serves lightweight dataset and run metadata needed by the frontend
- Persists review corrections separately from raw model detections
- Persists one validated local depth artifact per selected frame for later 3D slices

### .NET Bridge Service

- Exposes a minimal enterprise-style service boundary
- Can proxy run metadata, dataset summaries, or orchestration status
- Demonstrates interoperability between .NET and Python without dragging full auth or project management into MVP

## Data Flow

1. User loads or uploads images and metadata to the platform.
2. FastAPI validates the dataset and stores metadata references.
3. Files are persisted in object storage and indexed in PostgreSQL/PostGIS.
4. FastAPI runs or schedules inference and depth processing.
5. Detection outputs are stored in SQLite and depth artifacts are stored as local `.npy` files plus SQLite metadata for later map, image, and 3D rendering.
6. Optional .NET bridge reads run metadata and exposes summary endpoints.
7. Frontend retrieves map data, imagery references, detections, depth-derived geometry, and review state.
8. User selects one detection, edits or redraws the box inside the image bounds, and saves corrections through the FastAPI service.
9. Monitoring views aggregate original output and correction outcomes.

## Current Persistence Note

- The implemented MVP slices currently persist dataset, detection, and correction metadata in a local SQLite database inside the FastAPI service for fast iteration.
- Slice 10 adds `depth_artifacts` metadata in the same SQLite database and keeps the depth array itself on local disk under a service-managed artifact directory.
- PostgreSQL plus PostGIS remain part of the target Docker and deployment architecture for later slices that need richer geospatial storage.

## Data Lifecycle

The intended lifecycle is:

1. ingest
2. validate
3. index
4. infer
5. review
6. export
7. archive or extend

This should be visible in naming, API boundaries, and demo narration.

## Integration Points

- Map rendering library: Mapbox GL JS or Leaflet
- 3D rendering library: Three.js
- ML model family: YOLO for MVP, optional depth model for 3D view
- Container runtime: Docker

## Deferred Enterprise Layer

- Authentication and user management are intentionally deferred because they do not strengthen the core GIS, CV, and 3D story for the first demo.
- The .NET bridge remains intentionally thin so it demonstrates stack interoperability without consuming most of the build time.

## Architecture Diagram

```text
[React Frontend]
        |
        v
[.NET 8 Bridge Service] ------> [Python FastAPI Data + Inference Service] <-> [PostgreSQL + PostGIS]
         |                                      |
         |                                      +--------------------> [Object Storage]
         |
         +-------------- summary/orchestration--+
```
