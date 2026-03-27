import {
  useEffect,
  useId,
  useRef,
  useState,
  type JSX,
  type PointerEvent as ReactPointerEvent,
} from "react";

import {
  annotationLabelOptions,
  areBoundingBoxesEqual,
  buildEditableDetections,
  buildRedrawnBoundingBox,
  clipBoundingBox,
  deriveReviewStatusForSave,
  resizeBoundingBox,
  translateBoundingBox,
  validateBoundingBox,
  type BoundingBox,
  type EditableDetection,
  type Point,
  type ResizeHandle,
} from "./annotation";
import type {
  DetectionCorrectionRecord,
  DetectionCorrectionResponse,
  DetectionRecord,
  FrameDetailRecord,
  InferenceRunRecord,
  SaveCorrectionRequest,
} from "./types";
import {
  buildCorrectionSavePath,
  buildDetectionBoxLayout,
  buildPreviewUrl,
  buildViewerMessage,
  describeRunStatus,
  formatCoordinate,
  formatHeading,
  formatTimestamp,
  sendJson,
} from "./viewer";

const ANNOTATION_SOURCE_LABELS = {
  original: "Model output",
  corrected: "Corrected",
} as const;
const REVIEW_STATUS_LABELS = {
  pending: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
} as const;
const POINTER_PRIMARY_BUTTON = 0;

type DetectionViewerProps = {
  datasetId: number | null;
  datasetName: string | null;
  frame: FrameDetailRecord | null;
  run: InferenceRunRecord | null;
  detections: DetectionRecord[];
  corrections: DetectionCorrectionRecord[];
  loading: boolean;
  error: string | null;
  onCorrectionSaved: (correction: DetectionCorrectionRecord) => void;
};

type DraftAnnotation = {
  class_name: string;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
};

type DragMode = "move" | "redraw" | ResizeHandle;

type DragState =
  | {
      mode: "redraw";
      startPoint: Point;
      stageRect: DOMRect;
    }
  | {
      mode: "move" | ResizeHandle;
      startPoint: Point;
      startBox: BoundingBox;
      stageRect: DOMRect;
    };

function RunSummary({
  run,
  frameDetectionCount,
}: {
  run: InferenceRunRecord;
  frameDetectionCount: number;
}): JSX.Element {
  const runStatus = describeRunStatus(run);

  return (
    <section className="run-summary" aria-label="Detection run status">
      <div className="run-summary__header">
        <div>
          <p className="eyebrow">Slice 9</p>
          <h3>Stored detection run</h3>
        </div>
        <span className={`status-pill status-pill--${runStatus.tone}`}>
          {runStatus.label}
        </span>
      </div>

      <dl className="run-summary__grid">
        <div>
          <dt>Model</dt>
          <dd>{run.model_name}</dd>
        </div>
        <div>
          <dt>Frame detections</dt>
          <dd>{frameDetectionCount}</dd>
        </div>
        <div>
          <dt>Dataset detections</dt>
          <dd>{run.detection_count}</dd>
        </div>
        <div>
          <dt>Processed frames</dt>
          <dd>
            {run.processed_frame_count} / {run.frame_count}
          </dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>{formatTimestamp(run.started_at)}</dd>
        </div>
        <div>
          <dt>Completed</dt>
          <dd>{run.completed_at ? formatTimestamp(run.completed_at) : "In progress"}</dd>
        </div>
      </dl>

      {run.error_message ? (
        <p className="run-summary__error">{run.error_message}</p>
      ) : null}
    </section>
  );
}

function buildDraftAnnotation(detection: EditableDetection): DraftAnnotation {
  return {
    class_name: detection.displayed_detection.class_name,
    x_min: detection.displayed_detection.x_min,
    y_min: detection.displayed_detection.y_min,
    x_max: detection.displayed_detection.x_max,
    y_max: detection.displayed_detection.y_max,
  };
}

function getDraftBoundingBox(draft: DraftAnnotation): BoundingBox {
  return {
    x_min: draft.x_min,
    y_min: draft.y_min,
    x_max: draft.x_max,
    y_max: draft.y_max,
  };
}

function buildSelectionSignature(
  detection: EditableDetection | null,
  frameId: string | null,
): string {
  if (detection === null) {
    return `${frameId ?? "none"}:none`;
  }

  const currentDetection = detection.displayed_detection;
  const correctionUpdatedAt = detection.correction?.updated_at ?? "original";

  return [
    frameId ?? "none",
    detection.id,
    correctionUpdatedAt,
    currentDetection.class_name,
    currentDetection.x_min,
    currentDetection.y_min,
    currentDetection.x_max,
    currentDetection.y_max,
  ].join(":");
}

