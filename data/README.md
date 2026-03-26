# Data Staging

Large downloaded assets are staged under `data/raw/` and are intentionally excluded from git.

Current intended contents:

- `data/raw/models/yolo11n.pt`
- `data/raw/models/dpt_swin2_tiny_256.pt`
- `data/raw/a2d2-preview.tar`
- `data/raw/a2d2-subset/` for a small extracted local test subset

Use `scripts/download_external_assets.ps1` to fetch pinned external assets into this folder.
Use `scripts/extract_a2d2_subset.ps1` to extract a small camera subset for local development and testing.
