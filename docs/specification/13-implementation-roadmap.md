# 13. Implementation Roadmap

Status: Updated after Slice 11

## Current Progress

Completed slices:

- Slice 0: contracts frozen
- Slice 1: repo skeleton
- Slice 2: local runtime
- Slice 3: dataset loading
- Slice 4: map marker browsing
- Slice 5: .NET bridge minimum
- Slice 6: detection backend
- Slice 7: detection overlay UI
- Slice 8: correction persistence backend
- Slice 9: annotation editing UI
- Slice 10: depth artifact backend
- Slice 11: point-cloud conversion

Next planned slice:

- Slice 12: Three.js viewer

## Planning Assumptions

- Timeline assumes one primary developer building a fast, portfolio-ready demo in a few days.
- Scope is optimized for demonstrating GIS, CV, maps, and 3D capability rather than enterprise platform completeness.
- Anything not directly strengthening the geospatial or ML systems story is deferred.

## MVP Definition

The MVP is complete when the platform can:

- load a geo-tagged street-level dataset,
- run detection and depth inference through the Python service,
- visualize frames and detections on a map and image viewer,
- render a depth-derived point-cloud-style 3D view,
- let a user correct detections,
- persist corrections and run metadata,
- show a basic monitoring dashboard,
- run locally through Docker Compose.

## Build Strategy

- Keep the architecture lean: frontend, FastAPI backend, and a very small .NET bridge.
- Use PostGIS and object storage only where they visibly improve the demo.
- Replace authentication and user management with a simple local demo mode.
- Freeze one demo dataset schema and one label taxonomy before building the UI.
- Treat depth-to-point-cloud as pseudo-LiDAR visualization, not survey-accurate reconstruction.
- Prefer building in atomic slices documented in `18-codex-implementation-slices.md`.

## Day 1: Foundations, Dataset, And Map

### Goals

- Establish the smallest architecture that can show geospatial data quickly.
- Get street-level frames visible on a map on the first day.

### Deliverables

- Repository structure for frontend, FastAPI service, and Docker setup
- Minimal .NET bridge service
- Docker Compose with frontend, FastAPI, PostgreSQL plus PostGIS, and storage
- Seed dataset loader or local file-based ingestion
- Finalized demo dataset contract
- React map view with camera markers
- Frame detail panel with image preview and metadata

### Build Tasks

- Initialize React + TypeScript frontend
- Initialize .NET 8 bridge service
- Initialize FastAPI backend
- Set up PostgreSQL with PostGIS in Docker Compose
- Define dataset schema with latitude, longitude, heading, and timestamp
- Freeze label classes for the demo
- Implement dataset seed or upload flow
- Render camera points on Mapbox or Leaflet
- Open selected frame details from the map
- Add one .NET health or summary endpoint

### Acceptance Criteria

- The stack starts with Docker Compose
- Frontend, FastAPI, and .NET bridge all start successfully
- Camera locations render correctly on the map
- Clicking a point opens the related image and frame metadata
- Dataset format is documented and reproducible
- Label set and sample assets are stable enough to drive the rest of the build

## Day 2: Detection Pipeline And Overlay Review

### Goals

- Turn the app from a GIS viewer into an ML-enabled GIS viewer.
- Make predictions visible in the image and on the map.

### Deliverables

- FastAPI detection endpoint using YOLO or equivalent
- Batch or dataset-level inference flow
- Detection persistence with confidence and class metadata
- Image overlay rendering for detections
- Basic run-status panel
- .NET bridge summary endpoint backed by FastAPI or shared storage

### Build Tasks

- Integrate object detection model in FastAPI
- Create inference endpoint and batch processing path
- Store detections linked to frames
- Render bounding boxes and labels in the frontend
- Add run metadata such as model version and completion time
- Define explicit no-detection and failed-run behavior
- Expose run summaries through the .NET bridge

### Acceptance Criteria

- A dataset can be processed end to end
- Detections appear as overlays on selected images
- Detections are queryable by frame or run
- Run status is visible in the UI
- Failed or empty runs produce usable UI feedback
- The .NET bridge can return at least one dataset or run summary

Status note:
Day 2 scope is now effectively complete in the current repository state.

## Day 3: Human-In-The-Loop Annotation

### Goals

- Show that the system is not just inference, but reviewable and correctable.
- Make the annotation workflow one of the strongest portfolio features.

