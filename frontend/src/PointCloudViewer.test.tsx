import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PointCloudViewer } from "./PointCloudViewer";
import { sampleFrame, samplePointCloudResponse } from "./test/fixtures";
import { buildPointCloudViewerMessage } from "./viewer";

vi.mock("./PointCloudCanvas", () => ({
  PointCloudCanvas: ({
    points,
    ariaLabel,
  }: {
    points: { x: number; y: number; z: number }[];
    ariaLabel: string;
  }) => (
    <div data-testid="point-cloud-canvas" aria-label={ariaLabel}>
      Rendered {points.length} points
    </div>
  ),
}));

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

describe("buildPointCloudViewerMessage", () => {
  it("describes a missing point cloud with a useful empty state", () => {
    expect(
      buildPointCloudViewerMessage(
        {
          ...samplePointCloudResponse,
          state: "missing",
          detail: "Generate depth first before requesting a point cloud.",
          artifact: null,
          payload: null,
          run: null,
        },
        false,
        null,
        null,
      ),
    ).toMatchObject({
      title: "No point cloud yet",
      tone: "warning",
    });
  });

  it("surfaces rendering failures as an error state", () => {
    expect(
      buildPointCloudViewerMessage(
        samplePointCloudResponse,
        false,
        null,
        "WebGL is unavailable.",
      ),
    ).toMatchObject({
      title: "Unable to render 3D view",
      tone: "error",
    });
  });
});

describe("PointCloudViewer", () => {
  it("loads a completed point cloud and renders the 3D canvas summary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => createJsonResponse(samplePointCloudResponse)),
    );

    render(<PointCloudViewer datasetId={1} frame={sampleFrame} />);

    expect(await screen.findByTestId("point-cloud-canvas")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "3D point cloud" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Rendered 3 points")).toBeInTheDocument();
    expect(screen.getByText("camera_local_right_handed_x_right_y_up_z_forward")).toBeInTheDocument();
  });

  it("shows an understandable fallback when no point cloud exists yet", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        createJsonResponse({
          ...samplePointCloudResponse,
          state: "missing",
          detail: "Generate depth first before requesting a point cloud.",
          artifact: null,
          payload: null,
          run: null,
        }),
      ),
    );

    render(<PointCloudViewer datasetId={1} frame={sampleFrame} />);

    expect(await screen.findByText("No point cloud yet")).toBeInTheDocument();
    expect(
      screen.getByText("Generate depth first before requesting a point cloud."),
    ).toBeInTheDocument();
  });
});
