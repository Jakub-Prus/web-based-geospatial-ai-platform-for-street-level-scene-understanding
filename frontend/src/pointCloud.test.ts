import { describe, expect, it } from "vitest";

import {
  buildPointCloudPositionBuffer,
  calculatePointCloudBounds,
  resolvePointCloudCameraPose,
} from "./pointCloud";
import { samplePointCloudResponse } from "./test/fixtures";

const samplePoints = samplePointCloudResponse.payload?.points ?? [];

describe("buildPointCloudPositionBuffer", () => {
  it("flattens XYZ points into a Float32 buffer", () => {
    expect(Array.from(buildPointCloudPositionBuffer(samplePoints))).toEqual(
      expect.arrayContaining([
        -0.375,
        0.125,
        1,
        -0.125,
        -0.125,
        1.5,
        0.25,
      ]),
    );
    expect(buildPointCloudPositionBuffer(samplePoints)[7]).toBeCloseTo(-0.2);
    expect(buildPointCloudPositionBuffer(samplePoints)[8]).toBeCloseTo(2.2);
  });
});

describe("calculatePointCloudBounds", () => {
  it("returns the center point and radius for a cloud", () => {
    expect(calculatePointCloudBounds(samplePoints)).toEqual({
      center: {
        x: -0.0625,
        y: -0.037500000000000006,
        z: 1.6,
      },
      radius: 0.6000000000000001,
      minZ: 1,
      maxZ: 2.2,
    });
  });
});

describe("resolvePointCloudCameraPose", () => {
  it("positions the camera above and behind the point cloud center", () => {
    const pose = resolvePointCloudCameraPose(calculatePointCloudBounds(samplePoints));

    expect(pose.target).toEqual({
      x: -0.0625,
      y: -0.037500000000000006,
      z: 1.6,
    });
    expect(pose.radius).toBeCloseTo(1.44);
    expect(pose.position.x).toBeCloseTo(0.6863);
    expect(pose.position.y).toBeCloseTo(0.4665);
    expect(pose.position.z).toBeCloseTo(3.64);
  });
});
