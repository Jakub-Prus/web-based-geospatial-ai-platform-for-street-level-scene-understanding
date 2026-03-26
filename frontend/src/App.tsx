import { useEffect, useState } from "react";

const DEFAULT_FASTAPI_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const MAP_PADDING_RATIO = 0.12;
const MIN_COORDINATE_SPAN = 0.0001;
const HEADING_PRECISION = 1;
const COORDINATE_PRECISION = 6;
const STACK_COLUMNS = 4;
const STACK_HORIZONTAL_SPACING_PERCENT = 2.6;
const STACK_VERTICAL_SPACING_PERCENT = 2.4;
const MAP_EDGE_PADDING_PERCENT = 2;

type DatasetRecord = {
  id: number;
  name: string;
  source_path: string;
  sequence_id: string;
  camera_name: string;
  frame_count: number;
  created_at: string;
};

type FrameRecord = {
  frame_id: string;
  dataset_id: number;
  image_path: string;
  latitude: number;
  longitude: number;
  heading_degrees: number;
  timestamp: string;
  image_width: number;
  image_height: number;
  pitch_degrees: number | null;
  roll_degrees: number | null;
  camera_intrinsics_json: string | null;
  sequence_id: string | null;
  depth_path: string | null;
};

type FrameDetailRecord = FrameRecord & {
  preview_url: string;
};

type DatasetListResponse = {
  datasets: DatasetRecord[];
};

type FrameListResponse = {
  dataset: DatasetRecord;
  frames: FrameRecord[];
};

type FrameDetailResponse = {
  frame: FrameDetailRecord;
};

type MarkerPosition = {
  frame: FrameRecord;
  left: number;
  top: number;
};

