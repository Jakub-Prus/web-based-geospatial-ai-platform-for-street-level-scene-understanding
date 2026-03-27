import { describe, expect, it } from "vitest";

import {
  buildEditableDetections,
  buildRedrawnBoundingBox,
  resizeBoundingBox,
  translateBoundingBox,
  validateBoundingBox,
} from "./annotation";
import type { DetectionCorrectionRecord } from "./types";
import { sampleDetections, sampleFrame } from "./test/fixtures";

describe("buildEditableDetections", () => {
  it("uses the corrected effective detection when a saved correction exists", () => {
    const corrections: DetectionCorrectionRecord[] = [
      {
        id: 31,
        detection_id: 11,
        review_status: "approved",
        created_at: "2026-03-20T10:18:00Z",
        updated_at: "2026-03-20T10:19:00Z",
        original_detection: {
          detection_id: 11,
          inference_run_id: 7,
          frame_id: "frame-001",
          class_name: "car",
          confidence_score: 0.92,
          x_min: 96,
          y_min: 54,
          x_max: 960,
          y_max: 540,
          source: "original",
        },
        corrected_detection: {
          detection_id: 11,
          inference_run_id: 7,
          frame_id: "frame-001",
          class_name: "traffic_sign",
          confidence_score: 0.92,
          x_min: 100,
          y_min: 60,
          x_max: 980,
          y_max: 560,
          source: "corrected",
        },
        effective_detection: {
          detection_id: 11,
          inference_run_id: 7,
          frame_id: "frame-001",
          class_name: "traffic_sign",
          confidence_score: 0.92,
          x_min: 100,
          y_min: 60,
          x_max: 980,
          y_max: 560,
          source: "corrected",
        },
      },
    ];

    const [editableDetection] = buildEditableDetections(sampleDetections, corrections);

    expect(editableDetection.displayed_detection.class_name).toBe("traffic_sign");
    expect(editableDetection.displayed_detection.source).toBe("corrected");
    expect(editableDetection.original_detection.class_name).toBe("car");
  });
});

describe("bounding-box helpers", () => {
  it("clips a redrawn box to the image bounds and normalizes its coordinates", () => {
    const boundingBox = buildRedrawnBoundingBox(
      { x: 2000, y: 200 },
      { x: -20, y: 1200 },
      sampleFrame,
    );

    expect(boundingBox).toEqual({
      x_min: 0,
      y_min: 200,
      x_max: 1920,
      y_max: 1080,
    });
  });

  it("moves a box without shrinking it when it hits an image edge", () => {
    const movedBoundingBox = translateBoundingBox(
      {
        x_min: 96,
        y_min: 54,
        x_max: 960,
        y_max: 540,
      },
      -200,
      700,
      sampleFrame,
    );

    expect(movedBoundingBox).toEqual({
      x_min: 0,
      y_min: 594,
      x_max: 864,
      y_max: 1080,
    });
  });

  it("resizes a box but keeps x_min, y_min, x_max, y_max semantics intact", () => {
    const resizedBoundingBox = resizeBoundingBox(
      {
        x_min: 96,
        y_min: 54,
        x_max: 960,
        y_max: 540,
      },
      "top-left",
      { x: 1100, y: 600 },
      sampleFrame,
    );

    expect(resizedBoundingBox).toEqual({
      x_min: 959,
      y_min: 539,
      x_max: 960,
      y_max: 540,
    });
  });

  it("rejects collapsed boxes after clipping", () => {
    expect(
      validateBoundingBox(
        {
          x_min: 2000,
          y_min: 50,
          x_max: 2200,
          y_max: 400,
        },
        sampleFrame,
      ),
    ).toBe("Box width must stay greater than zero after clipping to the image bounds.");
  });
});
