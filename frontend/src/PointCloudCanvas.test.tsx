import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { samplePointCloudResponse } from "./test/fixtures";

type MockState = {
  shouldThrowRenderer: boolean;
  disconnectCount: number;
  observeCount: number;
  disposeRendererCount: number;
  disposeControlsCount: number;
  disposeGeometryCount: number;
  disposeMaterialCount: number;
  renderCount: number;
  setSizeCount: number;
  setPixelRatioCount: number;
  updateControlsCount: number;
};

function createMockState(): MockState {
  return {
    shouldThrowRenderer: false,
    disconnectCount: 0,
    observeCount: 0,
    disposeRendererCount: 0,
    disposeControlsCount: 0,
    disposeGeometryCount: 0,
    disposeMaterialCount: 0,
    renderCount: 0,
    setSizeCount: 0,
    setPixelRatioCount: 0,
    updateControlsCount: 0,
  };
}

async function loadPointCloudCanvas(mockState: MockState) {
  vi.doMock("three", () => {
    class Color {
      constructor(public value: number) {}
    }

    class Scene {
      background: Color | null = null;
      add = () => undefined;
    }

    class PerspectiveCamera {
      aspect = 1;
      position = {
        set: () => undefined,
      };

      lookAt = () => undefined;
      updateProjectionMatrix = () => undefined;
    }

    class WebGLRenderer {
      domElement = document.createElement("canvas");

      constructor() {
        if (mockState.shouldThrowRenderer) {
          throw new Error("renderer failure");
        }
      }

      setPixelRatio = () => {
        mockState.setPixelRatioCount += 1;
      };
      setSize = () => {
        mockState.setSizeCount += 1;
      };
      render = () => {
        mockState.renderCount += 1;
      };
      dispose = () => {
        mockState.disposeRendererCount += 1;
      };
    }

    class BufferGeometry {
      setAttribute = () => undefined;
      dispose = () => {
        mockState.disposeGeometryCount += 1;
      };
    }

    class Float32BufferAttribute {
      constructor(
        public array: Float32Array,
        public itemSize: number,
      ) {}
    }

    class PointsMaterial {
      constructor(public options: object) {}

      dispose = () => {
        mockState.disposeMaterialCount += 1;
      };
    }

    class Points {
      constructor(
        public geometry: BufferGeometry,
        public material: PointsMaterial,
      ) {}
    }

    class GridHelper {
      constructor(
        public size: number,
        public divisions: number,
        public colorCenterLine: number,
        public colorGrid: number,
      ) {}
    }

    class AxesHelper {
      position = {
        copy: () => undefined,
      };

      constructor(public size: number) {}
    }

    class Vector3 {
      constructor(
        public x: number,
        public y: number,
        public z: number,
      ) {}
    }

    return {
      AxesHelper,
      BufferGeometry,
      Color,
      Float32BufferAttribute,
      GridHelper,
      PerspectiveCamera,
      Points,
      PointsMaterial,
      Scene,
      Vector3,
      WebGLRenderer,
    };
  });

  vi.doMock("three/examples/jsm/controls/OrbitControls.js", () => ({
    OrbitControls: class OrbitControls {
      enableDamping = false;
      dampingFactor = 0;
      minDistance = 0;
      maxDistance = 0;
      target = {
        set: () => undefined,
      };

      update = () => {
        mockState.updateControlsCount += 1;
      };
      dispose = () => {
        mockState.disposeControlsCount += 1;
      };

      constructor(
        public camera: object,
        public domElement: HTMLElement,
      ) {}
    },
  }));

  return import("./PointCloudCanvas");
}

describe("PointCloudCanvas", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserver {
        observe = () => undefined;
        disconnect = () => undefined;
      },
    );
    vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());

    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 640,
      height: 480,
      top: 0,
      left: 0,
      right: 640,
      bottom: 480,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("mounts a Three.js scene and disposes resources on unmount", async () => {
    const mockState = createMockState();
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserver {
        observe = () => {
          mockState.observeCount += 1;
        };
        disconnect = () => {
          mockState.disconnectCount += 1;
        };
      },
    );

    const { PointCloudCanvas } = await loadPointCloudCanvas(mockState);
    const points = samplePointCloudResponse.payload?.points ?? [];
    const onError = vi.fn();

    const { container, unmount } = render(
      <PointCloudCanvas
        points={points}
        ariaLabel="3D point-cloud view"
        onError={onError}
      />,
    );

    expect(container.querySelector("canvas")).not.toBeNull();
    expect(mockState.observeCount).toBeGreaterThan(0);
    expect(mockState.setPixelRatioCount).toBeGreaterThan(0);
    expect(mockState.setSizeCount).toBeGreaterThan(0);
    expect(mockState.renderCount).toBeGreaterThan(0);
    expect(mockState.updateControlsCount).toBeGreaterThan(0);
    expect(onError).not.toHaveBeenCalled();

    unmount();

    expect(mockState.disconnectCount).toBeGreaterThan(0);
    expect(mockState.disposeControlsCount).toBeGreaterThan(0);
    expect(mockState.disposeGeometryCount).toBeGreaterThan(0);
    expect(mockState.disposeMaterialCount).toBeGreaterThan(0);
    expect(mockState.disposeRendererCount).toBeGreaterThan(0);
  });

  it("reports an understandable error when WebGL renderer setup fails", async () => {
    const mockState = createMockState();
    mockState.shouldThrowRenderer = true;

    const { PointCloudCanvas } = await loadPointCloudCanvas(mockState);
    const onError = vi.fn();

    render(
      <PointCloudCanvas
        points={samplePointCloudResponse.payload?.points ?? []}
        ariaLabel="3D point-cloud view"
        onError={onError}
      />,
    );

    expect(onError).toHaveBeenCalledWith(
      "The Three.js scene could not be initialized in this browser context.",
    );
  });
});
