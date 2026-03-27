import { useEffect, useState, type JSX } from "react";

import { PointCloudCanvas } from "./PointCloudCanvas";
import type { FrameDetailRecord, FramePointCloudResponse } from "./types";
import {
  buildPointCloudPath,
  buildPointCloudSummary,
  buildPointCloudViewerMessage,
  describeRunStatus,
  fetchJson,
  formatTimestamp,
} from "./viewer";

type PointCloudViewerProps = {
  datasetId: number | null;
  frame: FrameDetailRecord;
};

function PointCloudMetadata({
  response,
}: {
  response: FramePointCloudResponse;
}): JSX.Element | null {
  const artifact = response.artifact;
  const summary = buildPointCloudSummary(response);

  if (artifact === null || summary === null) {
    return null;
  }

  const runStatus = response.run ? describeRunStatus(response.run) : null;

  return (
    <dl className="point-cloud-metadata">
      <div>
        <dt>Rendered points</dt>
        <dd>{summary.renderedPointCount.toLocaleString()}</dd>
      </div>
      <div>
        <dt>Source points</dt>
        <dd>{summary.sourcePointCount.toLocaleString()}</dd>
      </div>
      <div>
        <dt>Subsample step</dt>
        <dd>{summary.subsampleStep}</dd>
      </div>
      <div>
        <dt>Coordinate system</dt>
        <dd>{artifact.coordinate_system}</dd>
      </div>
      <div>
        <dt>Intrinsics source</dt>
        <dd>{artifact.intrinsics_source}</dd>
      </div>
      <div>
        <dt>Run status</dt>
        <dd>{runStatus ? runStatus.label : response.state}</dd>
      </div>
      <div>
        <dt>Artifact created</dt>
        <dd>{formatTimestamp(artifact.created_at)}</dd>
      </div>
    </dl>
  );
}

export function PointCloudViewer({
  datasetId,
  frame,
}: PointCloudViewerProps): JSX.Element {
  const [response, setResponse] = useState<FramePointCloudResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    if (datasetId === null) {
      setResponse(null);
      setIsLoading(false);
      setError("Select a dataset before requesting a 3D point-cloud view.");
      setRenderError(null);
      return;
    }

    let isMounted = true;
    const resolvedDatasetId = datasetId;

    async function loadPointCloud() {
      setIsLoading(true);
      setError(null);
      setRenderError(null);

      try {
        const payload = await fetchJson<FramePointCloudResponse>(
          buildPointCloudPath(resolvedDatasetId, frame.frame_id),
        );

        if (!isMounted) {
          return;
        }

        setResponse(payload);
      } catch {
        if (!isMounted) {
          return;
        }

        setResponse(null);
        setError("Unable to load the stored point-cloud artifact for this frame.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadPointCloud();

    return () => {
      isMounted = false;
    };
  }, [datasetId, frame.frame_id]);

  const viewerMessage = buildPointCloudViewerMessage(
    response,
    isLoading,
    error,
    renderError,
  );
  const canRenderScene =
    viewerMessage === null && (response?.payload?.points.length ?? 0) > 0;

  return (
    <section className="point-cloud-viewer" aria-label="3D point-cloud viewer">
      <div className="point-cloud-viewer__header">
        <div>
          <p className="eyebrow">Slice 12</p>
          <h3>3D point cloud</h3>
        </div>
        {response?.artifact ? (
          <span className="stat-pill">
            {response.artifact.point_count.toLocaleString()} points
          </span>
        ) : null}
      </div>

      <div className="point-cloud-surface">
        {canRenderScene ? (
          <PointCloudCanvas
            points={response?.payload?.points ?? []}
            ariaLabel={`3D point-cloud view for frame ${frame.frame_id}`}
            onError={setRenderError}
          />
        ) : null}

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

      <p className="point-cloud-viewer__hint">
        Drag to orbit, use the mouse wheel to zoom, and right-drag to pan around
        the selected frame&apos;s local camera-space point cloud.
      </p>

      {response ? <PointCloudMetadata response={response} /> : null}
    </section>
  );
}
