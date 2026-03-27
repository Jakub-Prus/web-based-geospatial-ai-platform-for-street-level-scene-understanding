import type {
  DetectionCorrectionRecord,
  DetectionRecord,
  DetectionStateRecord,
  FrameDetailRecord,
  ReviewStatus,
} from "./types";

const MINIMUM_IMAGE_COORDINATE = 0;
const MINIMUM_BOX_SIZE_PIXELS = 1;
const LABEL_OPTION_SET = [
  "car",
  "traffic_sign",
  "building",
  "pole",
  "person",
] as const;

export const annotationLabelOptions = [...LABEL_OPTION_SET];

export type BoundingBox = Pick<
  DetectionStateRecord,
  "x_min" | "y_min" | "x_max" | "y_max"
>;

export type Point = {
  x: number;
  y: number;
};

export type ResizeHandle =
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right";

export type EditableDetection = DetectionRecord & {
  displayed_detection: DetectionStateRecord;
  original_detection: DetectionStateRecord;
  correction: DetectionCorrectionRecord | null;
  review_status: ReviewStatus | null;
};

export function buildEditableDetections(
  detections: DetectionRecord[],
  corrections: DetectionCorrectionRecord[],
): EditableDetection[] {
  const correctionsByDetectionId = new Map(
    corrections.map((correction) => [correction.detection_id, correction]),
  );

  return detections.map((detection) => {
    const fallbackDetection = buildOriginalDetectionState(detection);
    const correction = correctionsByDetectionId.get(detection.id) ?? null;
    const displayedDetection =
      correction?.effective_detection ??
      correction?.corrected_detection ??
      correction?.original_detection ??
      fallbackDetection;

    return {
      ...detection,
      displayed_detection: displayedDetection,
      original_detection: correction?.original_detection ?? fallbackDetection,
      correction,
      review_status: correction?.review_status ?? null,
    };
  });
}

export function buildOriginalDetectionState(
  detection: DetectionRecord,
): DetectionStateRecord {
  return {
    detection_id: detection.id,
    inference_run_id: detection.inference_run_id,
    frame_id: detection.frame_id,
    class_name: detection.class_name,
    confidence_score: detection.confidence_score,
    x_min: detection.x_min,
    y_min: detection.y_min,
    x_max: detection.x_max,
    y_max: detection.y_max,
    source: "original",
  };
}

export function clipBoundingBox(
  boundingBox: BoundingBox,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): BoundingBox {
  return {
    x_min: clampCoordinate(boundingBox.x_min, frame.image_width),
    y_min: clampCoordinate(boundingBox.y_min, frame.image_height),
    x_max: clampCoordinate(boundingBox.x_max, frame.image_width),
    y_max: clampCoordinate(boundingBox.y_max, frame.image_height),
  };
}

export function buildRedrawnBoundingBox(
  startPoint: Point,
  endPoint: Point,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): BoundingBox {
  const clippedStartPoint = clipPointToFrame(startPoint, frame);
  const clippedEndPoint = clipPointToFrame(endPoint, frame);

  return {
    x_min: Math.min(clippedStartPoint.x, clippedEndPoint.x),
    y_min: Math.min(clippedStartPoint.y, clippedEndPoint.y),
    x_max: Math.max(clippedStartPoint.x, clippedEndPoint.x),
    y_max: Math.max(clippedStartPoint.y, clippedEndPoint.y),
  };
}

export function translateBoundingBox(
  boundingBox: BoundingBox,
  deltaX: number,
  deltaY: number,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): BoundingBox {
  const minimumDeltaX = MINIMUM_IMAGE_COORDINATE - boundingBox.x_min;
  const maximumDeltaX = frame.image_width - boundingBox.x_max;
  const minimumDeltaY = MINIMUM_IMAGE_COORDINATE - boundingBox.y_min;
  const maximumDeltaY = frame.image_height - boundingBox.y_max;
  const constrainedDeltaX = Math.min(
    maximumDeltaX,
    Math.max(minimumDeltaX, deltaX),
  );
  const constrainedDeltaY = Math.min(
    maximumDeltaY,
    Math.max(minimumDeltaY, deltaY),
  );

  return {
    x_min: boundingBox.x_min + constrainedDeltaX,
    y_min: boundingBox.y_min + constrainedDeltaY,
    x_max: boundingBox.x_max + constrainedDeltaX,
    y_max: boundingBox.y_max + constrainedDeltaY,
  };
}