### Deliverables

- Box creation, edit, resize, relabel, and delete tools
- Save-correction API
- Stored original prediction plus corrected annotation state
- Approval or rejection action for detections

### Build Tasks

- Build annotation controls in the image viewer
- Add correction persistence model
- Show original versus corrected state in the UI
- Add approval and rejection markers
- Update metrics from correction events
- Define invalid-box and out-of-bounds edit handling

### Acceptance Criteria

- A user can correct a bad detection and save the change
- Reloading the frame preserves the correction
- Original model output remains inspectable
- The correction workflow is demo-ready and visually clear
- Invalid edits are rejected predictably

Status note:
Day 3 annotation review is now implemented through Slice 9 for the focused MVP path. The frontend can select one existing detection, move or redraw the box, resize it, relabel it, clip the edit to image bounds, and save it through the Slice 8 correction endpoint while preserving the original detection state.

## Day 4: Depth, 3D, And Monitoring

### Goals

- Push the project into your specialization area.
- Add a compelling 3D feature and just enough monitoring to show system thinking.

### Deliverables

- Depth estimation or pseudo-depth pipeline
- Three.js point-cloud-style viewer
- Scene geometry contract
- Basic monitoring dashboard

### Build Tasks

- Integrate monocular depth estimation or a lightweight pseudo-depth step
- Convert depth output into point-cloud-style coordinates
- Render the result in Three.js
- Aggregate detection count, confidence, and correction rate
- Define point-cloud coordinate conventions and frame alignment

### Acceptance Criteria

- A selected frame can be inspected in 2D and 3D
- Monitoring view shows real values from the dataset and corrections
- The point-cloud output is visually coherent and stable for the demo dataset

Status note:
Day 4 is now partially complete in the current repository state. Slices 10 and 11 persist one validated depth artifact per selected frame and one deterministic sampled point-cloud payload per selected frame with clear missing and failed fallback states; Three.js rendering and monitoring remain for the next slices.

## Day 5: Export, Failure Handling, And Demo Polish

### Goals

- Close the remaining usability and demo gaps without changing core architecture.

### Deliverables

- Export of corrected results
- Final demo script and setup notes
- Error-state polish for ingestion, inference, and 3D generation
- README improvements and screenshots
- AI-assisted development notes
- Minimal Kubernetes deployment sketch

### Build Tasks

- Add export endpoint and export UI
- Add clear UI states for failed inference, missing metadata, and missing depth data
- Finalize demo walkthrough
- Capture screenshots or a short walkthrough video
- Document how AI assistants were used for scaffolding, debugging, or tests
- Add one sample Kubernetes manifest or deployment diagram

### Acceptance Criteria

- Corrected results can be exported
- The full demo can be run locally in one documented flow
- Failure states are understandable during a live demo
- AI-assisted workflow is documented clearly
- One cloud-native deployment artifact exists

## Day 5 Plus: Buffer And Polish

Use any remaining time for the parts that improve demo quality most:

- Better point-cloud rendering
- Faster map loading and frame navigation
- Cleaner annotation UX
- Stronger visuals, labels, and dashboard clarity
- Short walkthrough video or screenshots

## Final MVP Review Gate

Before calling MVP complete, verify:

- Frontend, Python, database, and storage run together locally
- The .NET bridge exposes at least one live integration endpoint
- A dataset can be ingested and mapped
- Detection and depth inference can be triggered and observed
- A user can correct detections in the UI
- A frame can be explored in a point-cloud-style 3D view
- Corrections affect stored review outcomes and dashboard metrics
- Dataset and geometry contracts are documented and respected by the implementation
- Setup and architecture are documented clearly enough for a recruiter or interviewer to inspect quickly

## Stretch Work If Ahead Of Schedule

- Add side-by-side temporal comparison for the same location
- Add native point-cloud or LiDAR-style ingestion
- Add background queue infrastructure beyond simple in-process orchestration
- Expand the .NET bridge into a fuller orchestration layer

## Recommended Demo Narrative

If this project is built for the Cyclomedia interview process, the demo should tell this story:

1. Upload and index geospatial street-level data.
2. Run ML inference and depth generation through a dedicated Python service.
3. Review predictions in a modern React geospatial UI.
4. Correct model output through a human-in-the-loop workflow.
5. Inspect the same scene in a point-cloud-style 3D view.
6. Track quality through monitoring metrics and exports.
