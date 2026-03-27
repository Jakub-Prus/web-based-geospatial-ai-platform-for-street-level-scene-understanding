#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly ENV_TEMPLATE_PATH="${REPO_ROOT}/.env.example"
readonly ENV_FILE_PATH="${REPO_ROOT}/.env"
readonly DATA_RAW_DIR="${REPO_ROOT}/data/raw"
readonly MODELS_DIR="${DATA_RAW_DIR}/models"
readonly YOLO_MODEL_PATH="${MODELS_DIR}/yolo11n.pt"
readonly MIDAS_MODEL_PATH="${MODELS_DIR}/dpt_swin2_tiny_256.pt"
readonly A2D2_PREVIEW_ARCHIVE_PATH="${DATA_RAW_DIR}/a2d2-preview.tar"
readonly A2D2_SUBSET_DIR="${DATA_RAW_DIR}/a2d2-subset"
readonly DATASET_LOAD_ENDPOINT_PATH="/datasets/load"
readonly HEALTH_ENDPOINT_PATH="/health"
readonly DOCKER_COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
readonly DEFAULT_FRONTEND_PORT="3000"
readonly DEFAULT_FASTAPI_PORT="8000"
readonly DEFAULT_BRIDGE_PORT="8080"
readonly DEFAULT_START_LOCAL_RUN_DETECTION="1"
readonly DEFAULT_A2D2_SEQUENCE="20190401_121727"
readonly DEFAULT_A2D2_CAMERA="cam_front_right"
readonly DEFAULT_A2D2_FRAME_COUNT="20"
readonly DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS="180"
readonly DEFAULT_HEALTHCHECK_INTERVAL_SECONDS="2"
readonly YOLO_MODEL_URL="https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt"
readonly MIDAS_MODEL_URL="https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_swin2_tiny_256.pt"
readonly A2D2_PREVIEW_ARCHIVE_URL="https://aev-autonomous-driving-dataset.s3.eu-central-1.amazonaws.com/a2d2-preview.tar"
readonly CURL_ERROR_STATUS="000"
readonly HTTP_STATUS_OK="200"
readonly HTTP_STATUS_CREATED="201"
readonly HTTP_STATUS_NOT_FOUND="404"
readonly DETECTION_RUN_STATUS_COMPLETED="completed"
readonly DETECTION_RUN_STATUS_FAILED="failed"
readonly DETECTION_RUN_STATUS_EMPTY="empty"
readonly DETECTION_RUN_STATUS_RUNNING="running"

TEMP_FILES=()
LOADED_DATASET_ID=""
LOADED_FRAME_COUNT="0"

log() {
  printf '[start_local] %s\n' "$1"
}

fail() {
  printf '[start_local] ERROR: %s\n' "$1" >&2
  exit 1
}

register_temp_file() {
  TEMP_FILES+=("$1")
}

cleanup_temp_files() {
  local temp_file
  for temp_file in "${TEMP_FILES[@]:-}"; do
    if [[ -n "${temp_file}" && -f "${temp_file}" ]]; then
      rm -f "${temp_file}"
    fi
  done
}

trap cleanup_temp_files EXIT

extract_json_number_field() {
  local json_payload="$1"
  local field_name="$2"

  printf '%s' "${json_payload}" \
    | grep -oE "\"${field_name}\"[[:space:]]*:[[:space:]]*[0-9]+" \
    | head -n 1 \
    | grep -oE "[0-9]+" || true
}

extract_json_string_field() {
  local json_payload="$1"
  local field_name="$2"

  printf '%s' "${json_payload}" \
    | grep -oE "\"${field_name}\"[[:space:]]*:[[:space:]]*\"[^\"]+\"" \
    | head -n 1 \
    | sed -E "s/\"${field_name}\"[[:space:]]*:[[:space:]]*\"([^\"]+)\"/\\1/" || true
}

