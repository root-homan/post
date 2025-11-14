import React from "react";

/**
 * Simple Focus System
 * -------------------
 * 
 * Just pass rectangles. That's it.
 * - If rectangles exist, dim everything and spotlight those regions
 * - If one rectangle, camera centers on it
 * - No registration, no complexity
 */

export interface FocusRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SimpleFocusOverlayProps {
  /** Rectangles to spotlight (relative to container) */
  regions: FocusRect[];
  /** 0-1, controls dim/spotlight intensity */
  progress: number;
}

const DIM_OPACITY = 0.65;
const HIGHLIGHT_EDGE_SOFTNESS = 28;

export const SimpleFocusOverlay: React.FC<SimpleFocusOverlayProps> = ({
  regions,
  progress,
}) => {
  if (progress <= 0 || regions.length === 0) {
    return null;
  }

  return (
    <>
      {/* Full-screen dim */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          backgroundColor: `rgba(0, 0, 0, ${(DIM_OPACITY * progress).toFixed(3)})`,
          zIndex: 10,
          transition: "background-color 200ms ease",
        }}
      />
      {/* Spotlights */}
      {regions.map((region, index) => (
        <div
          key={index}
          style={{
            position: "fixed",
            left: `${region.x}px`,
            top: `${region.y}px`,
            width: `${region.width}px`,
            height: `${region.height}px`,
            borderRadius: "24px",
            background:
              "radial-gradient(ellipse at center, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.03) 60%, transparent 100%)",
            boxShadow: `0 0 ${HIGHLIGHT_EDGE_SOFTNESS * 3}px ${HIGHLIGHT_EDGE_SOFTNESS}px rgba(255,255,255,${(0.15 * progress).toFixed(3)})`,
            opacity: progress,
            pointerEvents: "none",
            zIndex: 11,
            mixBlendMode: "lighten",
            transition: "opacity 200ms ease",
          }}
        />
      ))}
    </>
  );
};

export interface SimpleFocusCameraProps {
  /** Single region to center on (if multiple, camera stays neutral) */
  region: FocusRect | null;
  /** Container bounds for calculating center */
  containerWidth: number;
  containerHeight: number;
  /** 0-1 animation progress */
  progress: number;
  children: React.ReactNode;
}

const CAMERA_SCALE_DELTA = 0.08;

export const SimpleFocusCamera: React.FC<SimpleFocusCameraProps> = ({
  region,
  containerWidth,
  containerHeight,
  progress,
  children,
}) => {
  let translateX = 0;
  let translateY = 0;
  let scale = 1;

  if (region && progress > 0) {
    const containerCenterX = containerWidth / 2;
    const containerCenterY = containerHeight / 2;
    const regionCenterX = region.x + region.width / 2;
    const regionCenterY = region.y + region.height / 2;

    translateX = (containerCenterX - regionCenterX) * progress;
    translateY = (containerCenterY - regionCenterY) * progress;
    scale = 1 + CAMERA_SCALE_DELTA * progress;
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `translate3d(${translateX.toFixed(3)}px, ${translateY.toFixed(3)}px, 0) scale(${scale.toFixed(3)})`,
        willChange: "transform",
        transition: "transform 520ms cubic-bezier(0.22, 0.61, 0.36, 1)",
      }}
    >
      {children}
    </div>
  );
};

