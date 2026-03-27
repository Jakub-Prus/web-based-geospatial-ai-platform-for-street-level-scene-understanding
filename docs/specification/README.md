# Application Specification

This folder contains the concrete project plan for the portfolio application:

- "Web-Based Geospatial AI Platform for Street-Level Scene Understanding"

The plan is intentionally aligned to the Cyclomedia Full Stack Developer: Geospatial & ML Systems role. It is designed to demonstrate four core pillars:

1. Geospatial data handling
2. ML systems integration
3. Advanced React-based visualization
4. Human-in-the-loop review and correction

## Current Build State

Implementation is currently complete through Slice 11:

- dataset loading and validation
- spatial browsing with stored camera markers
- .NET dataset summary bridge
- persisted detection runs
- correction-aware detection overlay rendering in the frontend viewer
- backend correction persistence with review status and original-versus-corrected state handling
- single-detection annotation editing with move, resize, redraw, relabel, and bounds clipping
- persisted MiDaS depth artifacts with explicit missing and failed fallback states
- persisted point-cloud artifacts generated from stored depth with a documented local camera coordinate system and deterministic subsampling

Three.js rendering, metrics, and export remain planned slices.

## Recommended Reading Order

1. `01-overview.md`
2. `02-goals-and-objectives.md`
3. `04-functional-requirements.md`
4. `06-system-architecture.md`
5. `14-demo-dataset-contract.md`
6. `15-scene-geometry-contract.md`
7. `13-implementation-roadmap.md`
8. `18-codex-implementation-slices.md`
9. `16-ai-assisted-development.md`
10. `17-cloud-deployment-sketch.md`
11. `19-external-assets-inventory.md`
12. `12-roadmap-and-future-work.md`

## MVP Summary

The MVP is a full stack platform where a user uploads geo-tagged street imagery, triggers ML inference, reviews detections in a map-plus-image interface, edits incorrect labels or boxes, and monitors output quality through dashboards.

## Delivery Planning

A concrete week-by-week execution plan is documented in `13-implementation-roadmap.md`.
A smaller, Codex-friendly build order is documented in `18-codex-implementation-slices.md`.

## Contracts

The MVP is anchored by two implementation contracts:

- `14-demo-dataset-contract.md`
- `15-scene-geometry-contract.md`

## Alignment Additions

To better match the target role, the plan also includes:

- `16-ai-assisted-development.md`
- `17-cloud-deployment-sketch.md`
- `19-external-assets-inventory.md`

## Job Alignment Summary

This project maps directly to the role:

- Geospatial datasets: map, GPS coordinates, imagery metadata, spatial storage
- ML pipelines: FastAPI inference, batch jobs, model outputs, monitoring
- React UI: responsive visualization with overlays and annotation tools
- 3D opportunity: Three.js point-cloud-style scene view
- System glue: FastAPI-based ML execution plus a thin .NET bridge for enterprise-style interoperability
- Review traceability: persisted correction records with recoverable original detections
