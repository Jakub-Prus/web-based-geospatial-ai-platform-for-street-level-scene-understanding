import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DetectionViewer } from "./DetectionViewer";
import type {
  DetectionRecord,
  FrameDetailRecord,
  InferenceRunRecord,
} from "./types";
import { buildDetectionBoxLayout, buildViewerMessage } from "./viewer";

const frame: FrameDetailRecord = {
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
  sequence_id: "sequence-1",
  depth_path: null,
  preview_url: "/datasets/1/frames/frame-001/preview",
};

const run: InferenceRunRecord = {
  id: 7,
  dataset_id: 1,
  run_type: "detection",
  status: "completed",
  model_name: "yolo11n",
  model_path: "data/raw/models/yolo11n.pt",
  frame_count: 2,
  processed_frame_count: 2,
  detection_count: 3,
  error_message: null,
  started_at: "2026-03-20T10:16:00Z",
  completed_at: "2026-03-20T10:17:00Z",
};

const detections: DetectionRecord[] = [
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
];

describe("buildDetectionBoxLayout", () => {
  it("converts stored pixel coordinates into percentage layout", () => {
    const layout = buildDetectionBoxLayout(detections[0], frame);

    expect(layout.style.left).toBe("5%");
    expect(layout.style.top).toBe("5%");
    expect(layout.style.width).toBe("45%");
    expect(layout.style.height).toBe("45%");
    expect(layout.label).toBe("car 92%");
  });
});

describe("buildViewerMessage", () => {
  it("describes missing detection runs as a useful empty state", () => {
    expect(buildViewerMessage(null, [], false, null)).toMatchObject({
      title: "No detection run yet",
      tone: "warning",
    });
  });

  it("surfaces failed runs as an error state", () => {
    const failedRun = {
      ...run,
      status: "failed",
      error_message: "synthetic detector failure",
    };

    expect(buildViewerMessage(failedRun, [], false, null)).toMatchObject({
      title: "Latest run failed",
      tone: "error",
    });
  });
});

describe("DetectionViewer", () => {
  it("renders stored boxes, labels, confidence, and run metadata", () => {
    render(
      <DetectionViewer
        datasetName="A2D2 demo"
        frame={frame}
        run={run}
        detections={detections}
        loading={false}
        error={null}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Stored detection run" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Completed")).toHaveLength(2);
    expect(screen.getByText("car 92%")).toBeInTheDocument();
    expect(screen.getByText("yolo11n")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Bounding boxes are rendered from stored pixel coordinates/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders a readable empty state when a frame has no detections", () => {
    render(
      <DetectionViewer
        datasetName="A2D2 demo"
        frame={frame}
        run={{ ...run, status: "empty", detection_count: 0 }}
        detections={[]}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("No detections for this frame")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The latest stored run does not contain any bounding boxes for the selected image.",
      ),
    ).toBeInTheDocument();
  });
});