env_var_is_truthy() {
  local value="${1:-}"

  case "${value,,}" in
    1|true|yes|on)
      return 0
      ;;
    0|false|no|off|"")
      return 1
      ;;
    *)
      fail "Unsupported boolean value '${value}' for START_LOCAL_RUN_DETECTION."
      ;;
  esac
}

print_help() {
  cat <<'EOF'
Usage: bash ./scripts/start_local.sh

Bootstraps the local demo environment by:
1. Creating .env from .env.example if needed
2. Downloading required model files
3. Downloading the A2D2 preview archive if the extracted subset is missing
4. Extracting the default A2D2 subset if needed
5. Starting Docker Compose in detached mode
6. Waiting for the frontend, FastAPI, and .NET bridge health endpoints
7. Loading the dataset through FastAPI

Environment overrides:
  FRONTEND_PORT
  FASTAPI_PORT
  BRIDGE_PORT
  START_LOCAL_RUN_DETECTION
  A2D2_SEQUENCE
  A2D2_CAMERA
  A2D2_FRAME_COUNT
  START_LOCAL_TIMEOUT_SECONDS
  START_LOCAL_POLL_INTERVAL_SECONDS
EOF
}

ensure_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command '${command_name}' was not found."
  fi
}

ensure_prerequisites() {
  ensure_command "docker"
  ensure_command "curl"
  ensure_command "tar"
  ensure_command "cp"

  if ! docker compose version >/dev/null 2>&1; then
    fail "Docker Compose v2 is required. 'docker compose version' failed."
  fi

  if [[ ! -f "${DOCKER_COMPOSE_FILE}" ]]; then
    fail "docker-compose.yml was not found at ${DOCKER_COMPOSE_FILE}."
  fi
}

ensure_env_file() {
  if [[ -f "${ENV_FILE_PATH}" ]]; then
    log "Using existing .env file."
    return
  fi

  if [[ ! -f "${ENV_TEMPLATE_PATH}" ]]; then
    fail ".env.example was not found at ${ENV_TEMPLATE_PATH}."
  fi

  cp "${ENV_TEMPLATE_PATH}" "${ENV_FILE_PATH}"
  log "Created .env from .env.example."
}

load_env_file() {
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE_PATH}"
  set +a
}

download_if_missing() {
  local url="$1"
  local output_path="$2"

  if [[ -f "${output_path}" ]]; then
    log "Skipping existing file: ${output_path}"
    return
  fi

  mkdir -p "$(dirname "${output_path}")"
  log "Downloading ${url}"
  curl --fail --location --output "${output_path}" "${url}"
}

ensure_assets() {
  download_if_missing "${YOLO_MODEL_URL}" "${YOLO_MODEL_PATH}"
  download_if_missing "${MIDAS_MODEL_URL}" "${MIDAS_MODEL_PATH}"
}

subset_has_files() {
  [[ -d "${A2D2_SUBSET_DIR}" ]] && find "${A2D2_SUBSET_DIR}" -type f | grep -q .
}

