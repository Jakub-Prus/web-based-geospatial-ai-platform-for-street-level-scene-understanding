# 18. Codex Implementation Slices

Status: Proposed v2

## Purpose

This document breaks the MVP into small implementation slices that are easy to build with Codex and easy to review after each step.

Each slice is intentionally narrow. The goal is to keep changes understandable, testable, and reversible.

## Global Rules

- Complete one slice at a time.
- Do not start the next slice until the current slice stop condition is satisfied.
- If a slice becomes too large, split it again instead of pushing through confusion.
- Keep each slice small enough that you can explain:
  - what changed
  - which files changed
  - how you verified it
- Prefer vertical slices that produce something visible or queryable.

## Shared Decisions For All Slices

- Main local dataset source: `data/raw/a2d2-subset/`
- Detection weights: `data/raw/models/yolo11n.pt`
- Depth weights: `data/raw/models/dpt_swin2_tiny_256.pt`
- Dataset contract: `14-demo-dataset-contract.md`
- Geometry contract: `15-scene-geometry-contract.md`
- External asset inventory: `19-external-assets-inventory.md`

## Recommended Service Layout

- `frontend/`
- `services/ml-fastapi/`
- `services/bridge-dotnet/`
- `infra/`

## Slice 0: Freeze Contracts

### Goal

Lock the data assumptions before writing application code.

### Read First

- `14-demo-dataset-contract.md`
- `15-scene-geometry-contract.md`
- `19-external-assets-inventory.md`

### Decide And Write Down

- final label set
- final frame metadata fields
- final bbox format
- final local 3D axis convention
- final chosen A2D2 camera for MVP

### Do Not Implement Yet

- no APIs
- no UI
- no schema migrations

### Stop Condition

- You can state the exact dataset fields, bbox contract, and point-cloud convention without guessing.

## Slice 1: Repo Skeleton

### Goal

Create the minimal codebase layout with bootstrapped applications only.

### Implement

- React app scaffold in `frontend/`
- FastAPI scaffold in `services/ml-fastapi/`
- .NET 8 Web API scaffold in `services/bridge-dotnet/`
- `infra/` folder for Docker and deployment files

### Expected Files

- `frontend/package.json`
- `services/ml-fastapi/requirements.txt` or equivalent
- `services/ml-fastapi/app/main.py`
- `services/bridge-dotnet/*.csproj`
- `infra/`

### Do Not Implement Yet

- no database logic
- no dataset parsing
- no map

### Verification

- frontend dev or container entry exists
- FastAPI app starts
- .NET app starts

### Stop Condition

- All project folders exist and each service is bootstrapped.

## Slice 2: Local Runtime

### Goal

Run the whole empty stack locally with one command.

### Implement

- `docker-compose.yml`
- container definitions for:
  - frontend
  - FastAPI
  - .NET bridge
  - PostgreSQL with PostGIS
  - object storage or a local substitute

### Expected Outputs

- working container build contexts
- environment variable strategy
- health endpoint exposure

### Do Not Implement Yet

- no seeded dataset
- no detection
- no UI logic beyond startup

### Verification

- `docker compose up` starts all services
- frontend responds
- FastAPI health endpoint responds
- .NET bridge health endpoint responds

### Stop Condition

- One command starts the stack successfully and all core services are reachable.

## Slice 3: Dataset Loading

### Goal

Load one small real dataset subset and persist frame metadata.

### Input

- `data/raw/a2d2-subset/`

### Implement

- dataset registration model
- frame metadata model
- metadata parser for A2D2 subset
- validation for required fields
- one FastAPI endpoint to trigger load or seed

### Expected Tables Or Models

- `datasets`
- `frames`

### Do Not Implement Yet

- no map rendering
- no detection
- no .NET summary integration

### Verification

- load endpoint succeeds on the local subset
- bad metadata is rejected clearly
- frame rows exist in the database
- one API can return stored frame metadata

### Stop Condition

- A dataset is loaded and frame metadata can be queried from FastAPI.

## Slice 4: Map Marker Browsing

### Goal

Visualize the stored frames spatially before ML is added.

### Implement

- frontend dataset selection view
- map component
- camera markers from stored lat and lon
- frame selection behavior
- frame preview panel

### API Needed

- dataset list
- frame list with coordinates
- frame detail

### Do Not Implement Yet

- no detection overlays
- no correction UI
- no 3D viewer

### Verification

- markers render from real database values
- clicking a marker opens the correct image preview
- switching dataset does not break the map

