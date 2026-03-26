# 01. Overview

Status: Proposed v1

## App Name

- "Web-Based Geospatial AI Platform for Street-Level Scene Understanding"

## Purpose

This project is a portfolio-grade platform designed in direct response to the Cyclomedia Full Stack Developer: Geospatial & ML Systems role.

It demonstrates how a full stack engineer can bridge high-resolution street-level geospatial data, machine learning inference, and human review workflows inside one production-style system. The platform ingests geo-tagged street imagery, runs AI inference, visualizes detections on a map and in image space, and allows a human operator to correct model output so those corrections can be tracked and reused.

## Target Users

- GIS or mapping practitioner reviewing street-level observations
- Computer vision engineer validating inference quality and scene outputs
- Reviewer correcting detections and validating results
- Technical interviewer or recruiter evaluating full stack geospatial and ML systems capability

## Platform

- Web application for map, image, annotation, and dashboard workflows
- Thin .NET 8 bridge service for metadata or orchestration signaling
- Python FastAPI service for inference, dataset processing, and ML-facing data pipelines
- Shared geospatial data store and object storage for imagery, metadata, and generated outputs
- Local demo mode with no authentication required for MVP

## Why This Project Fits The Job

The role emphasizes being the technical glue between enterprise software and ML systems. This project is explicitly designed around that responsibility:

- Geospatial data handling with GPS coordinates, spatial indexing, and map/image alignment
- Lightweight .NET plus Python service interaction to reflect mixed-stack enterprise reality
- ML integration focused on inference APIs and data pipelines rather than model research
- Advanced React visualization for complex 2D overlays and 3D scene exploration
- Human-in-the-loop review and correction workflows for ML enablement

## Scope Positioning

This is not intended to be a generic map app or a pure ML notebook project. It is a systems engineering demonstration that shows end-to-end product thinking across ingestion, orchestration, inference, visualization, correction, monitoring, and deployment.