export function resizeBoundingBox(
  boundingBox: BoundingBox,
  handle: ResizeHandle,
  pointer: Point,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): BoundingBox {
  const clippedPointer = clipPointToFrame(pointer, frame);

  if (handle === "top-left") {
    return {
      x_min: clampWithinRange(
        clippedPointer.x,
        MINIMUM_IMAGE_COORDINATE,
        boundingBox.x_max - MINIMUM_BOX_SIZE_PIXELS,
      ),
      y_min: clampWithinRange(
        clippedPointer.y,
        MINIMUM_IMAGE_COORDINATE,
        boundingBox.y_max - MINIMUM_BOX_SIZE_PIXELS,
      ),
      x_max: boundingBox.x_max,
      y_max: boundingBox.y_max,
    };
  }

  if (handle === "top-right") {
    return {
      x_min: boundingBox.x_min,
      y_min: clampWithinRange(
        clippedPointer.y,
        MINIMUM_IMAGE_COORDINATE,
        boundingBox.y_max - MINIMUM_BOX_SIZE_PIXELS,
      ),
      x_max: clampWithinRange(
        clippedPointer.x,
        boundingBox.x_min + MINIMUM_BOX_SIZE_PIXELS,
        frame.image_width,
      ),
      y_max: boundingBox.y_max,
    };
  }

  if (handle === "bottom-left") {
    return {
      x_min: clampWithinRange(
        clippedPointer.x,
        MINIMUM_IMAGE_COORDINATE,
        boundingBox.x_max - MINIMUM_BOX_SIZE_PIXELS,
      ),
      y_min: boundingBox.y_min,
      x_max: boundingBox.x_max,
      y_max: clampWithinRange(
        clippedPointer.y,
        boundingBox.y_min + MINIMUM_BOX_SIZE_PIXELS,
        frame.image_height,
      ),
    };
  }

  return {
    x_min: boundingBox.x_min,
    y_min: boundingBox.y_min,
    x_max: clampWithinRange(
      clippedPointer.x,
      boundingBox.x_min + MINIMUM_BOX_SIZE_PIXELS,
      frame.image_width,
    ),
    y_max: clampWithinRange(
      clippedPointer.y,
      boundingBox.y_min + MINIMUM_BOX_SIZE_PIXELS,
      frame.image_height,
    ),
  };
}

export function validateBoundingBox(
  boundingBox: BoundingBox,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): string | null {
  const clippedBoundingBox = clipBoundingBox(boundingBox, frame);

  if (clippedBoundingBox.x_min >= clippedBoundingBox.x_max) {
    return "Box width must stay greater than zero after clipping to the image bounds.";
  }

  if (clippedBoundingBox.y_min >= clippedBoundingBox.y_max) {
    return "Box height must stay greater than zero after clipping to the image bounds.";
  }

  return null;
}

export function areBoundingBoxesEqual(
  leftBoundingBox: BoundingBox,
  rightBoundingBox: BoundingBox,
): boolean {
  return (
    leftBoundingBox.x_min === rightBoundingBox.x_min &&
    leftBoundingBox.y_min === rightBoundingBox.y_min &&
    leftBoundingBox.x_max === rightBoundingBox.x_max &&
    leftBoundingBox.y_max === rightBoundingBox.y_max
  );
}

export function deriveReviewStatusForSave(
  correction: DetectionCorrectionRecord | null,
): ReviewStatus {
  if (correction === null || correction.review_status === "rejected") {
    return "pending";
  }

  return correction.review_status;
}

function clampCoordinate(value: number, maximumValue: number): number {
  return clampWithinRange(value, MINIMUM_IMAGE_COORDINATE, maximumValue);
}

function clipPointToFrame(
  point: Point,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): Point {
  return {
    x: clampCoordinate(point.x, frame.image_width),
    y: clampCoordinate(point.y, frame.image_height),
  };
}

function clampWithinRange(
  value: number,
  minimumValue: number,
  maximumValue: number,
): number {
  return Math.min(maximumValue, Math.max(minimumValue, value));
}
