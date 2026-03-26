# 17. Cloud Deployment Sketch

Status: Proposed v1

## Purpose

This document provides minimal cloud-native signaling for the MVP without requiring a full production rollout.

## Local Runtime

- Frontend container
- .NET bridge container
- FastAPI container
- PostgreSQL plus PostGIS container
- Object storage container or compatible service

## Cloud-Native Target Shape

Recommended deployment shape:

- Frontend served as a web container or static deployment
- .NET bridge as a small API deployment
- FastAPI inference service as a separate API deployment
- Managed PostgreSQL with PostGIS support
- Managed object storage for imagery and derived outputs

## Kubernetes Signaling

Minimum artifact to include:

- one sample Deployment manifest
- one sample Service manifest
- environment-based configuration for containerized services

## Example Deployment Split

```text
[Ingress]
   |
   +--> [Frontend Service]
   +--> [.NET Bridge Service]
   +--> [FastAPI Service]

[FastAPI Service] <-> [PostgreSQL/PostGIS]
[FastAPI Service] <-> [Object Storage]
[.NET Bridge Service] <-> [FastAPI Service or shared metadata store]
```

## Why This Is Enough For MVP

- Demonstrates awareness of service separation and cloud deployment boundaries
- Supports Docker-first local development without forcing a full Kubernetes implementation
- Signals familiarity with the deployment model the target role expects
