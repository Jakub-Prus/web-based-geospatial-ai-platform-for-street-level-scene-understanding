import { useEffect, useRef, type JSX } from "react";
import {
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
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import {
  buildPointCloudPositionBuffer,
  calculatePointCloudBounds,
  resolvePointCloudCameraPose,
} from "./pointCloud";
import type { PointCloudPointRecord } from "./types";

const CAMERA_FIELD_OF_VIEW_DEGREES = 55;
const MINIMUM_VIEWPORT_WIDTH = 320;
const MINIMUM_VIEWPORT_HEIGHT = 240;
const MAXIMUM_DEVICE_PIXEL_RATIO = 2;
const CAMERA_NEAR_PLANE = 0.01;
const CAMERA_FAR_PLANE = 5_000;
const GRID_SIZE_MULTIPLIER = 6;
const GRID_DIVISION_COUNT = 12;
const AXES_SIZE_MULTIPLIER = 1.5;
const POINT_SIZE_PIXELS = 2.2;
const CONTROL_DAMPING_FACTOR = 0.08;
const MINIMUM_DISTANCE_RATIO = 0.35;
const MAXIMUM_DISTANCE_RATIO = 8;
const BACKGROUND_COLOR = 0xf3f7f4;
const GRID_PRIMARY_COLOR = 0x9ac6bf;
const GRID_SECONDARY_COLOR = 0xddebe7;
const POINT_CLOUD_COLOR = 0x126c65;

type PointCloudCanvasProps = {
  points: PointCloudPointRecord[];
  ariaLabel: string;
  onError: (message: string) => void;
};

function resolveViewportSize(container: HTMLDivElement): {
  width: number;
  height: number;
} {
  const { width, height } = container.getBoundingClientRect();

  return {
    width: Math.max(MINIMUM_VIEWPORT_WIDTH, Math.round(width)),
    height: Math.max(MINIMUM_VIEWPORT_HEIGHT, Math.round(height)),
  };
}

export function PointCloudCanvas({
  points,
  ariaLabel,
  onError,
}: PointCloudCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || points.length === 0) {
      return;
    }

    let animationFrameId = 0;
    let resizeObserver: ResizeObserver | null = null;
    let resizeScene: (() => void) | null = null;

    try {
      const bounds = calculatePointCloudBounds(points);
      const cameraPose = resolvePointCloudCameraPose(bounds);
      const viewport = resolveViewportSize(container);

      const scene = new Scene();
      scene.background = new Color(BACKGROUND_COLOR);

      const camera = new PerspectiveCamera(
        CAMERA_FIELD_OF_VIEW_DEGREES,
        viewport.width / viewport.height,
        CAMERA_NEAR_PLANE,
        CAMERA_FAR_PLANE,
      );
      camera.position.set(
        cameraPose.position.x,
        cameraPose.position.y,
        cameraPose.position.z,
      );
      camera.lookAt(cameraPose.target.x, cameraPose.target.y, cameraPose.target.z);

      const renderer = new WebGLRenderer({
        antialias: true,
        alpha: true,
      });
      renderer.setPixelRatio(
        Math.min(window.devicePixelRatio || 1, MAXIMUM_DEVICE_PIXEL_RATIO),
      );
      renderer.setSize(viewport.width, viewport.height, false);
      renderer.domElement.className = "point-cloud-canvas__surface";
      renderer.domElement.setAttribute("aria-label", ariaLabel);
      container.replaceChildren(renderer.domElement);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = CONTROL_DAMPING_FACTOR;
      controls.target.set(
        cameraPose.target.x,
        cameraPose.target.y,
        cameraPose.target.z,
      );
      controls.minDistance = Math.max(
        bounds.radius * MINIMUM_DISTANCE_RATIO,
        CAMERA_NEAR_PLANE,
      );
      controls.maxDistance = Math.max(
        cameraPose.radius * MAXIMUM_DISTANCE_RATIO,
        controls.minDistance,
      );

      const geometry = new BufferGeometry();
      geometry.setAttribute(
        "position",
        new Float32BufferAttribute(buildPointCloudPositionBuffer(points), 3),
      );

      const pointMaterial = new PointsMaterial({
        color: POINT_CLOUD_COLOR,
        size: POINT_SIZE_PIXELS,
        sizeAttenuation: false,
      });

      const pointCloud = new Points(geometry, pointMaterial);
      scene.add(pointCloud);

      const gridSize = Math.max(bounds.radius * GRID_SIZE_MULTIPLIER, 1);
      const grid = new GridHelper(
        gridSize,
        GRID_DIVISION_COUNT,
        GRID_PRIMARY_COLOR,
        GRID_SECONDARY_COLOR,
      );
      scene.add(grid);

      const axes = new AxesHelper(Math.max(bounds.radius * AXES_SIZE_MULTIPLIER, 0.75));
      axes.position.copy(
        new Vector3(bounds.center.x, bounds.center.y, bounds.center.z),
      );
      scene.add(axes);

      const renderFrame = () => {
        controls.update();
        renderer.render(scene, camera);
        animationFrameId = window.requestAnimationFrame(renderFrame);
      };

      resizeScene = () => {
        if (containerRef.current === null) {
          return;
        }

        const nextViewport = resolveViewportSize(containerRef.current);
        camera.aspect = nextViewport.width / nextViewport.height;
        camera.updateProjectionMatrix();
        renderer.setSize(nextViewport.width, nextViewport.height, false);
      };

      if (typeof ResizeObserver !== "undefined") {
        resizeObserver = new ResizeObserver(() => {
          resizeScene?.();
        });
        resizeObserver.observe(container);
      } else {
        window.addEventListener("resize", resizeScene);
      }

      renderFrame();

      return () => {
        if (resizeObserver !== null) {
          resizeObserver.disconnect();
        } else if (resizeScene !== null) {
          window.removeEventListener("resize", resizeScene);
        }

        window.cancelAnimationFrame(animationFrameId);
        controls.dispose();
        geometry.dispose();
        pointMaterial.dispose();
        renderer.dispose();
        container.replaceChildren();
      };
    } catch {
      onError(
        "The Three.js scene could not be initialized in this browser context.",
      );

      return () => {
        if (resizeObserver !== null) {
          resizeObserver.disconnect();
        } else if (resizeScene !== null) {
          window.removeEventListener("resize", resizeScene);
        }

        window.cancelAnimationFrame(animationFrameId);
        container.replaceChildren();
      };
    }
  }, [ariaLabel, onError, points]);

  return <div ref={containerRef} className="point-cloud-canvas" />;
}
