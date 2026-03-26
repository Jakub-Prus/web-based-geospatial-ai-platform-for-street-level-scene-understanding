# 15. Scene Geometry Contract

Status: Proposed v1

## Purpose

This document defines how 2D image data, depth output, and point-cloud-style 3D visualization relate to each other in the MVP.

## Geometry Goal

The goal is a visually coherent pseudo-LiDAR scene view for demo purposes, not survey-grade reconstruction.

## Core Assumptions

- Depth is produced per image frame.
- Point-cloud coordinates are generated from a single frame at a time.
- The 3D view is local to the selected frame, not a globally registered city-scale point cloud.
- WGS84 map coordinates and local 3D point-cloud coordinates are linked by frame identity, not merged into one global coordinate space.

## Required Frame Geometry Inputs

Each frame should provide:

- `image_width`
- `image_height`
- `heading_degrees`
- Optional `camera_intrinsics_json`
- Optional `pitch_degrees`
- Optional `roll_degrees`

## Fallback Camera Model

If camera intrinsics are unavailable, use a fixed approximate pinhole camera model for the demo dataset and document the chosen values.

Example fallback values:

- `fx = fy = image_width`
- `cx = image_width / 2`
- `cy = image_height / 2`

These values are only for a stable demo, not for accurate measurement.

## Depth Artifact Contract

Each depth artifact must contain:

- `frame_id`
- `depth_uri`
- `width`
- `height`
- `depth_format`
- `depth_scale`

Recommended formats:

- single-channel float depth map
- normalized depth image with documented scale conversion

## Point-Cloud Conversion Contract

For each valid depth pixel:

1. Convert pixel coordinates into camera-local coordinates.
2. Apply depth scale.
3. Optionally subsample points for rendering performance.
4. Store or stream the resulting local XYZ points.

Recommended point fields:

- `x`
- `y`
- `z`
- optional `r`
- optional `g`
- optional `b`

## Coordinate System Convention

- Use a right-handed local camera coordinate system.
- Document which axis points forward, right, and up.
- Keep the same convention in backend generation and Three.js rendering.

Recommended convention:

- `+X` right
- `+Y` down or up, but fixed and documented
- `+Z` forward

If `+Y` is inverted between backend and Three.js, normalize it in one place only.

## Alignment Rules

- 2D detections remain in image pixel space.
- 3D point clouds are generated from the same selected frame.
- The UI does not need to project corrected 2D boxes into 3D for MVP.
- The map links to the frame; the frame links to both 2D and 3D views.

## Validation Rules

- Depth width and height must match the source image dimensions.
- Invalid or negative depth values must be filtered out.
- Point count should be capped or subsampled for browser performance.
- Missing depth artifacts should show a clear UI fallback instead of a broken 3D view.

## Implementation Guidance

- Start with one frame-to-point-cloud pipeline that works reliably.
- Only add sequence-level or global alignment after the single-frame 3D view is stable.
- Treat visual clarity and interaction smoothness as more important than geometric precision for MVP.
