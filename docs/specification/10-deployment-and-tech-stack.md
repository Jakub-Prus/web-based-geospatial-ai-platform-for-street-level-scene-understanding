# 10. Deployment And Tech Stack

Status: Updated after Slice 10

## Technology Stack

- Frontend: React, TypeScript, Vite
- State management: React Query plus local component state
- Mapping: Mapbox GL JS or Leaflet
- 3D visualization: Three.js
- Bridge service: C# with .NET 8 Web API
- Core backend: Python with FastAPI
- Depth inference: MiDaS `DPT_SwinV2_T_256` with pinned `dpt_swin2_tiny_256.pt`
- Database: PostgreSQL with PostGIS
- Storage: S3-compatible object storage

## Deployment

- Containerization: Docker for all services
- Local development: Docker Compose
- Cloud target: AWS or Azure
- Minimal Kubernetes deployment sketch after MVP, even if full rollout is not implemented
- The FastAPI image now pre-caches the official MiDaS repository code so the local depth backend does not need to fetch model code on first request inside Docker

## CI/CD

- GitHub Actions for linting, tests, build validation, and container image creation
- Automated frontend, .NET, and Python checks on pull requests
- Environment-based deployment pipelines for staging and production

## AI-Assisted Development

- Use AI coding assistants for scaffolding, test generation, API contract drafting, and refactor support
- Use prompt-driven debugging to accelerate iteration on geospatial parsing, inference integration, and annotation edge cases
- Document where AI assistance helped accelerate delivery without changing technical ownership of the code

## Cloud-Native Signaling

- Include one Kubernetes deployment sketch or sample manifest for the frontend or backend services
- Show environment-driven configuration, container boundaries, and service separation even if the demo runs only on Docker Compose

## Why This Stack Matches The Job

- FastAPI covers ML service integration, data orchestration, and rapid demo delivery.
- .NET 8 covers the enterprise-side integration signal the role explicitly asks for.
- React and TypeScript demonstrate modern frontend capability for complex visual workflows.
- PostGIS, map rendering, and Three.js keep the project centered on geospatial and 3D visualization strengths.
- Docker shows practical platform engineering discipline.
- A minimal Kubernetes artifact helps demonstrate cloud-native awareness without inflating the MVP.
