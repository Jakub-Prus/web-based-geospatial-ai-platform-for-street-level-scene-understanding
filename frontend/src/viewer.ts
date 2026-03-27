import type { CSSProperties } from "react";

import type {
  DetectionRecord,
  FrameDetailRecord,
  FramePointCloudResponse,
  FrameRecord,
  InferenceRunRecord,
} from "./types";

const DEFAULT_FASTAPI_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const MAP_PADDING_RATIO = 0.12;
const MIN_COORDINATE_SPAN = 0.0001;
const STACK_COLUMNS = 4;
const STACK_HORIZONTAL_SPACING_PERCENT = 2.6;
const STACK_VERTICAL_SPACING_PERCENT = 2.4;
const MAP_EDGE_PADDING_PERCENT = 2;
const COORDINATE_PRECISION = 6;
const HEADING_PRECISION = 1;
const CONFIDENCE_PERCENTAGE_SCALE = 100;
const PERCENTAGE_SCALE = 100;
const MINIMUM_PERCENT = 0;
const MAXIMUM_PERCENT = 100;
const DETECTION_COLOR_PALETTE = [
  "#ed6a32",
  "#1b9aaa",
  "#9c6644",
  "#6a994e",
  "#b56576",
  "#5b4b8a",
];

export const apiBaseUrl =
  import.meta.env.VITE_FASTAPI_BASE_URL ?? DEFAULT_FASTAPI_URL;

export type MarkerPosition = {
  frame: FrameRecord;
  left: number;
  top: number;
};

export type ApiError = Error & {
  status: number;
};

export type ViewerMessageTone = "neutral" | "warning" | "error";

export type ViewerMessage = {
  title: string;
  description: string;
  tone: ViewerMessageTone;
};

export type PointCloudSummary = {
  renderedPointCount: number;
  sourcePointCount: number;
  subsampleStep: number;
};

export type DetectionBoxLayout = {
  style: CSSProperties;
  accentColor: string;
  label: string;
};

function clampPercent(value: number): number {
  return Math.min(MAXIMUM_PERCENT, Math.max(MINIMUM_PERCENT, value));
}

function toPercentCoordinate(value: number, imageExtent: number): number {
  if (imageExtent <= 0) {
    return MINIMUM_PERCENT;
  }

  return clampPercent((value / imageExtent) * PERCENTAGE_SCALE);
}

function selectDetectionAccentColor(label: string): string {
  const paletteIndex = [...label].reduce(
    (accumulator, character) => accumulator + character.charCodeAt(0),
    0,
  );

  return DETECTION_COLOR_PALETTE[paletteIndex % DETECTION_COLOR_PALETTE.length];
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);

  if (!response.ok) {
    const error = new Error(
      `Request failed for ${path}: ${response.status}`,
    ) as ApiError;
    error.status = response.status;
    throw error;
  }

  return (await response.json()) as T;
}

export async function sendJson<TResponse>(
  path: string,
  method: "POST",
  body: object,
): Promise<TResponse> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let errorDetail = `Request failed for ${path}: ${response.status}`;

    try {
      const errorPayload = (await response.json()) as { detail?: string };
      if (errorPayload.detail) {
        errorDetail = errorPayload.detail;
      }
    } catch {
      // Ignore non-JSON error responses and use the default detail.
    }

    const error = new Error(errorDetail) as ApiError;
    error.status = response.status;
    throw error;
  }

  return (await response.json()) as TResponse;
}

export function buildPreviewUrl(previewPath: string): string {
  return new URL(previewPath, apiBaseUrl).toString();
}

export function formatTimestamp(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(timestamp));
}

export function formatCoordinate(value: number): string {
  return value.toFixed(COORDINATE_PRECISION);
}

export function formatHeading(value: number): string {
  return `${value.toFixed(HEADING_PRECISION)} degrees`;
}

export function formatPercentage(value: number): string {
  return `${Math.round(value * CONFIDENCE_PERCENTAGE_SCALE)}%`;
}

export function formatConfidence(value: number): string {
  return formatPercentage(value);
}

export function buildMarkerPositions(frames: FrameRecord[]): MarkerPosition[] {
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
  const longitudeSpan = Math.max(
    maximumLongitude - minimumLongitude,
    MIN_COORDINATE_SPAN,
  );
  const paddedLatitudeSpan = latitudeSpan * (1 + MAP_PADDING_RATIO * 2);
  const paddedLongitudeSpan = longitudeSpan * (1 + MAP_PADDING_RATIO * 2);
  const latitudeOrigin = minimumLatitude - latitudeSpan * MAP_PADDING_RATIO;
  const longitudeOrigin = minimumLongitude - longitudeSpan * MAP_PADDING_RATIO;
  const duplicateCounts = new Map<string, number>();
  const duplicateGroupSizes = new Map<string, number>();

  frames.forEach((frame) => {
    const duplicateKey = `${frame.latitude}:${frame.longitude}`;
    duplicateGroupSizes.set(
      duplicateKey,
      (duplicateGroupSizes.get(duplicateKey) ?? 0) + 1,
    );
  });

  return frames.map((frame) => {
    const longitudeOffset = frame.longitude - longitudeOrigin;
    const latitudeOffset = frame.latitude - latitudeOrigin;
    const anchorLeft = (longitudeOffset / paddedLongitudeSpan) * PERCENTAGE_SCALE;
    const anchorTop =
      PERCENTAGE_SCALE - (latitudeOffset / paddedLatitudeSpan) * PERCENTAGE_SCALE;
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

    return {
      frame,
      left: Math.min(
        PERCENTAGE_SCALE - MAP_EDGE_PADDING_PERCENT,
        Math.max(MAP_EDGE_PADDING_PERCENT, anchorLeft + offsetX),
      ),
      top: Math.min(
        PERCENTAGE_SCALE - MAP_EDGE_PADDING_PERCENT,
        Math.max(MAP_EDGE_PADDING_PERCENT, anchorTop + offsetY),
      ),
    };
  });
}

