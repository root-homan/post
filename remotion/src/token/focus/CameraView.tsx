import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Region } from "./types";

type CameraViewProps = {
  regions: Region[];
  duration?: number;
  children: React.ReactNode;
};

export const CameraView: React.FC<CameraViewProps> = ({
  regions,
  duration = 30,
  children,
}) => {
  const frame = useCurrentFrame();
  const { width: videoWidth, height: videoHeight, fps } = useVideoConfig();

  // Only center camera if there's exactly one region
  const shouldCenter = regions.length === 1;
  const targetRegion = shouldCenter ? regions[0] : null;

  // Calculate the center point of the target region
  let targetX = 0;
  let targetY = 0;

  if (targetRegion) {
    const regionCenterX = targetRegion.x + targetRegion.width / 2;
    const regionCenterY = targetRegion.y + targetRegion.height / 2;

    // Calculate how much we need to move to center the region
    targetX = videoWidth / 2 - regionCenterX;
    targetY = videoHeight / 2 - regionCenterY;
  }

  // Animate the camera movement
  const translateX = spring({
    frame,
    fps,
    config: {
      damping: 200,
      mass: 0.5,
    },
    durationInFrames: duration,
    from: 0,
    to: targetX,
  });

  const translateY = spring({
    frame,
    fps,
    config: {
      damping: 200,
      mass: 0.5,
    },
    durationInFrames: duration,
    from: 0,
    to: targetY,
  });

  return (
    <div
      style={{
        ...styles.container,
        transform: `translate(${translateX}px, ${translateY}px)`,
      }}
    >
      {children}
    </div>
  );
};

// Styles
const styles = {
  container: {
    width: "100%",
    height: "100%",
    transition: "transform 0.3s ease-out",
  },
};
