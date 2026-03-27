from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

DETECTION_RUN_TYPE = "detection"
DEPTH_RUN_TYPE = "depth"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_EMPTY = "empty"
RUN_STATUS_FAILED = "failed"
DEFAULT_DETECTION_CONFIDENCE_THRESHOLD = 0.1
DEFAULT_DEPTH_SCALE = 1.0
DEFAULT_DEPTH_ARTIFACT_FORMAT = "float32_npy_inverse_depth"
MIDAS_HUB_REPOSITORY = "isl-org/MiDaS"
MIDAS_HUB_MODEL_ENTRYPOINT = "DPT_SwinV2_T_256"
MIDAS_HUB_TRANSFORMS_ENTRYPOINT = "transforms"
MIDAS_TRANSFORM_ATTRIBUTE_NAME = "swin256_transform"


@dataclass(frozen=True)
class DetectionPrediction:
    class_name: str
    confidence_score: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class DepthPrediction:
    depth_map: np.ndarray
    depth_format: str = DEFAULT_DEPTH_ARTIFACT_FORMAT
    depth_scale: float = DEFAULT_DEPTH_SCALE


class ObjectDetector(Protocol):
    def detect(self, image_paths: list[Path]) -> list[list[DetectionPrediction]]:
        ...


class DepthEstimator(Protocol):
    def estimate(self, image_path: Path) -> DepthPrediction:
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


class MidasDepthEstimator:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self._model = None
        self._transform = None
        self._cv2 = None
        self._torch = None

    def estimate(self, image_path: Path) -> DepthPrediction:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Depth model file was not found: {self.model_path}")

        cv2 = self._get_cv2()
        torch = self._get_torch()

        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(f"Depth source image was not found: {image_path}")

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        source_height, source_width = rgb_image.shape[:2]
        input_batch = self._get_transform()(rgb_image)

        with torch.no_grad():
            prediction = self._get_model()(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=(source_height, source_width),
                mode="bicubic",
                align_corners=False,
            ).squeeze(0).squeeze(0)

        depth_map = prediction.cpu().numpy().astype(np.float32, copy=False)
        return DepthPrediction(depth_map=depth_map)

    def _get_cv2(self):
        if self._cv2 is None:
            import cv2

            self._cv2 = cv2

        return self._cv2

    def _get_torch(self):
        if self._torch is None:
            import torch

            self._torch = torch

        return self._torch

    def _get_model(self):
        if self._model is None:
            torch = self._get_torch()
            model = torch.hub.load(
                MIDAS_HUB_REPOSITORY,
                MIDAS_HUB_MODEL_ENTRYPOINT,
                pretrained=False,
                trust_repo=True,
            )
            state_dict = torch.load(self.model_path, map_location="cpu")
            model.load_state_dict(state_dict)
            model.eval()
            self._model = model

        return self._model

    def _get_transform(self):
        if self._transform is None:
            torch = self._get_torch()
            transforms = torch.hub.load(
                MIDAS_HUB_REPOSITORY,
                MIDAS_HUB_TRANSFORMS_ENTRYPOINT,
                trust_repo=True,
            )
            self._transform = getattr(transforms, MIDAS_TRANSFORM_ATTRIBUTE_NAME)

        return self._transform