const apiBaseUrl = import.meta.env.VITE_FASTAPI_BASE_URL ?? DEFAULT_FASTAPI_URL;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);

  if (!response.ok) {
    throw new Error(`Request failed for ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

function buildPreviewUrl(previewPath: string): string {
  return new URL(previewPath, apiBaseUrl).toString();
}

function formatTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(timestamp));
}

function formatCoordinate(value: number): string {
  return value.toFixed(COORDINATE_PRECISION);
}

function buildMarkerPositions(frames: FrameRecord[]): MarkerPosition[] {
  if (frames.length === 0) {
    return [];
  }

  const latitudes = frames.map((frame) => frame.latitude);
  const longitudes = frames.map((frame) => frame.longitude);
  const minimumLatitude = Math.min(...latitudes);
  const maximumLatitude = Math.max(...latitudes);
  const minimumLongitude = Math.min(...longitudes);
  const maximumLongitude = Math.max(...longitudes);
  const latitudeSpan = Math.max(maximumLatitude - minimumLatitude, MIN_COORDINATE_SPAN);
  const longitudeSpan = Math.max(maximumLongitude - minimumLongitude, MIN_COORDINATE_SPAN);
  const paddedLatitudeSpan = latitudeSpan * (1 + MAP_PADDING_RATIO * 2);
  const paddedLongitudeSpan = longitudeSpan * (1 + MAP_PADDING_RATIO * 2);
  const latitudeOrigin = minimumLatitude - latitudeSpan * MAP_PADDING_RATIO;
  const longitudeOrigin = minimumLongitude - longitudeSpan * MAP_PADDING_RATIO;

  const duplicateCounts = new Map<string, number>();
  const duplicateGroupSizes = new Map<string, number>();

  frames.forEach((frame) => {
    const duplicateKey = `${frame.latitude}:${frame.longitude}`;
    duplicateGroupSizes.set(duplicateKey, (duplicateGroupSizes.get(duplicateKey) ?? 0) + 1);
  });

  return frames.map((frame) => {
    const longitudeOffset = frame.longitude - longitudeOrigin;
    const latitudeOffset = frame.latitude - latitudeOrigin;
    const anchorLeft = (longitudeOffset / paddedLongitudeSpan) * 100;
    const anchorTop = 100 - (latitudeOffset / paddedLatitudeSpan) * 100;
    const duplicateKey = `${frame.latitude}:${frame.longitude}`;
    const duplicateIndex = duplicateCounts.get(duplicateKey) ?? 0;
    const duplicateGroupSize = duplicateGroupSizes.get(duplicateKey) ?? 1;

    duplicateCounts.set(duplicateKey, duplicateIndex + 1);

    const columnCount = Math.min(duplicateGroupSize, STACK_COLUMNS);
    const rowCount = Math.ceil(duplicateGroupSize / STACK_COLUMNS);
    const columnIndex = duplicateIndex % STACK_COLUMNS;
    const rowIndex = Math.floor(duplicateIndex / STACK_COLUMNS);
    const offsetX =
      (columnIndex - (columnCount - 1) / 2) * STACK_HORIZONTAL_SPACING_PERCENT;
    const offsetY =
      (rowIndex - (rowCount - 1) / 2) * STACK_VERTICAL_SPACING_PERCENT;
    const left = Math.min(
      100 - MAP_EDGE_PADDING_PERCENT,
      Math.max(MAP_EDGE_PADDING_PERCENT, anchorLeft + offsetX),
    );
    const top = Math.min(
      100 - MAP_EDGE_PADDING_PERCENT,
      Math.max(MAP_EDGE_PADDING_PERCENT, anchorTop + offsetY),
    );

    return {
      frame,
      left,
      top,
    };
  });
}

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
        <p className="eyebrow">Slice 4</p>
        <h1>Spatial frame browser</h1>
        <p className="panel-copy">
          Choose a loaded dataset, inspect the stored camera locations, and open
          a frame preview directly from the map.
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
  dataset: DatasetRecord | null;
  selectedFrame: FrameDetailRecord | null;
  loading: boolean;
  error: string | null;
};

function FramePreview({
  dataset,
  selectedFrame,
  loading,
  error,
}: FramePreviewProps): JSX.Element {
  return (
    <section className="workspace-panel preview-panel">
      <div className="section-header section-header--row">
        <div>
          <h2>Frame preview</h2>
          <p className="panel-copy">
            Click any camera marker to inspect the corresponding stored frame.
          </p>
        </div>
        {dataset ? <span className="stat-pill">{dataset.name}</span> : null}
      </div>

      {loading ? <p className="status-message">Loading selected frame...</p> : null}
      {error ? <p className="status-message status-message--error">{error}</p> : null}

      {!loading && !error && !selectedFrame ? (
        <p className="status-message">
          No frame selected yet. Choose a marker from the map to open its
          preview.
        </p>
      ) : null}

      {selectedFrame ? (
        <div className="preview-card">
          <img
            className="preview-image"
            src={buildPreviewUrl(selectedFrame.preview_url)}
            alt={`Preview for ${selectedFrame.frame_id}`}
          />
          <dl className="frame-metadata">
            <div>
              <dt>Frame</dt>
              <dd>{selectedFrame.frame_id}</dd>
            </div>
            <div>
              <dt>Captured</dt>
              <dd>{formatTimestamp(selectedFrame.timestamp)}</dd>
            </div>
            <div>
              <dt>Heading</dt>
              <dd>{selectedFrame.heading_degrees.toFixed(HEADING_PRECISION)} degrees</dd>
            </div>
            <div>
              <dt>Coordinates</dt>
              <dd>
                {formatCoordinate(selectedFrame.latitude)},{" "}
                {formatCoordinate(selectedFrame.longitude)}
              </dd>
            </div>
            <div>
              <dt>Dimensions</dt>
              <dd>
                {selectedFrame.image_width} x {selectedFrame.image_height}
              </dd>
            </div>
            <div>
              <dt>Image path</dt>
              <dd>{selectedFrame.image_path}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </section>
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
      return;
    }

    let isMounted = true;

    async function loadFrames() {
      setFramesLoading(true);
      setFramesError(null);
      setSelectedFrameId(null);
      setSelectedFrame(null);
      setFrameError(null);

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
          dataset={selectedDataset}
          selectedFrame={selectedFrame}
          loading={frameLoading}
          error={frameError}
        />
      </section>

      {framesLoading ? <p className="status-message">Loading frame locations...</p> : null}
      {framesError ? <p className="status-message status-message--error">{framesError}</p> : null}
    </main>
  );
}
