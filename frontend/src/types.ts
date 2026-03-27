export type DatasetRecord = {
  id: number;
  name: string;
  source_path: string;
  sequence_id: string;
  camera_name: string;
  frame_count: number;
  created_at: string;
};

export type FrameRecord = {
  frame_id: string;
  dataset_id: number;
  image_path: string;
  latitude: number;
  longitude: number;
  heading_degrees: number;
  timestamp: string;
  image_width: number;
  image_height: number;
  pitch_degrees: number | null;
  roll_degrees: number | null;
  camera_intrinsics_json: string | null;
  sequence_id: string | null;
  depth_path: string | null;
};

export type FrameDetailRecord = FrameRecord & {
  preview_url: string;
};

export type DatasetListResponse = {
  datasets: DatasetRecord[];
};

export type FrameListResponse = {
  dataset: DatasetRecord;
  frames: FrameRecord[];
};

export type FrameDetailResponse = {
  frame: FrameDetailRecord;
};

export type InferenceRunRecord = {
  id: number;
  dataset_id: number;
  run_type: string;
  status: string;
  model_name: string;
  model_path: string;
  frame_count: number;
  processed_frame_count: number;
  detection_count: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

export type DetectionRecord = {
  id: number;
  inference_run_id: number;
  frame_id: string;
  class_name: string;
  confidence_score: number;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  created_at: string;
};

export type FrameDetectionsResponse = {
  frame_id: string;
  run: InferenceRunRecord;
  detections: DetectionRecord[];
};

export type ReviewStatus = "pending" | "approved" | "rejected";

export type DetectionStateSource = "original" | "corrected";

export type DetectionStateRecord = {
  detection_id: number;
  inference_run_id: number;
  frame_id: string;
  class_name: string;
  confidence_score: number;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  source: DetectionStateSource;
};

export type DetectionCorrectionRecord = {
  id: number;
  detection_id: number;
  review_status: ReviewStatus;
  created_at: string;
  updated_at: string;
  original_detection: DetectionStateRecord;
  corrected_detection: DetectionStateRecord | null;
  effective_detection: DetectionStateRecord | null;
};

export type FrameCorrectionsResponse = {
  frame_id: string;
  run: InferenceRunRecord;
  corrections: DetectionCorrectionRecord[];
};

export type SaveCorrectionRequest = {
  review_status: ReviewStatus;
  corrected_detection: {
    class_name: string;
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
};

export type DetectionCorrectionResponse = {
  correction: DetectionCorrectionRecord;
};
