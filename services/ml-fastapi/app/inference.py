from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DETECTION_RUN_TYPE = "detection"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_EMPTY = "empty"
RUN_STATUS_FAILED = "failed"
DEFAULT_DETECTION_CONFIDENCE_THRESHOLD = 0.1


@dataclass(frozen=True)
class DetectionPrediction:
    class_name: str
    confidence_score: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class ObjectDetector(Protocol):
    def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
        ...


class UltralyticsObjectDetector:
    def __init__(
        self,
        model_path: Path,
        *,
        confidence_threshold: float = DEFAULT_DETECTION_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self._model = None

    def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
        if not image_paths:
            return []

        model = self._get_model()
        results = model.predict(
            source=[str(image_path) for image_path in image_paths],
            conf=self.confidence_threshold,
            verbose=False,
        )

        predictions: list[list[DetectionPrediction]] = []
        for result in results:
            frame_predictions: list[DetectionPrediction] = []
            for box in result.boxes:
                class_index = int(box.cls.item())
                x_min, y_min, x_max, y_max = box.xyxy[0].tolist()
                frame_predictions.append(
                    DetectionPrediction(
                        class_name=str(model.names[class_index]),
                        confidence_score=float(box.conf.item()),
                        x_min=float(x_min),
                        y_min=float(y_min),
                        x_max=float(x_max),
                        y_max=float(y_max),
                    )
                )
            predictions.append(frame_predictions)

        return predictions

    def _get_model(self):
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(self.model_path))

        return self._model