export function buildDetectionBoxLayout(
  detection: DetectionRecord,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): DetectionBoxLayout {
  const left = toPercentCoordinate(detection.x_min, frame.image_width);
  const top = toPercentCoordinate(detection.y_min, frame.image_height);
  const right = toPercentCoordinate(detection.x_max, frame.image_width);
  const bottom = toPercentCoordinate(detection.y_max, frame.image_height);
  const accentColor = selectDetectionAccentColor(detection.class_name);

  return {
    accentColor,
    label: `${detection.class_name} ${formatConfidence(detection.confidence_score)}`,
    style: {
      left: `${left}%`,
      top: `${top}%`,
      width: `${Math.max(MINIMUM_PERCENT, right - left)}%`,
      height: `${Math.max(MINIMUM_PERCENT, bottom - top)}%`,
      "--detection-accent": accentColor,
    } as CSSProperties,
  };
}

export function buildCorrectionSavePath(
  datasetId: number,
  frameId: string,
  detectionId: number,
): string {
  return `/datasets/${datasetId}/frames/${frameId}/detections/${detectionId}/correction`;
}

export function buildCorrectionsPath(datasetId: number, frameId: string): string {
  return `/datasets/${datasetId}/frames/${frameId}/corrections`;
}

export function buildDatasetMetricsPath(datasetId: number): string {
  return `/datasets/${datasetId}/metrics`;
}

export function buildPointCloudPath(datasetId: number, frameId: string): string {
  return `/datasets/${datasetId}/frames/${frameId}/point-cloud`;
}

export function describeRunStatus(run: InferenceRunRecord): {
  label: string;
  tone: ViewerMessageTone;
} {
  if (run.status === "completed") {
    return { label: "Completed", tone: "neutral" };
  }

  if (run.status === "empty") {
    return { label: "No detections", tone: "warning" };
  }

  if (run.status === "failed") {
    return { label: "Failed", tone: "error" };
  }

  if (run.status === "running") {
    return { label: "Running", tone: "warning" };
  }

  return { label: run.status, tone: "neutral" };
}

export function buildViewerMessage(
  run: InferenceRunRecord | null,
  detections: DetectionRecord[],
  isLoading: boolean,
  error: string | null,
): ViewerMessage | null {
  if (isLoading) {
    return {
      title: "Loading overlays",
      description: "Stored detections and run metadata are loading for this frame.",
      tone: "neutral",
    };
  }

  if (error) {
    return {
      title: "Unable to load overlays",
      description: error,
      tone: "error",
    };
  }

  if (run === null) {
    return {
      title: "No detection run yet",
      description:
        "Run Slice 6 detection for this dataset before expecting overlay output in the viewer.",
      tone: "warning",
    };
  }

  if (run.status === "failed") {
    return {
      title: "Latest run failed",
      description:
        run.error_message ??
        "The last detection run failed, so there are no stored overlays for this frame.",
      tone: "error",
    };
  }

  if (run.status === "running") {
    return {
      title: "Detection run in progress",
      description:
        "This dataset is still processing. Stored overlays will appear when the run completes.",
      tone: "warning",
    };
  }

  if (detections.length === 0) {
    return {
      title: "No detections for this frame",
      description:
        "The latest stored run does not contain any bounding boxes for the selected image.",
      tone: run.status === "empty" ? "warning" : "neutral",
    };
  }

  return null;
}

export function buildPointCloudSummary(
  response: FramePointCloudResponse | null,
): PointCloudSummary | null {
  const artifact = response?.artifact;

  if (artifact === null || artifact === undefined) {
    return null;
  }

  return {
    renderedPointCount: artifact.point_count,
    sourcePointCount: artifact.source_point_count,
    subsampleStep: artifact.subsample_step,
  };
}

export function buildPointCloudViewerMessage(
  response: FramePointCloudResponse | null,
  isLoading: boolean,
  error: string | null,
  renderError: string | null,
): ViewerMessage | null {
  if (isLoading) {
    return {
      title: "Loading 3D point cloud",
      description: "Stored point-cloud data is loading for this selected frame.",
      tone: "neutral",
    };
  }

  if (error !== null) {
    return {
      title: "Unable to load 3D view",
      description: error,
      tone: "error",
    };
  }

  if (renderError !== null) {
    return {
      title: "Unable to render 3D view",
      description: renderError,
      tone: "error",
    };
  }

  if (response === null) {
    return {
      title: "No point cloud yet",
      description:
        "Select a stored frame and generate Slice 11 point-cloud output before expecting a 3D view.",
      tone: "warning",
    };
  }

  if (response.state === "missing") {
    return {
      title: "No point cloud yet",
      description:
        response.detail ??
        "Generate Slice 11 point-cloud output for this frame before expecting 3D inspection.",
      tone: "warning",
    };
  }

  if (response.state === "running") {
    return {
      title: "3D generation in progress",
      description:
        response.detail ??
        "Point-cloud generation is still running for this frame. Refresh after it completes.",
      tone: "warning",
    };
  }

  if (response.state === "failed") {
    return {
      title: "3D generation failed",
      description:
        response.detail ??
        "The latest point-cloud run failed, so no interactive 3D view is available for this frame.",
      tone: "error",
    };
  }

  const pointCount = response.payload?.points.length ?? 0;
  if (pointCount === 0) {
    return {
      title: "Point cloud is empty",
      description:
        "The latest point-cloud artifact loaded successfully, but it does not contain any renderable points.",
      tone: "warning",
    };
  }

  return null;
}
