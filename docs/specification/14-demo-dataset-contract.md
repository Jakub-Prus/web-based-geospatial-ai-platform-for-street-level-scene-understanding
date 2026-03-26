# 14. Demo Dataset Contract

Status: Proposed v1

## Purpose

This document freezes the demo dataset shape so the backend, frontend, correction workflow, metrics, and exports all target the same contract.

## Recommended Demo Scope

- 1 dataset
- 20 to 100 street-level frames
- 3 to 6 object classes
- One consistent city or route segment
- Prefer perspective frames derived from panoramic or 360-degree street capture if available

## Required Metadata Fields

Each frame record must contain:

- `frame_id`
- `image_path`
- `latitude`
- `longitude`
- `heading_degrees`
- `timestamp`
- `image_width`
- `image_height`

## Optional Metadata Fields

- `pitch_degrees`
- `roll_degrees`
- `camera_intrinsics_json`
- `sequence_id`
- `depth_path`

## Recommended File Layout

```text
dataset/
  frames/
    frame_0001.jpg
    frame_0002.jpg
  metadata/
    frames.csv
```

## CSV Contract

Required columns:

- `frame_id`
- `image_path`
- `latitude`
- `longitude`
- `heading_degrees`
- `timestamp`
- `image_width`
- `image_height`

Example row:

```csv
frame_id,image_path,latitude,longitude,heading_degrees,timestamp,image_width,image_height
frame_0001,frames/frame_0001.jpg,48.2082,16.3738,92.5,2026-03-20T10:15:00Z,1920,1080
```

## Label Taxonomy

Freeze one small class set for MVP. Recommended:

- `car`
- `traffic_sign`
- `building`
- `pole`
- `person`

Do not expand the taxonomy mid-build unless it is absolutely necessary.

## Bounding Box Contract

- Bounding boxes use image pixel coordinates.
- Format: `x_min`, `y_min`, `x_max`, `y_max`
- Origin is top-left of the image.
- Coordinates must be clipped to image bounds before saving.

## CRS And Spatial Assumptions

- Geographic coordinates are stored in WGS84 latitude and longitude.
- Map rendering may transform coordinates into the projection required by the chosen map library.
- Any local 3D coordinates used for point-cloud rendering are separate from stored WGS84 positions.

## Validation Rules

- Missing latitude or longitude rejects the frame.
- Missing image path rejects the frame.
- Missing width or height rejects the frame.
- Duplicate `frame_id` values reject the dataset.
- Nonexistent image files reject the dataset or mark the frame invalid with a clear error.

## Notes

- This contract is intentionally small so the MVP remains stable.
- If panoramic data is available, the MVP may use extracted perspective views rather than full panoramic rendering.
- If you later add temporal comparison, extend the dataset with `sequence_id` and capture grouping metadata.