extract_subset_if_missing() {
  local a2d2_sequence="${A2D2_SEQUENCE:-${DEFAULT_A2D2_SEQUENCE}}"
  local a2d2_camera="${A2D2_CAMERA:-${DEFAULT_A2D2_CAMERA}}"
  local a2d2_frame_count="${A2D2_FRAME_COUNT:-${DEFAULT_A2D2_FRAME_COUNT}}"
  local archive_listing_file
  local selected_entries_file
  local camera_prefix
  local bus_signals_path
  local entry
  local base_name
  local json_path

  if subset_has_files; then
    log "Skipping subset extraction because ${A2D2_SUBSET_DIR} already contains files."
    return
  fi

  download_if_missing "${A2D2_PREVIEW_ARCHIVE_URL}" "${A2D2_PREVIEW_ARCHIVE_PATH}"

  archive_listing_file="$(mktemp)"
  selected_entries_file="$(mktemp)"
  register_temp_file "${archive_listing_file}"
  register_temp_file "${selected_entries_file}"

  tar -tf "${A2D2_PREVIEW_ARCHIVE_PATH}" > "${archive_listing_file}"

  camera_prefix="camera_lidar/${a2d2_sequence}/camera/${a2d2_camera}/"
  mapfile -t matching_pngs < <(
    grep -E "^${camera_prefix}.*\.png$" "${archive_listing_file}" | sort | head -n "${a2d2_frame_count}"
  )

  if [[ "${#matching_pngs[@]}" -eq 0 ]]; then
    fail "No PNG frames were found for sequence '${a2d2_sequence}' and camera '${a2d2_camera}'."
  fi

  : > "${selected_entries_file}"
  for entry in "${matching_pngs[@]}"; do
    printf '%s\n' "${entry}" >> "${selected_entries_file}"
    base_name="$(basename "${entry}" .png)"
    json_path="${camera_prefix}${base_name}.json"
    if grep -Fxq "${json_path}" "${archive_listing_file}"; then
      printf '%s\n' "${json_path}" >> "${selected_entries_file}"
    fi
  done

  bus_signals_path="camera_lidar/${a2d2_sequence}/bus_signals_${a2d2_sequence}.json"
  if grep -Fxq "${bus_signals_path}" "${archive_listing_file}"; then
    printf '%s\n' "${bus_signals_path}" >> "${selected_entries_file}"
  fi

  mkdir -p "${A2D2_SUBSET_DIR}"
  tar -xf "${A2D2_PREVIEW_ARCHIVE_PATH}" -C "${A2D2_SUBSET_DIR}" -T "${selected_entries_file}"
  log "Extracted ${#matching_pngs[@]} A2D2 frames into ${A2D2_SUBSET_DIR}."
}

wait_for_endpoint() {
  local service_name="$1"
  local endpoint_url="$2"
  local timeout_seconds="${START_LOCAL_TIMEOUT_SECONDS:-${DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS}}"
  local poll_interval_seconds="${START_LOCAL_POLL_INTERVAL_SECONDS:-${DEFAULT_HEALTHCHECK_INTERVAL_SECONDS}}"
  local start_time
  local elapsed_seconds

  log "Waiting for ${service_name} at ${endpoint_url}"
  start_time="$(date +%s)"

  while true; do
    if curl --silent --show-error --fail "${endpoint_url}" >/dev/null; then
      log "${service_name} is ready."
      return
    fi

    elapsed_seconds="$(( $(date +%s) - start_time ))"
    if (( elapsed_seconds >= timeout_seconds )); then
      fail "${service_name} did not become ready within ${timeout_seconds} seconds."
    fi

    sleep "${poll_interval_seconds}"
  done
}

start_compose_stack() {
  log "Starting Docker Compose stack."
  (
    cd "${REPO_ROOT}"
    docker compose up --detach --build
  )
}

load_dataset() {
  local fastapi_base_url="$1"
  local dataset_load_url="${fastapi_base_url}${DATASET_LOAD_ENDPOINT_PATH}"
  local response_file
  local http_status
  local response_body

  log "Loading dataset through ${dataset_load_url}"
  response_file="$(mktemp)"
  register_temp_file "${response_file}"
  http_status="$(
    curl --silent --show-error \
      --output "${response_file}" \
      --write-out "%{http_code}" \
      --request POST \
      --header "Content-Type: application/json" \
      --data '{}' \
      "${dataset_load_url}" || printf '%s' "${CURL_ERROR_STATUS}"
  )"
  if [[ "${http_status}" != "${HTTP_STATUS_OK}" && "${http_status}" != "${HTTP_STATUS_CREATED}" ]]; then
    fail "Dataset load failed with status ${http_status}: $(cat "${response_file}")"
  fi
  response_body="$(tr -d '\r\n' < "${response_file}")"
  LOADED_DATASET_ID="$(extract_json_number_field "${response_body}" "id")"
  LOADED_FRAME_COUNT="$(extract_json_number_field "${response_body}" "loaded_frame_count")"

  if [[ -z "${LOADED_DATASET_ID}" || -z "${LOADED_FRAME_COUNT}" ]]; then
    fail "Dataset load succeeded but the response could not be parsed: ${response_body}"
  fi

  log "Dataset load request completed."
  log "Loaded dataset ${LOADED_DATASET_ID} with ${LOADED_FRAME_COUNT} frames."
}

