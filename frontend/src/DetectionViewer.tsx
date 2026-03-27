import type { JSX } from "react";

import type {
  DetectionRecord,
  FrameDetailRecord,
  InferenceRunRecord,
} from "./types";
import {
  buildDetectionBoxLayout,
  buildPreviewUrl,
  buildViewerMessage,
  describeRunStatus,
  formatCoordinate,
  formatHeading,
  formatTimestamp,
} from "./viewer";

type DetectionViewerProps = {
  datasetName: string | null;
  frame: FrameDetailRecord | null;
  run: InferenceRunRecord | null;
  detections: DetectionRecord[];
  loading: boolean;
  error: string | null;
};

function RunSummary({
  run,
  frameDetectionCount,
}: {
  run: InferenceRunRecord;
  frameDetectionCount: number;
}): JSX.Element {
  const runStatus = describeRunStatus(run);

  return (
    <section className="run-summary" aria-label="Detection run status">
      <div className="run-summary__header">
        <div>
          <p className="eyebrow">Slice 7</p>
          <h3>Stored detection run</h3>
        </div>
        <span className={`status-pill status-pill--${runStatus.tone}`}>
          {runStatus.label}
        </span>
      </div>

      <dl className="run-summary__grid">
        <div>
          <dt>Model</dt>
          <dd>{run.model_name}</dd>
        </div>
        <div>
          <dt>Frame detections</dt>
          <dd>{frameDetectionCount}</dd>
        </div>
        <div>
          <dt>Dataset detections</dt>
          <dd>{run.detection_count}</dd>
        </div>
        <div>
          <dt>Processed frames</dt>
          <dd>
            {run.processed_frame_count} / {run.frame_count}
          </dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>{formatTimestamp(run.started_at)}</dd>
        </div>
        <div>
          <dt>Completed</dt>
          <dd>{run.completed_at ? formatTimestamp(run.completed_at) : "In progress"}</dd>
        </div>
      </dl>

      {run.error_message ? (
        <p className="run-summary__error">{run.error_message}</p>
      ) : null}
    </section>
  );
}

export function DetectionViewer({
  datasetName,
  frame,
  run,
  detections,
  loading,
  error,
}: DetectionViewerProps): JSX.Element {
  const viewerMessage = buildViewerMessage(run, detections, loading, error);

  if (frame === null) {
    return (
      <section className="workspace-panel preview-panel">
        <div className="section-header section-header--row">
          <div>
            <h2>Frame inspection</h2>
            <p className="panel-copy">
              Open a stored frame, inspect read-only bounding boxes, and verify
              the latest persisted detection run without entering edit mode.
            </p>
          </div>
          {datasetName ? <span className="stat-pill">{datasetName}</span> : null}
        </div>

        {loading || error ? (
          <p
            className={`status-message${error ? " status-message--error" : ""}`}
            role={error ? "alert" : "status"}
          >
            {error ?? "Loading selected frame and stored overlays..."}
          </p>
        ) : (
          <p className="status-message">
            No frame selected yet. Choose a marker from the map to open the image
            viewer.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="workspace-panel preview-panel">
      <div className="section-header section-header--row">
        <div>
          <h2>Frame inspection</h2>
          <p className="panel-copy">
            Open a stored frame, inspect read-only bounding boxes, and verify
            the latest persisted detection run without entering edit mode.
          </p>
        </div>
        {datasetName ? <span className="stat-pill">{datasetName}</span> : null}
      </div>

      <div className="preview-card">
        {run ? <RunSummary run={run} frameDetectionCount={detections.length} /> : null}

        <figure className="image-viewer">
          <div
            className="image-stage"
            style={{ aspectRatio: `${frame.image_width} / ${frame.image_height}` }}
          >
            <img
              className="preview-image"
              src={buildPreviewUrl(frame.preview_url)}
              alt={`Selected frame ${frame.frame_id}`}
            />

            <div
              className="overlay-layer"
              role="presentation"
              aria-hidden={detections.length === 0}
            >
              {detections.map((detection) => {
                const layout = buildDetectionBoxLayout(detection, frame);

                return (
                  <div
                    key={detection.id}
                    className="detection-box"
                    style={layout.style}
                    aria-label={layout.label}
                  >
                    <span className="detection-box__label">{layout.label}</span>
                  </div>
                );
              })}
            </div>

            {viewerMessage ? (
              <div
                className={`viewer-message viewer-message--${viewerMessage.tone}`}
                role={viewerMessage.tone === "error" ? "alert" : "status"}
              >
                <h3>{viewerMessage.title}</h3>
                <p>{viewerMessage.description}</p>
              </div>
            ) : null}
          </div>
          <figcaption className="image-viewer__caption">
            Bounding boxes are rendered from stored pixel coordinates and scaled
            to the displayed image without editing controls.
          </figcaption>
        </figure>

        <dl className="frame-metadata">
          <div>
            <dt>Frame</dt>
            <dd>{frame.frame_id}</dd>
          </div>
          <div>
            <dt>Captured</dt>
            <dd>{formatTimestamp(frame.timestamp)}</dd>
          </div>
          <div>
            <dt>Heading</dt>
            <dd>{formatHeading(frame.heading_degrees)}</dd>
          </div>
          <div>
            <dt>Coordinates</dt>
            <dd>
              {formatCoordinate(frame.latitude)}, {formatCoordinate(frame.longitude)}
            </dd>
          </div>
          <div>
            <dt>Dimensions</dt>
            <dd>
              {frame.image_width} x {frame.image_height}
            </dd>
          </div>
          <div>
            <dt>Image path</dt>
            <dd>{frame.image_path}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
