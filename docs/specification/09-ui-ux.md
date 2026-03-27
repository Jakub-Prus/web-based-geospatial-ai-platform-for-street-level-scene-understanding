# 09. UI And UX

Status: Updated after Slice 9

## Current Screens

- dataset selection and spatial browsing workspace
- street-image review workspace with single-detection editing
- planned 3D point-cloud viewer
- planned monitoring dashboard
- planned export panel

## Current Review Workspace

The implemented workspace is currently a two-panel review layout:

- left panel: map with stored camera positions and frame selection
- right panel: street-level image viewer with persisted bounding boxes, run metadata, and a focused annotation editor

The annotation editor is intentionally scoped to one existing detection at a time:

- select a detection from the overlay or editor list
- drag the selected box to move it
- resize it from the four corner handles
- switch to redraw mode and redraw the full box
- edit the label
- save the corrected state through the Slice 8 correction endpoint

## Primary User Flow

1. User uploads or selects a prepared dataset.
2. User starts AI processing.
3. User waits for job completion and opens the review workspace.
4. User selects a camera point on the map.
5. User inspects detections, labels, confidence values, and run status.
6. User selects one incorrect detection and edits the label or box directly in the image viewer.
7. User saves the corrected state and sees the effective detection update without losing the original model output.
8. Future slice: user opens the 3D view for the same frame.
9. Future slice: user views updated metrics.

## Visualization Requirements

- The map must support camera markers and spatial navigation.
- The image viewer must render stored detections from image pixel coordinates.
- The current UI must expose run state clearly for completed, empty, failed, and missing-run cases.
- The current UI must allow move, resize, redraw, relabel, and save for one selected detection.
- The current UI must clip edited coordinates to the image bounds and reject collapsed boxes with understandable errors.
- Future slice: the image viewer should support zoom and pan.
- Future slice: the annotation UI should allow deletion and approval-state controls.
- Future slice: the review UI should expose `pending`, `approved`, and `rejected` states backed by the Slice 8 correction endpoints.
- The 3D view must render depth-derived point data in Three.js.

## Current Empty States

The Slice 9 viewer should remain understandable in each of these states:

- no frame selected
- no detection run stored yet
- detection run is still running
- latest detection run failed
- latest run exists but the selected frame has no stored detections
- edited box clips to an image edge
- user attempts to save a collapsed or otherwise invalid box

## UX Quality Bar

- Minimize context switching between map, image, and review actions.
- Make model output, human edits, and approval state visually distinct.
- Prioritize responsiveness and clarity over UI complexity.