fetch_first_frame_id() {
  local fastapi_base_url="$1"
  local dataset_id="$2"
  local frames_url="${fastapi_base_url}/datasets/${dataset_id}/frames"
  local response_file
  local http_status
  local response_body

  response_file="$(mktemp)"
  register_temp_file "${response_file}"
  http_status="$(
    curl --silent --show-error \
      --output "${response_file}" \
      --write-out "%{http_code}" \
      "${frames_url}" || printf '%s' "${CURL_ERROR_STATUS}"
  )"

  if [[ "${http_status}" != "${HTTP_STATUS_OK}" ]]; then
    fail "Frame lookup failed with status ${http_status}: $(cat "${response_file}")"
  fi

  response_body="$(tr -d '\r\n' < "${response_file}")"
  extract_json_string_field "${response_body}" "frame_id"
}

fetch_existing_detection_run_status() {
  local fastapi_base_url="$1"
  local dataset_id="$2"
  local frame_id="$3"
  local detections_url="${fastapi_base_url}/datasets/${dataset_id}/frames/${frame_id}/detections"
  local response_file
  local http_status
  local response_body
  local run_status

  response_file="$(mktemp)"
  register_temp_file "${response_file}"
  http_status="$(
    curl --silent --show-error \
      --output "${response_file}" \
      --write-out "%{http_code}" \
      "${detections_url}" || printf '%s' "${CURL_ERROR_STATUS}"
  )"

  case "${http_status}" in
    "${HTTP_STATUS_OK}")
      response_body="$(tr -d '\r\n' < "${response_file}")"
      run_status="$(extract_json_string_field "${response_body}" "status")"
      if [[ -z "${run_status}" ]]; then
        fail "Unable to parse the existing detection-run status: ${response_body}"
      fi
      printf '%s' "${run_status}"
      return 0
      ;;
    "${HTTP_STATUS_NOT_FOUND}")
      return 0
      ;;
    *)
      fail "Detection-run check failed with status ${http_status}: $(cat "${response_file}")"
      ;;
  esac
}

