# 12. Roadmap And Future Work

Status: Proposed v1

Detailed execution sequencing is documented in `13-implementation-roadmap.md`.

## Phase 1: MVP

- Thin .NET bridge service for summary or orchestration endpoints
- FastAPI inference and geospatial data service
- Dataset load or upload with image plus metadata ingestion
- Map plus street-view review workspace
- Bounding-box correction and review workflow
- Depth-based 3D point-cloud-style viewer
- Monitoring dashboard for counts, confidence, and correction rates
- Fixed dataset and scene-geometry contracts
- AI-assisted development notes and minimal Kubernetes deployment sketch
- Docker-based local deployment

## Phase 2: Strong Enhancements

- Better segmentation or depth estimation pipeline
- Better filtering, search, and dataset comparison
- Export improvements and richer audit trail views

## Phase 3: Differentiators

- Time-based comparison for the same location across multiple captures
- Smarter large-dataset loading and tile-based rendering strategies
- Model version comparison workflows
- Reviewer productivity analytics

## Future Ideas

- Active learning loop for retraining support
- Native LiDAR ingestion
- Kubernetes deployment profile
- External customer portal or partner API

## MVP Cut Line

If time slips, cut in this order:

1. Advanced monitoring charts
2. Export polish
3. Depth quality improvements
4. Temporal comparison or large-dataset optimizations

Do not cut:

- thin .NET interoperability slice,
- map plus frame viewer,
- object detection overlays,
- correction workflow,
- basic depth-to-point-cloud demo,
- Dockerized local run.
