import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./PointCloudCanvas", () => ({
  PointCloudCanvas: ({
    points,
  }: {
    points: { x: number; y: number; z: number }[];
  }) => <div>Rendered points {points.length}</div>,
}));

const datasetListPayload = {
  datasets: [
    {
      id: 1,
      name: "A2D2 demo",
      source_path: "data/raw/a2d2-subset",
      sequence_id: "20190401_121727",
      camera_name: "cam_front_right",
      frame_count: 1,
      created_at: "2026-03-20T10:14:00Z",
    },
  ],
};

const frameListPayload = {
  dataset: datasetListPayload.datasets[0],
  frames: [
    {
      frame_id: "frame-001",
      dataset_id: 1,
      image_path: "frames/frame-001.png",
      latitude: 48.14542,
      longitude: 11.56661,
      heading_degrees: 92.5,
      timestamp: "2026-03-20T10:15:00Z",
      image_width: 1920,
      image_height: 1080,
      pitch_degrees: null,
      roll_degrees: null,
      camera_intrinsics_json: null,
      sequence_id: "20190401_121727",
      depth_path: null,
    },
  ],
};

const metricsPayload = {
  dataset_id: 1,
  run: {
    id: 7,
    dataset_id: 1,
    run_type: "detection",
    status: "completed",
    model_name: "yolo11n",
    model_path: "data/raw/models/yolo11n.pt",
    frame_count: 1,
    processed_frame_count: 1,
    detection_count: 1,
    error_message: null,
    started_at: "2026-03-20T10:16:00Z",
    completed_at: "2026-03-20T10:17:00Z",
  },
  metrics: {
    detection_count: 1,
    average_confidence_score: 0.92,
    correction_count: 0,
    correction_rate: 0,
  },
};

const frameDetailPayload = {
  frame: {
    ...frameListPayload.frames[0],
    preview_url: "/datasets/1/frames/frame-001/preview",
  },
};

const detectionPayload = {
  frame_id: "frame-001",
  run: {
    id: 7,
    dataset_id: 1,
    run_type: "detection",
    status: "completed",
    model_name: "yolo11n",
    model_path: "data/raw/models/yolo11n.pt",
    frame_count: 1,
    processed_frame_count: 1,
    detection_count: 1,
    error_message: null,
    started_at: "2026-03-20T10:16:00Z",
    completed_at: "2026-03-20T10:17:00Z",
  },
  detections: [
    {
      id: 11,
      inference_run_id: 7,
      frame_id: "frame-001",
      class_name: "car",
      confidence_score: 0.92,
      x_min: 96,
      y_min: 54,
      x_max: 960,
      y_max: 540,
      created_at: "2026-03-20T10:17:00Z",
    },
  ],
};

const correctionsPayload = {
  frame_id: "frame-001",
  run: detectionPayload.run,
  corrections: [],
};

const pointCloudPayload = {
  frame_id: "frame-001",
  state: "completed",
  detail: null,
  run: {
    id: 9,
    dataset_id: 1,
    frame_id: "frame-001",
    run_type: "point_cloud",
    status: "completed",
    model_name: "stored-depth-conversion",
    model_path: "depth/frame-001.npy",
    frame_count: 1,
    processed_frame_count: 1,
    detection_count: 0,
    error_message: null,
    started_at: "2026-03-20T10:18:00Z",
    completed_at: "2026-03-20T10:18:05Z",
  },
  artifact: {
    id: 14,
    inference_run_id: 9,
    frame_id: "frame-001",
    source_depth_artifact_id: 8,
    point_cloud_uri: "dataset-1/frame-001/run-9.npz",
    point_format: "float32_npz_xyz",
    coordinate_system: "camera_local_right_handed_x_right_y_up_z_forward",
    source_point_count: 5,
    point_count: 3,
    subsample_step: 2,
    intrinsics_source: "frame_metadata",
    fx: 812.1,
    fy: 811.0,
    cx: 999.3,
    cy: 650.7,
    created_at: "2026-03-20T10:18:05Z",
  },
  payload: {
    points: [
      { x: -0.25, y: 0.12, z: 1.1 },
      { x: -0.1, y: -0.08, z: 1.6 },
      { x: 0.22, y: -0.18, z: 2.3 },
    ],
  },
};

