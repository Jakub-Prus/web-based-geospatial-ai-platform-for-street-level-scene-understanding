# 05. Non-Functional Requirements

Status: Proposed v1

## Performance

- Interactive API responses should return within 2 seconds for standard project, map, and review operations.
- Initial map and viewer interactions should feel responsive for datasets up to the defined demo scale.
- Batch inference must run asynchronously so long-running ML jobs do not block the UI.

## Security

- All inter-service and client-server traffic must use HTTPS in deployed environments.
- The MVP may run in local demo mode without authentication.
- Any future authenticated deployment should isolate dataset access behind a simple auth layer.

## Scalability

- The platform should support horizontal scaling of the Python inference service.
- The ingestion and processing pipeline should handle larger datasets through queued background jobs.
- Spatial queries should use indexing suitable for geospatial lookup performance.

## Reliability

- Failed jobs must expose actionable status and error information.
- Inference retries must not duplicate stored outputs for the same job step.
- The system should preserve auditability for uploads, detections, and review actions.

## Usability

- The core analyst workflow should be understandable without specialist GIS tooling knowledge.
- Review actions should be reachable in one workspace without repeated context switching.
- System feedback for loading, processing, and save events must be explicit.

## Observability

- The platform should log ingestion, inference, correction, and export events.
- The platform should expose metrics for job duration, detection counts, and correction rates.
- The platform should expose enough structured logs to debug failed ingestion, failed inference, and invalid depth output.
