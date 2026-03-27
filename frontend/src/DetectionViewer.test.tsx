import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DetectionViewer } from "./DetectionViewer";
import { sampleDetections, sampleFrame, sampleRun, sampleSavedCorrection } from "./test/fixtures";
import { buildDetectionBoxLayout, buildViewerMessage } from "./viewer";

function createJsonResponse(payload: object, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response;
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("buildDetectionBoxLayout", () => {
  it("converts stored pixel coordinates into percentage layout", () => {
    const layout = buildDetectionBoxLayout(sampleDetections[0], sampleFrame);

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
      ...sampleRun,
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
        datasetId={1}
        datasetName="A2D2 demo"
        frame={sampleFrame}
        run={sampleRun}
        detections={sampleDetections}
        corrections={[]}
        loading={false}
        error={null}
        onCorrectionSaved={vi.fn()}
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
        /Boxes stay in image pixel coordinates/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Detection 1:\s*car/i)).toBeInTheDocument();
  });

  it("renders a readable empty state when a frame has no detections", () => {
    render(
      <DetectionViewer
        datasetId={1}
        datasetName="A2D2 demo"
        frame={sampleFrame}
        run={{ ...sampleRun, status: "empty", detection_count: 0 }}
        detections={[]}
        corrections={[]}
        loading={false}
        error={null}
        onCorrectionSaved={vi.fn()}
      />,
    );

    expect(screen.getByText("No detections for this frame")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The latest stored run does not contain any bounding boxes for the selected image.",
      ),
    ).toBeInTheDocument();
  });

  it("lets a user relabel and save one detection", async () => {
    const fetchMock = vi.fn(async () =>
      createJsonResponse({ correction: sampleSavedCorrection }),
    );
    const onCorrectionSaved = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <DetectionViewer
        datasetId={1}
        datasetName="A2D2 demo"
        frame={sampleFrame}
        run={sampleRun}
        detections={sampleDetections}
        corrections={[]}
        loading={false}
        error={null}
        onCorrectionSaved={onCorrectionSaved}
      />,
    );

    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "traffic_sign" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save correction" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const requestArguments = fetchMock.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    const [requestUrl, requestInit] = requestArguments;
    expect(String(requestUrl)).toContain(
      "/datasets/1/frames/frame-001/detections/11/correction",
    );
    expect(requestInit.method).toBe("POST");
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      review_status: "pending",
      corrected_detection: {
        class_name: "traffic_sign",
        x_min: 96,
        y_min: 54,
        x_max: 960,
        y_max: 540,
      },
    });

    await waitFor(() => {
      expect(onCorrectionSaved).toHaveBeenCalledWith(sampleSavedCorrection);
    });
    expect(
      await screen.findByText("Saved the updated annotation."),
    ).toBeInTheDocument();
  });
});
