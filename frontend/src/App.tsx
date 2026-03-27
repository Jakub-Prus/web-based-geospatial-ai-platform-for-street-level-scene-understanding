import { useEffect, useState } from "react";

import { DetectionViewer } from "./DetectionViewer";
import type {
  DetectionCorrectionRecord,
  DatasetListResponse,
  DatasetRecord,
  FrameDetectionsResponse,
  FrameCorrectionsResponse,
  FrameDetailRecord,
  FrameDetailResponse,
  FrameListResponse,
  FrameRecord,
  InferenceRunRecord,
  DetectionRecord,
} from "./types";
import {
  buildMarkerPositions,
  buildCorrectionsPath,
  fetchJson,
  type ApiError,
} from "./viewer";

type DatasetListProps = {
  datasets: DatasetRecord[];
  selectedDatasetId: number | null;
  onSelect: (datasetId: number) => void;
};

function DatasetList({
  datasets,
  selectedDatasetId,
  onSelect,
}: DatasetListProps): JSX.Element {
  return (
    <section className="dataset-panel">
      <div className="section-header">
        <p className="eyebrow">Slice 9</p>
        <h1>Detection editing workspace</h1>
        <p className="panel-copy">
          Choose a loaded dataset, inspect stored camera locations, and open a
          frame viewer where one persisted detection can be corrected at a time.
        </p>
      </div>

      <div className="dataset-list" role="list" aria-label="Loaded datasets">
        {datasets.map((dataset) => {
          const isSelected = dataset.id === selectedDatasetId;

          return (
            <button
              key={dataset.id}
              className={`dataset-card${isSelected ? " dataset-card--selected" : ""}`}
              type="button"
              onClick={() => onSelect(dataset.id)}
            >
              <span className="dataset-card__title">{dataset.name}</span>
              <span className="dataset-card__meta">
                {dataset.frame_count} frames - {dataset.camera_name}
              </span>
              <span className="dataset-card__meta">
                Sequence {dataset.sequence_id}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

type SpatialMapProps = {
  frames: FrameRecord[];
  selectedFrameId: string | null;
  onSelectFrame: (frameId: string) => void;
};

function SpatialMap({
  frames,
  selectedFrameId,
  onSelectFrame,
}: SpatialMapProps): JSX.Element {
  const markerPositions = buildMarkerPositions(frames);

  if (frames.length === 0) {
    return (
      <section className="workspace-panel map-panel">
        <div className="section-header">
          <h2>Map</h2>
          <p className="panel-copy">No stored frame coordinates are available yet.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="workspace-panel map-panel">
      <div className="section-header section-header--row">
        <div>
          <h2>Map</h2>
          <p className="panel-copy">
            Marker positions are projected from stored latitude and longitude.
          </p>
        </div>
        <span className="stat-pill">{frames.length} markers</span>
      </div>

      <div className="map-surface" role="group" aria-label="Frame map">
        <div className="map-grid" aria-hidden="true" />
        {markerPositions.map(({ frame, left, top }) => {
          const isSelected = frame.frame_id === selectedFrameId;

          return (
            <button
              key={frame.frame_id}
              className={`map-marker${isSelected ? " map-marker--selected" : ""}`}
              type="button"
              style={{ left: `${left}%`, top: `${top}%` }}
              onClick={() => onSelectFrame(frame.frame_id)}
              aria-pressed={isSelected}
              aria-label={`Open frame ${frame.frame_id}`}
              title={frame.frame_id}
            >
              <span className="map-marker__dot" />
            </button>
          );
        })}
      </div>
    </section>
  );
}

type FramePreviewProps = {
  datasetId: number | null;
  datasetName: string | null;
  selectedFrame: FrameDetailRecord | null;
  run: InferenceRunRecord | null;
  detections: DetectionRecord[];
  corrections: DetectionCorrectionRecord[];
  loading: boolean;
  error: string | null;
  onCorrectionSaved: (correction: DetectionCorrectionRecord) => void;
};

function FramePreview({
  datasetId,
  datasetName,
  selectedFrame,
  run,
  detections,
  corrections,
  loading,
  error,
  onCorrectionSaved,
}: FramePreviewProps): JSX.Element {
  return (
    <DetectionViewer
      datasetId={datasetId}
      datasetName={datasetName}
      frame={selectedFrame}
      run={run}
      detections={detections}
      corrections={corrections}
      loading={loading}
      error={error}
      onCorrectionSaved={onCorrectionSaved}
    />
  );
}

export default function App(): JSX.Element {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<DatasetRecord | null>(null);
  const [frames, setFrames] = useState<FrameRecord[]>([]);
  const [framesLoading, setFramesLoading] = useState(false);
  const [framesError, setFramesError] = useState<string | null>(null);
  const [selectedFrameId, setSelectedFrameId] = useState<string | null>(null);
  const [selectedFrame, setSelectedFrame] = useState<FrameDetailRecord | null>(null);
  const [frameLoading, setFrameLoading] = useState(false);
  const [frameError, setFrameError] = useState<string | null>(null);
  const [detections, setDetections] = useState<DetectionRecord[]>([]);
  const [detectionRun, setDetectionRun] = useState<InferenceRunRecord | null>(null);
  const [detectionsLoading, setDetectionsLoading] = useState(false);
  const [detectionsError, setDetectionsError] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<DetectionCorrectionRecord[]>([]);
  const [correctionsLoading, setCorrectionsLoading] = useState(false);
  const [correctionsError, setCorrectionsError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDatasets() {
      try {
        const payload = await fetchJson<DatasetListResponse>("/datasets");

        if (!isMounted) {
          return;
        }

        setDatasets(payload.datasets);
        setDatasetError(null);

        if (payload.datasets.length > 0) {
          setSelectedDatasetId((currentSelectedDatasetId) => {
            if (
              currentSelectedDatasetId !== null &&
              payload.datasets.some((dataset) => dataset.id === currentSelectedDatasetId)
            ) {
              return currentSelectedDatasetId;
            }

            return payload.datasets[0].id;
          });
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setDatasetError("Unable to load datasets from FastAPI.");
      }
    }

    void loadDatasets();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (selectedDatasetId === null) {
      setSelectedDataset(null);
      setFrames([]);
      setSelectedFrameId(null);
      setSelectedFrame(null);
      setDetectionRun(null);
      setDetections([]);
      setDetectionsError(null);
      setCorrections([]);
      setCorrectionsLoading(false);
      setCorrectionsError(null);
      return;
    }

    let isMounted = true;

    async function loadFrames() {
      setFramesLoading(true);
      setFramesError(null);
      setSelectedFrameId(null);
      setSelectedFrame(null);
      setFrameError(null);
      setDetectionRun(null);
      setDetections([]);
      setDetectionsError(null);
      setCorrections([]);
      setCorrectionsError(null);

      try {
        const payload = await fetchJson<FrameListResponse>(
          `/datasets/${selectedDatasetId}/frames`,
        );

        if (!isMounted) {
          return;
        }

        setSelectedDataset(payload.dataset);
        setFrames(payload.frames);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSelectedDataset(null);
        setFrames([]);
        setFramesError("Unable to load frame coordinates for the selected dataset.");
      } finally {
        if (isMounted) {
          setFramesLoading(false);
        }
      }
    }

    void loadFrames();

    return () => {
      isMounted = false;
    };
  }, [selectedDatasetId]);

  useEffect(() => {
    if (selectedFrameId === null) {
      setSelectedFrame(null);
      setFrameLoading(false);
      setFrameError(null);
      setDetections([]);
      setDetectionRun(null);
      setDetectionsLoading(false);
      setDetectionsError(null);
      setCorrections([]);
      setCorrectionsLoading(false);
      setCorrectionsError(null);
      return;
    }

    let isMounted = true;

    async function loadFrameDetail() {
      if (selectedDatasetId === null) {
        setFrameLoading(false);
        return;
      }

      setFrameLoading(true);
      setFrameError(null);

      try {
        const payload = await fetchJson<FrameDetailResponse>(
          `/datasets/${selectedDatasetId}/frames/${selectedFrameId}`,
        );

        if (!isMounted) {
          return;
        }

        setSelectedFrame(payload.frame);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setSelectedFrame(null);
        setFrameError("Unable to load the selected frame preview.");
      } finally {
        if (isMounted) {
          setFrameLoading(false);
        }
      }
    }

    void loadFrameDetail();

    return () => {
      isMounted = false;
    };
  }, [selectedDatasetId, selectedFrameId]);

  useEffect(() => {
    if (selectedDatasetId === null || selectedFrameId === null) {
      setDetections([]);
      setDetectionRun(null);
      setDetectionsLoading(false);
      setDetectionsError(null);
      return;
    }

    let isMounted = true;

    async function loadDetections() {
      setDetectionsLoading(true);
      setDetectionsError(null);

      try {
        const payload = await fetchJson<FrameDetectionsResponse>(
          `/datasets/${selectedDatasetId}/frames/${selectedFrameId}/detections`,
        );

        if (!isMounted) {
          return;
        }

        setDetectionRun(payload.run);
        setDetections(payload.detections);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        const apiError = error as Partial<ApiError>;
        setDetections([]);

        if (apiError.status === 404) {
          setDetectionRun(null);
          setDetectionsError(null);
          return;
        }

        setDetectionRun(null);
        setDetectionsError(
          "Unable to load stored detections or run metadata for the selected frame.",
        );
      } finally {
        if (isMounted) {
          setDetectionsLoading(false);
        }
      }
    }

    void loadDetections();

    return () => {
      isMounted = false;
    };
  }, [selectedDatasetId, selectedFrameId]);

  useEffect(() => {
    if (selectedDatasetId === null || selectedFrameId === null) {
      setCorrections([]);
      setCorrectionsLoading(false);
      setCorrectionsError(null);
      return;
    }

    let isMounted = true;
    const datasetId = selectedDatasetId;
    const frameId = selectedFrameId;

    async function loadCorrections() {
      setCorrectionsLoading(true);
      setCorrectionsError(null);

      try {
        const payload = await fetchJson<FrameCorrectionsResponse>(
          buildCorrectionsPath(datasetId, frameId),
        );

        if (!isMounted) {
          return;
        }

        setCorrections(payload.corrections);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        const apiError = error as Partial<ApiError>;
        setCorrections([]);

        if (apiError.status === 404) {
          setCorrectionsError(null);
          return;
        }

        setCorrectionsError(
          "Unable to load saved correction state for the selected frame.",
        );
      } finally {
        if (isMounted) {
          setCorrectionsLoading(false);
        }
      }
    }

    void loadCorrections();

    return () => {
      isMounted = false;
    };
  }, [selectedDatasetId, selectedFrameId]);

  function handleCorrectionSaved(correction: DetectionCorrectionRecord) {
    setCorrections((currentCorrections) => {
      const remainingCorrections = currentCorrections.filter(
        (currentCorrection) => currentCorrection.detection_id !== correction.detection_id,
      );

      return [...remainingCorrections, correction];
    });
  }

  return (
    <main className="app-shell">
      <DatasetList
        datasets={datasets}
        selectedDatasetId={selectedDatasetId}
        onSelect={setSelectedDatasetId}
      />

      {datasetError ? <p className="status-message status-message--error">{datasetError}</p> : null}
      {datasets.length === 0 && !datasetError ? (
        <p className="status-message">
          No datasets are loaded yet. Run the Slice 3 loader endpoint first.
        </p>
      ) : null}

      <section className="workspace-grid">
        <SpatialMap
          frames={frames}
          selectedFrameId={selectedFrameId}
          onSelectFrame={setSelectedFrameId}
        />
        <FramePreview
          datasetId={selectedDatasetId}
          datasetName={selectedDataset?.name ?? null}
          selectedFrame={selectedFrame}
          run={detectionRun}
          detections={detections}
          corrections={corrections}
          loading={frameLoading || detectionsLoading || correctionsLoading}
          error={frameError ?? detectionsError ?? correctionsError}
          onCorrectionSaved={handleCorrectionSaved}
        />
      </section>

      {framesLoading ? <p className="status-message">Loading frame locations...</p> : null}
      {framesError ? <p className="status-message status-message--error">{framesError}</p> : null}
    </main>
  );
}
