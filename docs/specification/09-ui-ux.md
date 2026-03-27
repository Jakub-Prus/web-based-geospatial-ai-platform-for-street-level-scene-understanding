# 09. UI And UX

Status: Updated after Slice 7

## Current Screens

- dataset selection and spatial browsing workspace
- read-only street-image review workspace with detection overlays
- planned 3D point-cloud viewer
- planned monitoring dashboard
- planned export panel

## Current Review Workspace

The implemented workspace is currently a two-panel review layout:

- left panel: map with stored camera positions and frame selection
- right panel: street-level image viewer with persisted bounding boxes and run metadata

The future correction sidebar is still deferred until the annotation slices.

## Primary User Flow

1. User uploads or selects a prepared dataset.
2. User starts AI processing.
3. User waits for job completion and opens the review workspace.
4. User selects a camera point on the map.
5. User inspects read-only detections, labels, confidence values, and run status.
6. Future slice: user edits incorrect predictions.
7. Future slice: user opens the 3D view for the same frame.
8. Future slice: user saves corrections and views updated metrics.

## Visualization Requirements

- The map must support camera markers and spatial navigation.
- The image viewer must render stored detections from image pixel coordinates.
- The current UI must expose run state clearly for completed, empty, failed, and missing-run cases.
- Future slice: the image viewer should support zoom and pan.
- Future slice: the annotation UI should allow drawing, resizing, relabeling, and deleting boxes.
- The 3D view must render depth-derived point data in Three.js.

## Current Empty States

The Slice 7 viewer should remain understandable in each of these states:

- no frame selected
- no detection run stored yet
- detection run is still running
- latest detection run failed
- latest run exists but the selected frame has no stored detections

## UX Quality Bar

- Minimize context switching between map, image, and review actions.
- Make model output, human edits, and approval state visually distinct.
- Prioritize responsiveness and clarity over UI complexity.
