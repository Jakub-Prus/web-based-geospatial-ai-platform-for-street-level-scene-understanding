# 19. External Assets Inventory

Status: Proposed v1

## Purpose

This document freezes the external data, model weights, and online references needed by the project before implementation begins.

## Rule

If the project depends on an external asset, its source and intended local location must appear here first.

## Pinned Demo Dataset

### Chosen Source

- Dataset: A2D2: Audi Autonomous Driving Dataset
- Why: street-level driving imagery, LiDAR, calibration data, 360-degree capture context, and commercial-friendly licensing

### Official Links

- Registry page: `https://registry.opendata.aws/aev-a2d2/`
- Documentation: `http://a2d2.audi`
- Preview archive: `https://aev-autonomous-driving-dataset.s3.eu-central-1.amazonaws.com/a2d2-preview.tar`
- License: `https://creativecommons.org/licenses/by-nd/4.0/`

### Notes

- The preview archive is approximately `4,633,241,600` bytes.
- For MVP, use a small extracted subset from the preview archive rather than the full dataset.
- If available, prefer perspective frames derived from panoramic or 360-degree capture.
- The archive is already downloaded locally at `data/raw/a2d2-preview.tar`.
- Observed top-level archive structure starts with `camera_lidar/<sequence>/camera/<camera_name>/...`.

### Vendored Small Files In Repo

- `external-assets/a2d2/README.txt`
- `external-assets/a2d2/cams_lidars.json`
- `external-assets/a2d2/LICENSE.txt`

## Detection Model

### Chosen Source

- Provider: Ultralytics
- Model: `yolo11n.pt`
- Why: lightweight baseline for a fast MVP detection pipeline

### Official Links

- Model family docs: `https://docs.ultralytics.com/models/yolo11/`
- Detection task docs: `https://docs.ultralytics.com/tasks/detect/`
- Release asset used for local download: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt`

### Local Path

- `data/raw/models/yolo11n.pt`

## Depth Model

### Chosen Source

- Provider: MiDaS
- Model: `dpt_swin2_tiny_256.pt`
- Why: lightweight enough for MVP while still supporting convincing pseudo-LiDAR visualization

### Official Links

- Repository: `https://github.com/isl-org/MiDaS`
- Releases: `https://github.com/isl-org/MiDaS/releases`
- Direct weight URL: `https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_swin2_tiny_256.pt`
- Optional higher-quality model: `https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_beit_large_512.pt`

### Local Path

- `data/raw/models/dpt_swin2_tiny_256.pt`

## Map Runtime

### Chosen Source

- Frontend map library: Leaflet
- Dev tile source: OpenStreetMap standard tiles

### Official Links

- Leaflet reference: `https://leafletjs.com/reference.html`
- OSM tile policy: `https://operations.osmfoundation.org/policies/tiles/`

### Notes

- OSM tiles are acceptable for development and demo usage only if the tile policy is respected.
- If later needed, replace the tile source without changing the frame or detection contracts.

## Runtime And Infrastructure References

### Python

- PyTorch wheel index reference: `https://download.pytorch.org/whl/cu121`

### Deployment

- Docker Compose is the default local runtime.
- A minimal Kubernetes sketch is documented in `17-cloud-deployment-sketch.md`.

## What Is Already Downloaded Locally

- `data/raw/a2d2-preview.tar`
- `data/raw/models/yolo11n.pt`
- `data/raw/models/dpt_swin2_tiny_256.pt`

## Reproducible Download Command

Run:

```powershell
./scripts/download_external_assets.ps1
```

To also fetch the large A2D2 preview archive:

```powershell
./scripts/download_external_assets.ps1 -DownloadA2D2Preview
```

## Recommended Local Subset Extraction

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/extract_a2d2_subset.ps1
```

This extracts a small default subset from sequence `20190401_121727` and camera `cam_front_right` into `data/raw/a2d2-subset/`.
