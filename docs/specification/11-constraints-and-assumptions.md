# 11. Constraints And Assumptions

Status: Proposed v1

## Constraints

- This project is intended as an application-ready portfolio piece, so scope must stay achievable by one developer.
- MVP should prioritize strong system integration over breadth of geospatial formats.
- Time investment should focus on features that clearly map to the target role description.

## Assumptions

- A curated demo dataset of street-level images with latitude, longitude, and timestamps is available.
- The demo dataset will use one fixed metadata schema documented in `14-demo-dataset-contract.md`.
- The MVP will use one fixed label taxonomy to avoid UI and export churn during implementation.
- YOLO-based object detection is sufficient for MVP demonstration quality.
- One optional depth or segmentation model is enough to demonstrate richer ML integration.
- Pseudo-LiDAR visualization can be derived from depth output rather than requiring native LiDAR capture.
- Scene geometry assumptions for depth-to-point-cloud conversion will be documented in `15-scene-geometry-contract.md`.

## Technical Boundaries

- Real-world production scale will be simulated through architecture and workflow design, not fully reproduced in MVP infrastructure.
- The first release will optimize for clarity, maintainability, and demonstration value rather than exhaustive feature coverage.

## Early Risks

- Map-to-image alignment may require careful metadata validation.
- Large imagery volumes can quickly stress storage and frontend performance.
- Human correction UX can become complex if annotation interactions are not kept focused.
- Monocular depth may look compelling visually while still being geometrically noisy, so the 3D viewer should be presented as pseudo-LiDAR rather than survey-grade reconstruction.