### Stop Condition

- You can browse the dataset spatially and inspect one frame from the map.

## Slice 5: .NET Bridge Minimum

### Goal

Add the smallest credible `.NET` signal for mixed-stack interoperability.

### Implement

- `.NET` health endpoint
- `.NET` dataset summary endpoint
- one integration method:
  - proxy to FastAPI, or
  - shared read from database

### API Needed

- `GET /bridge/health`
- `GET /bridge/datasets/summary`

### Do Not Implement Yet

- no auth
- no project management
- no write logic in `.NET`

### Verification

- `.NET` service returns a summary derived from real loaded data
- if FastAPI is down, the failure is understandable

### Stop Condition

- The bridge proves a live `.NET` to data-path connection.

## Slice 6: Detection Run Backend

### Goal

Introduce model inference and persist detections.

### Input

- `data/raw/models/yolo11n.pt`

### Implement

- run model for detection
- run persistence
- detection persistence
- run status fields
- explicit failed-run and empty-run states

### Expected Tables Or Models

- `inference_runs`
- `detections`

### API Needed

- trigger detection run
- get run status
- get detections by frame

### Do Not Implement Yet

- no overlay UI
- no correction editing

### Verification

- a run can be started
- detections are stored for at least one frame
- no-detection results do not crash the flow

### Stop Condition

- Backend detection works end to end on the local subset.

## Slice 7: Detection Overlay UI

### Goal

Render stored detections on the selected frame.

### Implement

- image viewer
- bbox overlay layer
- label and confidence rendering
- run status display in UI

### Input Contract

- bbox values stay in image pixel coordinates

### Do Not Implement Yet

- no editing tools
- no correction save

### Verification

- detections align with the image
- labels and confidence values are readable
- empty state is visible for frames without detections

### Stop Condition

- One frame can be visually inspected with correct overlays.

## Slice 8: Correction Persistence Backend

### Goal

Store human corrections separately from model output.

### Implement

- correction model
- save correction endpoint
- fetch corrections endpoint
- review status field
- original versus corrected state handling

### Expected Tables Or Models

- `corrections`

### Do Not Implement Yet

- no box drawing tools
- no advanced audit timeline

### Verification

- correction save works
- reloading the frame returns saved corrections
- original detection is still recoverable

### Stop Condition

- One detection can be corrected and that correction survives reload.

## Slice 9: Annotation Editing UI

### Goal

Make corrections editable in the frontend.

### Implement

- select detection
- move or redraw box
- resize box
- change label
- reject invalid box coordinates

### Input Contract

- clip boxes to image bounds
- preserve `x_min`, `y_min`, `x_max`, `y_max`

### Do Not Implement Yet

- no polygon tools
- no batch editing

### Verification

- edited boxes cannot escape image bounds
- label changes persist
- invalid edits show understandable errors

### Stop Condition

- A user can visually edit one box and save it successfully.

## Slice 10: Depth Artifact Backend

### Goal

Produce one stored depth artifact per selected frame.

### Input

- `data/raw/models/dpt_swin2_tiny_256.pt`

### Implement

- depth inference step
- depth artifact persistence
- width and height validation
- missing-depth fallback

### Expected Tables Or Models

- `depth_artifacts`

### Do Not Implement Yet

- no point-cloud conversion
- no 3D viewer

### Verification

- one selected frame gets a depth artifact
- stored dimensions match the source image
- missing depth produces a clear failure state

### Stop Condition

- One frame has a valid stored depth artifact.

## Slice 11: Point-Cloud Conversion

### Goal

Turn stored depth into a point-cloud payload.

### Implement

- pixel-to-3D conversion
- local coordinate convention from the geometry contract
- point subsampling
- point-cloud artifact storage or streaming

### Expected Tables Or Models

- `point_cloud_artifacts`

### Do Not Implement Yet

- no fancy rendering polish
- no multi-frame registration

### Verification

- one frame produces a stable point-cloud payload
- invalid depth values are filtered
- point count is capped for browser performance

### Stop Condition

- One frame returns a valid point-cloud payload in the agreed coordinate system.

## Slice 12: Three.js Viewer

### Goal

Display the point cloud interactively in the frontend.

### Implement

- Three.js scene
- point rendering
- orbit or equivalent camera controls
- loading state
- empty or failed 3D state

### Do Not Implement Yet

- no global scene merge
- no advanced shaders

### Verification

