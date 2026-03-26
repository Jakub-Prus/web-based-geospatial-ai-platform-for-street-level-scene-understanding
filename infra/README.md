# Infrastructure Assets

Slice 2 introduces the local runtime assets for the empty stack:

- root `docker-compose.yml` for one-command startup
- service-level Dockerfiles under `frontend/`, `services/ml-fastapi/`, and `services/bridge-dotnet/`
- root `.env.example` documenting compose overrides

Later slices can expand this folder with deployment manifests and environment-specific infrastructure files without changing the basic local stack contract.
