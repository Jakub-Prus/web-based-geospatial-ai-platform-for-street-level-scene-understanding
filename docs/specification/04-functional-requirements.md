# 04. Functional Requirements

Status: Proposed v1

## Dataset Ingestion

- The system must allow a user to load a dataset containing street-level images and metadata including latitude, longitude, heading, and timestamp.
- The system must validate required metadata before a dataset is accepted for processing.
- The system should support both seeded demo data and local file-based ingestion for fast development.

## Geospatial Data Handling

- The system must store camera positions as geospatial coordinates.
- The system must support map-based browsing of camera locations.
- The system must support coordinate transformation required for map rendering and overlay alignment.
- The system should support spatial filtering by bounding box or proximity.

## ML Inference Pipeline

- The system must send selected images to the Python FastAPI inference service.
- The inference service must run object detection on street-level images.
- The inference service must support one additional scene understanding output such as segmentation or monocular depth estimation.
- The system must persist detections, confidence scores, and model version metadata.
- The system must support asynchronous batch inference jobs with status tracking.

## Visualization

- The frontend must render a 2D map with camera positions and dataset context.
- The frontend must open a street image viewer from a selected camera position.
- The frontend must display detection overlays such as bounding boxes, labels, vectors, and review states.
- The system must provide a 3D viewer for pseudo-LiDAR or point-cloud-style visualization derived from depth outputs.

## Human-In-The-Loop Review

- The system must allow a user to create, edit, and delete bounding boxes.
- The system must allow a user to change labels and mark detections as approved or rejected.
- The system must store both original model output and corrected annotations.
- The system should record correction timestamps and preserve the previous prediction state.

## Monitoring And Reporting

- The system must expose dashboards for detection volume, confidence distribution, approval rate, and correction rate.
- The system should show model performance trends by dataset or run.
- The system must allow export of approved results and annotations.

## Architecture

- The system must expose a clean separation between the visualization client and the ML or data-processing backend.
- The system should keep architecture lightweight enough to be completed in a few days without undermining the GIS, CV, and 3D demo value.
