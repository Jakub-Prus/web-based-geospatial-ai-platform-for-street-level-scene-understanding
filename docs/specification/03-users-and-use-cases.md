# 03. Users And Use Cases

Status: Proposed v1

## User Types

### Dataset Operator

- Uploads street-level datasets with GPS and timestamp metadata
- Launches inference jobs and inspects outputs on map and image views
- Exports reviewed outputs for downstream analysis

### Reviewer

- Opens detections from map or image context
- Edits bounding boxes and labels
- Approves, rejects, or comments on AI results

### Demo Observer

- Views processed outputs, point clouds, and monitoring summaries during a demo

## Main Use Cases

- User loads or uploads a dataset of street images with metadata
- User launches batch inference on the selected dataset
- User clicks a camera position on the map and opens the related street image
- User reviews detections rendered as overlays
- User edits incorrect labels or bounding boxes and saves corrections
- User compares original model output with reviewed output
- User inspects a depth-derived point-cloud-style 3D scene
- User views monitoring metrics such as confidence distribution and correction rate

## Role-Based Capability Summary

- Dataset operator can ingest data, run jobs, and export outputs
- Reviewer can modify annotations and submit review decisions
- Demo observer can inspect results and dashboard summaries

## Priority User Journey

The primary MVP journey is:

1. Dataset operator uploads or loads a dataset
2. System processes and georeferences it
3. Python inference service returns detections
4. Reviewer validates predictions in the UI
5. Reviewer explores the depth-derived 3D scene for the same frame
6. Corrections are saved and surfaced in dashboards