trigger_detection_run_if_needed() {
  local fastapi_base_url="$1"
  local detection_run_enabled="${START_LOCAL_RUN_DETECTION:-${DEFAULT_START_LOCAL_RUN_DETECTION}}"
  local frame_id
  local run_url
  local response_file
  local http_status
  local response_body
  local run_status
  local detection_count
  local existing_run_status

  if ! env_var_is_truthy "${detection_run_enabled}"; then
    log "Skipping automatic detection run because START_LOCAL_RUN_DETECTION=${detection_run_enabled}."
    return
  fi

  if [[ "${LOADED_FRAME_COUNT}" == "0" ]]; then
    log "Skipping automatic detection run because the loaded dataset has no frames."
    return
  fi

  frame_id="$(fetch_first_frame_id "${fastapi_base_url}" "${LOADED_DATASET_ID}")"
  if [[ -z "${frame_id}" ]]; then
    fail "Unable to determine a frame id for dataset ${LOADED_DATASET_ID}."
  fi

  existing_run_status="$(
    fetch_existing_detection_run_status "${fastapi_base_url}" "${LOADED_DATASET_ID}" "${frame_id}"
  )"
  case "${existing_run_status}" in
    "")
      ;;
    "${DETECTION_RUN_STATUS_COMPLETED}"|"${DETECTION_RUN_STATUS_RUNNING}")
      log "Skipping automatic detection run because dataset ${LOADED_DATASET_ID} already has a detection run with status ${existing_run_status}."
      return
      ;;
    "${DETECTION_RUN_STATUS_EMPTY}"|"${DETECTION_RUN_STATUS_FAILED}")
      log "Existing detection run status is ${existing_run_status}; triggering a fresh run."
      ;;
    *)
      fail "Unsupported detection-run status '${existing_run_status}' returned for dataset ${LOADED_DATASET_ID}."
      ;;
  esac

  run_url="${fastapi_base_url}/datasets/${LOADED_DATASET_ID}/runs/detect"
  response_file="$(mktemp)"
  register_temp_file "${response_file}"

  log "Triggering Slice 6 detection run for dataset ${LOADED_DATASET_ID}."
  http_status="$(
    curl --silent --show-error \
      --output "${response_file}" \
      --write-out "%{http_code}" \
      --request POST \
      --header "Content-Type: application/json" \
      --data '{}' \
      "${run_url}" || printf '%s' "${CURL_ERROR_STATUS}"
  )"

  if [[ "${http_status}" != "${HTTP_STATUS_CREATED}" ]]; then
    fail "Detection run failed with status ${http_status}: $(cat "${response_file}")"
  fi

  response_body="$(tr -d '\r\n' < "${response_file}")"
  run_status="$(extract_json_string_field "${response_body}" "status")"
  detection_count="$(extract_json_number_field "${response_body}" "detection_count")"

  if [[ -z "${run_status}" ]]; then
    fail "Detection run succeeded but the response could not be parsed: ${response_body}"
  fi

  if [[ "${run_status}" == "${DETECTION_RUN_STATUS_FAILED}" ]]; then
    fail "Detection run completed with status '${run_status}': ${response_body}"
  fi

  if [[ "${run_status}" == "${DETECTION_RUN_STATUS_EMPTY}" ]]; then
    log "Detection run completed with no stored detections. Frames may still show empty-state messaging."
    return
  fi

  log "Detection run completed with status ${run_status} and ${detection_count:-0} stored detections."
}

main() {
  local frontend_port
  local fastapi_port
  local bridge_port
  local frontend_base_url
  local fastapi_base_url
  local bridge_base_url

  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    print_help
    exit 0
  fi

  if [[ $# -gt 0 ]]; then
    fail "Unknown argument: $1"
  fi

  ensure_prerequisites
  ensure_env_file
  load_env_file
  ensure_assets
  extract_subset_if_missing
  start_compose_stack

  frontend_port="${FRONTEND_PORT:-${DEFAULT_FRONTEND_PORT}}"
  fastapi_port="${FASTAPI_PORT:-${DEFAULT_FASTAPI_PORT}}"
  bridge_port="${BRIDGE_PORT:-${DEFAULT_BRIDGE_PORT}}"

  frontend_base_url="http://localhost:${frontend_port}"
  fastapi_base_url="http://localhost:${fastapi_port}"
  bridge_base_url="http://localhost:${bridge_port}"

  wait_for_endpoint "FastAPI" "${fastapi_base_url}${HEALTH_ENDPOINT_PATH}"
  wait_for_endpoint ".NET bridge" "${bridge_base_url}${HEALTH_ENDPOINT_PATH}"
  wait_for_endpoint "frontend" "${frontend_base_url}${HEALTH_ENDPOINT_PATH}"
  load_dataset "${fastapi_base_url}"
  trigger_detection_run_if_needed "${fastapi_base_url}"

  cat <<EOF

Local stack is ready.

Frontend: ${frontend_base_url}
FastAPI: ${fastapi_base_url}
.NET bridge: ${bridge_base_url}

To stop the stack:
  docker compose down
EOF
}

main "$@"
