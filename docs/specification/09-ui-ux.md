# 09. UI And UX

Status: Proposed v1

## Core Screens

- Dataset upload and processing screen
- Map plus street-image review workspace
- 3D point-cloud viewer
- Monitoring dashboard
- Export panel

## Primary UX Concept

The most important screen is a split review workspace:

- Left panel: map with camera positions and dataset navigation
- Center panel: street-level image viewer
- Overlay layer: detections, labels, and annotation tools
- Right panel: selected object details, correction controls, and audit history

## Primary User Flow

1. User uploads or selects a prepared dataset.
2. User starts AI processing.
3. User waits for job completion and opens the review workspace.
4. User selects a camera point on the map.
5. User inspects detections and edits incorrect predictions.
6. User opens the 3D view for the same frame.
7. User saves corrections and views updated metrics.

## Visualization Requirements

- The map must support camera markers and spatial navigation.
- The image viewer must support zoom, pan, and box overlays.
- The annotation UI must allow drawing, resizing, relabeling, and deleting boxes.
- The 3D view must render depth-derived point data in Three.js.

## UX Quality Bar

- Minimize context switching between map, image, and review actions.
- Make model output, human edits, and approval state visually distinct.
- Prioritize responsiveness and clarity over UI complexity.