function readPointerPoint(
  event: PointerEvent | ReactPointerEvent<HTMLElement>,
  stageRect: DOMRect,
  frame: Pick<FrameDetailRecord, "image_width" | "image_height">,
): Point {
  const xRatio = frame.image_width / stageRect.width;
  const yRatio = frame.image_height / stageRect.height;

  return {
    x: (event.clientX - stageRect.left) * xRatio,
    y: (event.clientY - stageRect.top) * yRatio,
  };
}

function describeDetectionState(detection: EditableDetection): string {
  const sourceLabel =
    ANNOTATION_SOURCE_LABELS[detection.displayed_detection.source] ?? "Edited";

  if (detection.review_status === null) {
    return sourceLabel;
  }

  return `${sourceLabel} · ${REVIEW_STATUS_LABELS[detection.review_status]}`;
}

export function DetectionViewer({
  datasetId,
  datasetName,
  frame,
  run,
  detections,
  corrections,
  loading,
  error,
  onCorrectionSaved,
}: DetectionViewerProps): JSX.Element {
  const labelOptionsId = useId();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const dragStateRef = useRef<DragState | null>(null);
  const editableDetections = buildEditableDetections(detections, corrections);
  const [selectedDetectionId, setSelectedDetectionId] = useState<number | null>(null);
  const [draftAnnotation, setDraftAnnotation] = useState<DraftAnnotation | null>(null);
  const [isRedrawMode, setIsRedrawMode] = useState(false);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (editableDetections.length === 0) {
      setSelectedDetectionId(null);
      return;
    }

    if (
      selectedDetectionId === null ||
      !editableDetections.some((detection) => detection.id === selectedDetectionId)
    ) {
      setSelectedDetectionId(editableDetections[0].id);
    }
  }, [editableDetections, selectedDetectionId]);

  const selectedDetection =
    editableDetections.find((detection) => detection.id === selectedDetectionId) ?? null;
  const selectionSignature = buildSelectionSignature(
    selectedDetection,
    frame?.frame_id ?? null,
  );

  useEffect(() => {
    if (selectedDetection === null) {
      setDraftAnnotation(null);
      setEditorError(null);
      setSaveMessage(null);
      setIsRedrawMode(false);
      return;
    }

    setDraftAnnotation(buildDraftAnnotation(selectedDetection));
    setEditorError(null);
    setIsRedrawMode(false);
  }, [selectionSignature]);

  useEffect(() => {
    setSaveMessage(null);
  }, [frame?.frame_id, selectedDetectionId]);

  useEffect(() => {
    function handlePointerMove(event: PointerEvent) {
      if (frame === null || draftAnnotation === null) {
        return;
      }

      const dragState = dragStateRef.current;
      if (dragState === null) {
        return;
      }

      const currentPoint = readPointerPoint(event, dragState.stageRect, frame);
      setEditorError(null);
      setSaveMessage(null);

      if (dragState.mode === "redraw") {
        setDraftAnnotation((currentDraftAnnotation) => {
          if (currentDraftAnnotation === null) {
            return currentDraftAnnotation;
          }

          const nextBoundingBox = buildRedrawnBoundingBox(
            dragState.startPoint,
            currentPoint,
            frame,
          );

          return {
            ...currentDraftAnnotation,
            ...nextBoundingBox,
          };
        });

        return;
      }

      if (dragState.mode === "move") {
        const deltaX = currentPoint.x - dragState.startPoint.x;
        const deltaY = currentPoint.y - dragState.startPoint.y;
        const nextBoundingBox = translateBoundingBox(
          dragState.startBox,
          deltaX,
          deltaY,
          frame,
        );

        setDraftAnnotation((currentDraftAnnotation) => {
          if (currentDraftAnnotation === null) {
            return currentDraftAnnotation;
          }

          return {
            ...currentDraftAnnotation,
            ...nextBoundingBox,
          };
        });

        return;
      }

      const nextBoundingBox = resizeBoundingBox(
        dragState.startBox,
        dragState.mode,
        currentPoint,
        frame,
      );

      setDraftAnnotation((currentDraftAnnotation) => {
        if (currentDraftAnnotation === null) {
          return currentDraftAnnotation;
        }

        return {
          ...currentDraftAnnotation,
          ...nextBoundingBox,
        };
      });
    }

    function handlePointerUp() {
      if (dragStateRef.current?.mode === "redraw") {
        setIsRedrawMode(false);
      }

      dragStateRef.current = null;
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [draftAnnotation, frame]);

  const viewerMessage = buildViewerMessage(run, detections, loading, error);
  const draftBoundingBox =
    draftAnnotation === null ? null : getDraftBoundingBox(draftAnnotation);
  const draftValidationError =
    frame !== null && draftBoundingBox !== null
      ? validateBoundingBox(draftBoundingBox, frame)
      : null;
  const selectedBoundingBox =
    selectedDetection === null
      ? null
      : {
          x_min: selectedDetection.displayed_detection.x_min,
          y_min: selectedDetection.displayed_detection.y_min,
          x_max: selectedDetection.displayed_detection.x_max,
          y_max: selectedDetection.displayed_detection.y_max,
        };
  const hasUnsavedChanges =
    selectedDetection !== null &&
    draftAnnotation !== null &&
    (draftAnnotation.class_name.trim() !==
      selectedDetection.displayed_detection.class_name ||
      !areBoundingBoxesEqual(
        getDraftBoundingBox(draftAnnotation),
        selectedBoundingBox as BoundingBox,
      ));
  const editorStatusMessage = editorError ?? draftValidationError ?? saveMessage;
  const editorStatusTone =
    editorError !== null || draftValidationError !== null ? "error" : "neutral";

  function beginDrag(
    mode: DragMode,
    event: ReactPointerEvent<HTMLElement>,
    startBox: BoundingBox | null,
  ) {
    if (
      event.button !== POINTER_PRIMARY_BUTTON ||
      frame === null ||
      stageRef.current === null
    ) {
      return;
    }

    const stageRect = stageRef.current.getBoundingClientRect();
    const startPoint = readPointerPoint(event, stageRect, frame);
    dragStateRef.current =
      mode === "redraw"
        ? {
            mode,
            startPoint,
            stageRect,
          }
        : {
            mode,
            startPoint,
            startBox: startBox as BoundingBox,
            stageRect,
          };
    stageRef.current.setPointerCapture?.(event.pointerId);
    setEditorError(null);
    setSaveMessage(null);
  }

  function handleStagePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (!isRedrawMode || selectedDetection === null) {
      return;
    }

    beginDrag("redraw", event, null);
  }

  function handleMoveStart(event: ReactPointerEvent<HTMLDivElement>) {
    if (selectedDetection === null || draftBoundingBox === null) {
      return;
    }

    beginDrag("move", event, draftBoundingBox);
  }

  function handleResizeStart(
    handle: ResizeHandle,
    event: ReactPointerEvent<HTMLButtonElement>,
  ) {
    event.stopPropagation();

    if (draftBoundingBox === null) {
      return;
    }

    beginDrag(handle, event, draftBoundingBox);
  }

  async function handleSave() {
    if (
      datasetId === null ||
      frame === null ||
      selectedDetection === null ||
      draftAnnotation === null
    ) {
      return;
    }

    const trimmedLabel = draftAnnotation.class_name.trim();
    if (trimmedLabel.length === 0) {
      setEditorError("Label is required before saving a correction.");
      return;
    }

    const clippedBoundingBox = clipBoundingBox(getDraftBoundingBox(draftAnnotation), frame);
    const validationError = validateBoundingBox(clippedBoundingBox, frame);
    if (validationError !== null) {
      setEditorError(validationError);
      return;
    }

    const requestPayload: SaveCorrectionRequest = {
      review_status: deriveReviewStatusForSave(selectedDetection.correction),
      corrected_detection: {
        class_name: trimmedLabel,
        ...clippedBoundingBox,
      },
    };

    setIsSaving(true);
    setEditorError(null);
    setSaveMessage(null);

    try {
      const response = await sendJson<DetectionCorrectionResponse>(
        buildCorrectionSavePath(datasetId, frame.frame_id, selectedDetection.id),
        "POST",
        requestPayload,
      );

      onCorrectionSaved(response.correction);
      setSaveMessage("Saved the updated annotation.");
    } catch (saveError) {
      setEditorError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to save the updated annotation.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  function handleResetSelection() {
    if (selectedDetection === null) {
      return;
    }

    setDraftAnnotation(buildDraftAnnotation(selectedDetection));
    setEditorError(null);
    setSaveMessage(null);
    setIsRedrawMode(false);
  }

  if (frame === null) {
    return (
      <section className="workspace-panel preview-panel">
        <div className="section-header section-header--row">
          <div>
            <h2>Frame inspection</h2>
            <p className="panel-copy">
              Open a stored frame, edit one detection at a time, and save the
              clipped correction without overwriting the original model output.
            </p>
          </div>
          {datasetName ? <span className="stat-pill">{datasetName}</span> : null}
        </div>

        {loading || error ? (
          <p
            className={`status-message${error ? " status-message--error" : ""}`}
            role={error ? "alert" : "status"}
          >
            {error ?? "Loading selected frame and editable overlays..."}
          </p>
        ) : (
          <p className="status-message">
            No frame selected yet. Choose a marker from the map to open the image
            viewer.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="workspace-panel preview-panel">
      <div className="section-header section-header--row">
        <div>
          <h2>Frame inspection</h2>
          <p className="panel-copy">
            Select one stored detection, drag or redraw the box inside the image
            bounds, update the label, and save the correction back to FastAPI.
          </p>
        </div>
        {datasetName ? <span className="stat-pill">{datasetName}</span> : null}
      </div>

      <div className="preview-card">
        {run ? <RunSummary run={run} frameDetectionCount={detections.length} /> : null}

        <figure className="image-viewer">
          <div
            ref={stageRef}
            className={`image-stage${isRedrawMode ? " image-stage--redraw" : ""}`}
            style={{ aspectRatio: `${frame.image_width} / ${frame.image_height}` }}
            onPointerDown={handleStagePointerDown}
          >
            <img
              className="preview-image"
              src={buildPreviewUrl(frame.preview_url)}
              alt={`Selected frame ${frame.frame_id}`}
            />

            <div
              className="overlay-layer overlay-layer--interactive"
              role="presentation"
              aria-hidden={detections.length === 0}
            >
              {editableDetections.map((detection) => {
                const displayDetection =
                  selectedDetection !== null &&
                  draftAnnotation !== null &&
                  detection.id === selectedDetection.id
                    ? {
                        ...detection,
                        class_name: draftAnnotation.class_name,
                        x_min: draftAnnotation.x_min,
                        y_min: draftAnnotation.y_min,
                        x_max: draftAnnotation.x_max,
                        y_max: draftAnnotation.y_max,
                      }
                    : {
                        ...detection.displayed_detection,
                      };
                const layout = buildDetectionBoxLayout(
                  {
                    ...detection,
                    class_name: displayDetection.class_name,
                    x_min: displayDetection.x_min,
                    y_min: displayDetection.y_min,
                    x_max: displayDetection.x_max,
                    y_max: displayDetection.y_max,
                  },
                  frame,
                );
                const isSelected = detection.id === selectedDetection?.id;

                return (
                  <div
                    key={detection.id}
                    className={[
                      "detection-box",
                      "detection-box--interactive",
                      isSelected ? "detection-box--selected" : "",
                      detection.displayed_detection.source === "corrected"
                        ? "detection-box--corrected"
                        : "",
                      detection.review_status === "rejected"
                        ? "detection-box--rejected"
                        : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    style={layout.style}
                    aria-label={layout.label}
                    onClick={() => setSelectedDetectionId(detection.id)}
                    onPointerDown={isSelected ? handleMoveStart : undefined}
                  >
                    <span className="detection-box__label">{layout.label}</span>
                    {isSelected ? (
                      <>
                        <button
                          type="button"
                          className="resize-handle resize-handle--top-left"
                          aria-label="Resize from top left"
                          onPointerDown={(event) =>
                            handleResizeStart("top-left", event)
                          }
                        />
                        <button
                          type="button"
                          className="resize-handle resize-handle--top-right"
                          aria-label="Resize from top right"
                          onPointerDown={(event) =>
                            handleResizeStart("top-right", event)
                          }
                        />
                        <button
                          type="button"
                          className="resize-handle resize-handle--bottom-left"
                          aria-label="Resize from bottom left"
                          onPointerDown={(event) =>
                            handleResizeStart("bottom-left", event)
                          }
                        />
                        <button
                          type="button"
                          className="resize-handle resize-handle--bottom-right"
                          aria-label="Resize from bottom right"
                          onPointerDown={(event) =>
                            handleResizeStart("bottom-right", event)
                          }
                        />
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>

            {viewerMessage ? (
              <div
                className={`viewer-message viewer-message--${viewerMessage.tone}`}
                role={viewerMessage.tone === "error" ? "alert" : "status"}
              >
                <h3>{viewerMessage.title}</h3>
                <p>{viewerMessage.description}</p>
              </div>
            ) : null}
          </div>
          <figcaption className="image-viewer__caption">
            Boxes stay in image pixel coordinates. Drag the selected box to move
            it, use the corner handles to resize it, or redraw it from scratch
            after enabling redraw mode.
          </figcaption>
        </figure>

        {editableDetections.length > 0 ? (
          <section className="annotation-editor" aria-label="Annotation editor">
            <div className="annotation-editor__header">
              <div>
                <p className="eyebrow">Slice 9</p>
                <h3>Annotation editor</h3>
              </div>
              {selectedDetection?.review_status ? (
                <span className="stat-pill">
                  {REVIEW_STATUS_LABELS[selectedDetection.review_status]}
                </span>
              ) : null}
            </div>

            <div className="annotation-editor__list" role="list">
              {editableDetections.map((detection, index) => {
                const isSelected = detection.id === selectedDetection?.id;

                return (
                  <button
                    key={detection.id}
                    type="button"
                    role="listitem"
                    className={`annotation-detection${isSelected ? " annotation-detection--selected" : ""}`}
                    onClick={() => setSelectedDetectionId(detection.id)}
                  >
                    <span className="annotation-detection__title">
                      Detection {index + 1}: {detection.displayed_detection.class_name}
                    </span>
                    <span className="annotation-detection__meta">
                      {describeDetectionState(detection)}
                    </span>
                  </button>
                );
              })}
            </div>

            {selectedDetection !== null && draftAnnotation !== null ? (
              <div className="annotation-editor__details">
                <label className="field-group" htmlFor="annotation-label">
                  <span>Label</span>
                  <input
                    id="annotation-label"
                    name="annotation-label"
                    list={labelOptionsId}
                    value={draftAnnotation.class_name}
                    onChange={(event) => {
                      setDraftAnnotation({
                        ...draftAnnotation,
                        class_name: event.target.value,
                      });
                      setEditorError(null);
                      setSaveMessage(null);
                    }}
                  />
                </label>
                <datalist id={labelOptionsId}>
                  {annotationLabelOptions.map((labelOption) => (
                    <option key={labelOption} value={labelOption} />
                  ))}
                </datalist>

                <dl className="annotation-editor__metrics">
                  <div>
                    <dt>x_min</dt>
                    <dd>{draftAnnotation.x_min.toFixed(1)}</dd>
                  </div>
                  <div>
                    <dt>y_min</dt>
                    <dd>{draftAnnotation.y_min.toFixed(1)}</dd>
                  </div>
                  <div>
                    <dt>x_max</dt>
                    <dd>{draftAnnotation.x_max.toFixed(1)}</dd>
                  </div>
                  <div>
                    <dt>y_max</dt>
                    <dd>{draftAnnotation.y_max.toFixed(1)}</dd>
                  </div>
                </dl>

                <div className="annotation-editor__actions">
                  <button
                    type="button"
                    className={`secondary-button${isRedrawMode ? " secondary-button--active" : ""}`}
                    onClick={() => {
                      setIsRedrawMode((currentValue) => !currentValue);
                      setEditorError(null);
                      setSaveMessage(null);
                    }}
                  >
                    {isRedrawMode ? "Cancel redraw" : "Redraw box"}
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={handleResetSelection}
                    disabled={!hasUnsavedChanges && !isRedrawMode}
                  >
                    Reset
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => {
                      void handleSave();
                    }}
                    disabled={!hasUnsavedChanges || draftValidationError !== null || isSaving}
                  >
                    {isSaving ? "Saving..." : "Save correction"}
                  </button>
                </div>

                <p className="annotation-editor__hint">
                  Click a box to select it. Drag inside the selected box to move
                  it, drag a corner handle to resize it, or redraw it directly on
                  the image. Coordinates are clipped to the image bounds before
                  save.
                </p>

                {editorStatusMessage ? (
                  <p
                    className={`status-message${editorStatusTone === "error" ? " status-message--error" : ""}`}
                    role={editorStatusTone === "error" ? "alert" : "status"}
                  >
                    {editorStatusMessage}
                  </p>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <dl className="frame-metadata">
          <div>
            <dt>Frame</dt>
            <dd>{frame.frame_id}</dd>
          </div>
          <div>
            <dt>Captured</dt>
            <dd>{formatTimestamp(frame.timestamp)}</dd>
          </div>
          <div>
            <dt>Heading</dt>
            <dd>{formatHeading(frame.heading_degrees)}</dd>
          </div>
          <div>
            <dt>Coordinates</dt>
            <dd>
              {formatCoordinate(frame.latitude)}, {formatCoordinate(frame.longitude)}
            </dd>
          </div>
          <div>
            <dt>Dimensions</dt>
            <dd>
              {frame.image_width} x {frame.image_height}
            </dd>
          </div>
          <div>
            <dt>Image path</dt>
            <dd>{frame.image_path}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
