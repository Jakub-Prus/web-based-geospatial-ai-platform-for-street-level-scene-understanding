import type { PointCloudPointRecord } from "./types";

const POSITION_COMPONENTS_PER_POINT = 3;
const INITIAL_MINIMUM = Number.POSITIVE_INFINITY;
const INITIAL_MAXIMUM = Number.NEGATIVE_INFINITY;
const CAMERA_PADDING_MULTIPLIER = 2.4;
const CAMERA_HORIZONTAL_OFFSET_RATIO = 0.52;
const CAMERA_VERTICAL_OFFSET_RATIO = 0.35;
const MINIMUM_CAMERA_RADIUS = 0.5;

export type PointCloudBounds = {
  center: PointCloudPointRecord;
  radius: number;
  minZ: number;
  maxZ: number;
};

export type PointCloudCameraPose = {
  target: PointCloudPointRecord;
  position: PointCloudPointRecord;
  radius: number;
};

export function buildPointCloudPositionBuffer(
  points: PointCloudPointRecord[],
): Float32Array {
  const buffer = new Float32Array(points.length * POSITION_COMPONENTS_PER_POINT);

  points.forEach((point, index) => {
    const offset = index * POSITION_COMPONENTS_PER_POINT;
    buffer[offset] = point.x;
    buffer[offset + 1] = point.y;
    buffer[offset + 2] = point.z;
  });

  return buffer;
}

export function calculatePointCloudBounds(
  points: PointCloudPointRecord[],
): PointCloudBounds {
  if (points.length === 0) {
    return {
      center: { x: 0, y: 0, z: 0 },
      radius: MINIMUM_CAMERA_RADIUS,
      minZ: 0,
      maxZ: 0,
    };
  }

  let minX = INITIAL_MINIMUM;
  let minY = INITIAL_MINIMUM;
  let minZ = INITIAL_MINIMUM;
  let maxX = INITIAL_MAXIMUM;
  let maxY = INITIAL_MAXIMUM;
  let maxZ = INITIAL_MAXIMUM;

  points.forEach((point) => {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    minZ = Math.min(minZ, point.z);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
    maxZ = Math.max(maxZ, point.z);
  });

  const sizeX = maxX - minX;
  const sizeY = maxY - minY;
  const sizeZ = maxZ - minZ;
  const radius = Math.max(
    MINIMUM_CAMERA_RADIUS,
    Math.max(sizeX, sizeY, sizeZ) * 0.5,
  );

  return {
    center: {
      x: minX + sizeX * 0.5,
      y: minY + sizeY * 0.5,
      z: minZ + sizeZ * 0.5,
    },
    radius,
    minZ,
    maxZ,
  };
}

export function resolvePointCloudCameraPose(
  bounds: PointCloudBounds,
): PointCloudCameraPose {
  const paddedRadius = Math.max(
    MINIMUM_CAMERA_RADIUS,
    bounds.radius * CAMERA_PADDING_MULTIPLIER,
  );

  return {
    target: bounds.center,
    radius: paddedRadius,
    position: {
      x: bounds.center.x + paddedRadius * CAMERA_HORIZONTAL_OFFSET_RATIO,
      y: bounds.center.y + paddedRadius * CAMERA_VERTICAL_OFFSET_RATIO,
      z: bounds.maxZ + paddedRadius,
    },
  };
}
