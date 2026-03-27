import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

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
        "/datasets/1/frames": createJsonResponse(frameListPayload),
        "/datasets/1/frames/frame-001": createJsonResponse(frameDetailPayload),
        "/datasets/1/frames/frame-001/detections": createJsonResponse(
          detectionPayload,
        ),
        "/datasets/1/frames/frame-001/corrections": createJsonResponse(
          correctionsPayload,
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
    expect(screen.getAllByText("A2D2 demo")).toHaveLength(2);
  });

  it("shows a useful empty state when no run exists for the selected frame", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "/datasets": createJsonResponse(datasetListPayload),
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
      }),
    );

    render(<App />);

    const markerButton = await screen.findByRole("button", {
      name: "Open frame frame-001",
    });
    fireEvent.click(markerButton);

    expect(await screen.findByText("No detection run yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Run Slice 6 detection for this dataset before expecting overlay output/i,
      ),
    ).toBeInTheDocument();
  });
});