- selecting a frame opens a stable interactive 3D view
- controls are usable
- failure state is understandable when no point cloud exists

### Stop Condition

- A selected frame can be inspected interactively in 3D.

## Slice 13: Metrics

### Goal

Show minimal monitoring that reflects real system activity.

### Implement

- detection count
- average confidence
- correction count
- correction rate

### API Needed

- summary metrics
- optional run-specific metrics

### Do Not Implement Yet

- no advanced time-series dashboards
- no model comparison

### Verification

- metrics change after a run
- metrics change again after corrections

### Stop Condition

- The dashboard reflects real processed and corrected data.

## Slice 14: Export

### Goal

Let corrected outputs leave the system.

### Implement

- export endpoint
- one documented export format
- one frontend export trigger

### Recommended Format

- JSON first

### Do Not Implement Yet

- no multiple export formats
- no async export jobs unless necessary

### Verification

- corrected detections download successfully
- exported data matches stored corrections

### Stop Condition

- Corrected detections can be exported in one stable format.

## Slice 15: Demo Hardening

### Goal

Make the project reliable and easy to explain in a live walkthrough.

### Implement

- failure-state UI
- setup instructions
- screenshots or demo script
- AI-assisted development note
- minimal Kubernetes sketch

### Required Failures To Handle

- bad dataset metadata
- no detections
- failed detection run
- missing depth artifact
- missing point cloud

### Verification

- a new machine can follow the docs
- a live walkthrough can be completed without hidden manual fixes

### Stop Condition

- You can run the demo from docs alone and explain each subsystem clearly.

## Exact Implementation Order

Use this order:

1. Slice 0
2. Slice 1
3. Slice 2
4. Slice 3
5. Slice 4
6. Slice 5
7. Slice 6
8. Slice 7
9. Slice 8
10. Slice 9
11. Slice 10
12. Slice 11
13. Slice 12
14. Slice 13
15. Slice 14
16. Slice 15

## Safe Cuts If Time Runs Out

Cut in this order:

1. Kubernetes artifact polish
2. Export UI polish
3. Advanced metric presentation
4. Point-cloud visual polish

Do not cut:

- dataset loading
- map marker browsing
- detection run
- correction persistence
- point-cloud generation
- 3D viewer

## How To Use This With Codex

For each slice:

1. Tell Codex the exact slice number.
2. Ask it to inspect the related contracts before coding.
3. Ask it to implement only that slice.
4. Ask it to verify the stop condition before moving on.

Example:

```text
Implement Slice 3 from docs/specification/18-codex-implementation-slices.md.
Read docs/specification/14-demo-dataset-contract.md first.
Only implement dataset loading and metadata persistence.
Do not start map rendering or detection.
Verify the slice stop condition before finishing.
```

## Ready-To-Use Codex Prompts

### Slice 0 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 0 only.
Read docs/specification/14-demo-dataset-contract.md, docs/specification/15-scene-geometry-contract.md, and docs/specification/19-external-assets-inventory.md first.
Do not write application code yet.
Produce the final locked decisions for:
- label taxonomy
- frame metadata fields
- bbox format
- local 3D axis convention
- chosen A2D2 camera for MVP
If needed, update the docs so these decisions are explicit.
Do not start APIs, UI, schema migrations, or runtime setup.
Verify the Slice 0 stop condition before finishing.
```

### Slice 1 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 1 only.
Create the minimal repo skeleton:
- frontend/
- services/ml-fastapi/
- services/bridge-dotnet/
- infra/
Bootstrap a React frontend, a FastAPI service, and a .NET 8 Web API service.
Do not add database logic, dataset parsing, maps, or ML code yet.
Keep the scaffolding minimal and easy to understand.
At the end, verify that each service is bootstrapped and explain which files were created.
```

### Slice 2 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 2 only.
Set up the local runtime so the stack starts with one command.
Add Docker Compose and container definitions for:
- frontend
- FastAPI
- .NET bridge
- PostgreSQL with PostGIS
- object storage or a local substitute
Expose simple health endpoints or startup pages.
Do not seed data or implement features yet.
Verify that docker compose up starts the stack and that the core services are reachable.
```

### Slice 3 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 3 only.
Read docs/specification/14-demo-dataset-contract.md first.
Use data/raw/a2d2-subset/ as the input dataset.
Implement:
- dataset registration model
- frame metadata model
- A2D2 subset metadata parser
- validation for required fields
- one FastAPI endpoint to load or seed the dataset
Do not implement maps, detection, or .NET summary integration yet.
Verify that the dataset loads, bad metadata is rejected clearly, and frame metadata can be queried from FastAPI.
```