function createJsonResponse(payload: object, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

function mockFetch(
  responses: Record<string, Response>,
): ReturnType<typeof vi.fn> {
  return vi.fn(async (input: string | URL | Request) => {
    const requestUrl = typeof input === "string" ? input : input.toString();
    const matchingPath = Object.keys(responses).find((path) =>
      requestUrl.endsWith(path),
    );

    if (!matchingPath) {
      throw new Error(`Unexpected fetch request: ${requestUrl}`);
    }

    return responses[matchingPath];
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("loads a selected frame and renders stored detection overlays", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "/datasets": createJsonResponse(datasetListPayload),
        "/datasets/1/metrics": createJsonResponse(metricsPayload),
        "/datasets/1/frames": createJsonResponse(frameListPayload),
        "/datasets/1/frames/frame-001": createJsonResponse(frameDetailPayload),
        "/datasets/1/frames/frame-001/detections": createJsonResponse(
          detectionPayload,
        ),
        "/datasets/1/frames/frame-001/corrections": createJsonResponse(
          correctionsPayload,
        ),
        "/datasets/1/frames/frame-001/point-cloud": createJsonResponse(
          pointCloudPayload,
        ),
      }),
    );

    render(<App />);

    const markerButton = await screen.findByRole("button", {
      name: "Open frame frame-001",
    });
    fireEvent.click(markerButton);

    expect(await screen.findByText("car 92%")).toBeInTheDocument();
    expect(screen.getByText("Stored detection run")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Monitoring summary" })).toBeInTheDocument();
    expect(screen.getByText("Detection count")).toBeInTheDocument();
    expect(screen.getByText("Average confidence")).toBeInTheDocument();
    expect(screen.getAllByText("92%").length).toBeGreaterThan(0);
    expect(await screen.findByText("3D point cloud")).toBeInTheDocument();
    expect(screen.getByText("Rendered points")).toBeInTheDocument();
    expect(screen.getAllByText("A2D2 demo")).toHaveLength(2);
  });

  it("shows a useful empty state when no run exists for the selected frame", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "/datasets": createJsonResponse(datasetListPayload),
        "/datasets/1/metrics": createJsonResponse({
          dataset_id: 1,
          run: null,
          metrics: {
            detection_count: 0,
            average_confidence_score: null,
            correction_count: 0,
            correction_rate: 0,
          },
        }),
        "/datasets/1/frames": createJsonResponse(frameListPayload),
        "/datasets/1/frames/frame-001": createJsonResponse(frameDetailPayload),
        "/datasets/1/frames/frame-001/detections": createJsonResponse(
          { detail: "Not found" },
          404,
        ),
        "/datasets/1/frames/frame-001/corrections": createJsonResponse(
          { detail: "Not found" },
          404,
        ),
        "/datasets/1/frames/frame-001/point-cloud": createJsonResponse({
          frame_id: "frame-001",
          state: "missing",
          detail: "Generate depth first before requesting a point cloud.",
          run: null,
          artifact: null,
          payload: null,
        }),
      }),
    );

    render(<App />);

    const markerButton = await screen.findByRole("button", {
      name: "Open frame frame-001",
    });
    fireEvent.click(markerButton);

    expect(await screen.findByText("No detection run yet")).toBeInTheDocument();
    expect(
      screen.getByText(/Run detection for this dataset to populate monitoring metrics/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Run Slice 6 detection for this dataset before expecting overlay output/i,
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("No point cloud yet")).toBeInTheDocument();
  });
});