### Slice 4 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 4 only.
Build spatial browsing for the already loaded dataset.
Implement:
- frontend dataset selection view
- map component
- camera markers from stored coordinates
- frame selection from the map
- frame preview panel
Use only the dataset/frame APIs needed for browsing.
Do not implement detection overlays, correction UI, or 3D view yet.
Verify that clicking a marker opens the correct frame preview.
```

### Slice 5 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 5 only.
Add the smallest possible .NET bridge for mixed-stack signaling.
Implement:
- .NET health endpoint
- .NET dataset summary endpoint
- one live integration path, either proxying FastAPI or reading shared metadata
Do not add authentication, project management, or write logic in .NET.
Verify that the .NET bridge returns at least one real summary from loaded data.
```

### Slice 6 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 6 only.
Use data/raw/models/yolo11n.pt.
Implement the detection backend:
- trigger detection run
- run persistence
- detection persistence
- failed-run state
- empty-detection state
Do not implement overlay UI or correction editing yet.
Verify that a run can be triggered and stored detections exist for at least one frame.
```

### Slice 7 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 7 only.
Render stored detections in the frontend image viewer.
Implement:
- image viewer
- bbox overlay layer
- label rendering
- confidence rendering
- run status display
Keep bbox handling in image pixel coordinates as defined in the dataset contract.
Do not implement editing tools yet.
Verify that one frame can be visually inspected with correct overlays and useful empty states.
```

### Slice 8 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 8 only.
Implement correction persistence on the backend.
Add:
- correction model
- save correction endpoint
- fetch corrections endpoint
- review status handling
- original versus corrected state handling
Do not implement box drawing or editing UI yet.
Verify that one detection can be corrected and the correction survives reload while the original detection remains recoverable.
```

### Slice 9 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 9 only.
Add frontend annotation editing for existing detections.
Implement:
- select detection
- move or redraw box
- resize box
- label change
- bounds validation
Clip boxes to image bounds and preserve x_min, y_min, x_max, y_max semantics.
Do not add polygon tools or batch editing.
Verify that a user can visually edit one box and save it successfully.
```

### Slice 10 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 10 only.
Read docs/specification/15-scene-geometry-contract.md first.
Use data/raw/models/dpt_swin2_tiny_256.pt.
Implement:
- depth inference step
- depth artifact persistence
- width/height validation
- missing-depth fallback
Do not implement point-cloud conversion or 3D rendering yet.
Verify that one frame gets a valid stored depth artifact matching the source image dimensions.
```

### Slice 11 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 11 only.
Read docs/specification/15-scene-geometry-contract.md first.
Implement point-cloud conversion from stored depth:
- pixel-to-3D conversion
- local coordinate convention
- point subsampling
- point-cloud artifact storage or streaming
Do not implement advanced rendering polish or multi-frame registration.
Verify that one frame returns a stable point-cloud payload in the agreed coordinate system.
```

### Slice 12 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 12 only.
Build the Three.js viewer for an existing point-cloud artifact.
Implement:
- Three.js scene
- point rendering
- basic camera controls
- loading state
- empty or failed 3D state
Do not implement global scene merge or advanced shader work.
Verify that a selected frame can be inspected interactively in 3D.
```

### Slice 13 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 13 only.
Add minimal monitoring metrics based on real stored data.
Implement:
- detection count
- average confidence
- correction count
- correction rate
Add only the APIs and UI needed for these summary metrics.
Do not implement advanced time-series dashboards or model comparison.
Verify that metrics change after runs and after corrections.
```

### Slice 14 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 14 only.
Add corrected-output export.
Implement:
- export endpoint
- one documented export format, preferably JSON
- one frontend export trigger
Do not add multiple formats or async export jobs unless strictly necessary.
Verify that corrected detections can be downloaded and that the export matches stored corrections.
```

### Slice 15 Prompt

```text
Follow docs/specification/18-codex-implementation-slices.md and implement Slice 15 only.
Harden the demo and documentation.
Implement:
- failure-state UI
- setup instructions
- screenshots or demo script
- AI-assisted development note
- minimal Kubernetes sketch
Explicitly handle:
- bad dataset metadata
- no detections
- failed detection run
- missing depth artifact
- missing point cloud
Do not expand core architecture at this stage.
Verify that the demo can be run from the docs alone and explained clearly.
```
