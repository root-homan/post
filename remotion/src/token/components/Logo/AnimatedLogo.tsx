import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface RingProps {
  size: number;
  color?: string;
  centerX: number;
  centerY: number;
}

export const Ring: React.FC<RingProps> = ({
  size,
  color = "#000000",
  centerX,
  centerY,
}) => {
  const radius = size / 2;
  // Maintain the thickness ratio from the original logo (10% of diameter)
  const strokeWidth = size * 0.1;

  return (
    <circle
      cx={centerX}
      cy={centerY}
      r={radius - strokeWidth / 2}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
    />
  );
};

interface AnimatedLogoProps {
  size?: number;
  color?: string;
  /**
   * Duration of the collapse animation in frames
   */
  durationInFrames?: number;
  /**
   * Delay before animation starts in frames
   */
  delayFrames?: number;
  /**
   * Duration of the fade-in animation in frames
   */
  fadeInDurationInFrames?: number;
}

export const AnimatedLogo: React.FC<AnimatedLogoProps> = ({
  size = 100,
  color = "#000000",
  durationInFrames = 24,
  delayFrames = 0,
  fadeInDurationInFrames = 12,
}) => {
  const radius = size / 2;
  const strokeWidth = size * 0.1;
  const padding = strokeWidth;

  // Final offset for the collapsed state (matches original Logo)
  const finalOffset = size * 0.45;

  // Starting offset for separated rings (fully separated with some gap)
  const startOffset = size * 1.5;

  // Calculate how much extra separation there is at the start
  // Each ring moves half of this distance towards the center
  const extraSeparation = (startOffset - finalOffset) / 2;

  // To ensure the left ring isn't cut off, we need extra space on the left
  // The left ring will move left by extraSeparation from its final position
  // So we need to add extraSeparation to all x-coordinates
  const xOffset = extraSeparation;

  // Final positions (where rings end up) - shifted to accommodate starting positions
  const leftFinalX = padding + radius + xOffset;
  const rightFinalX = padding + radius + finalOffset + xOffset;

  // Starting positions (where rings begin, separated)
  const leftStartX = leftFinalX - extraSeparation; // = padding + radius
  const rightStartX = rightFinalX + extraSeparation; // = padding + radius + startOffset

  // Calculate SVG dimensions based on the maximum possible extent
  // Right ring at start has the rightmost edge at (rightStartX + radius)
  const svgWidth = rightStartX + radius + padding;
  const svgHeight = size + padding * 2;
  const centerY = radius + padding;

  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade-in animation (snappy spring for opacity)
  const fadeInProgress = spring({
    frame: Math.max(0, frame - delayFrames),
    fps,
    config: {
      damping: 35,
      stiffness: 400,
      mass: 0.5,
    },
    durationInFrames: fadeInDurationInFrames,
  });

  const opacity = interpolate(fadeInProgress, [0, 1], [0, 1]);

  // Collapse animation starts when opacity reaches ~0.5
  // Calculate when the spring reaches 0.5 (approximately half the fade duration)
  const collapseStartOffset = fadeInDurationInFrames * 0.2; // Start earlier in the fade
  const collapseStartFrame = delayFrames + collapseStartOffset;
  const collapseProgress = spring({
    frame: Math.max(0, frame - collapseStartFrame),
    fps,
    config: {
      damping: 38, // Slightly lower damping for quicker settling
      stiffness: 550, // Much higher stiffness for faster motion
      mass: 0.12, // Lower mass for even quicker response
    },
    durationInFrames: Math.max(8, Math.round(durationInFrames * 0.45)), // reduce duration for higher speed
  });

  // Both rings move towards each other
  const leftCenterX = interpolate(
    collapseProgress,
    [0, 1],
    [leftStartX, leftFinalX]
  );

  const rightCenterX = interpolate(
    collapseProgress,
    [0, 1],
    [rightStartX, rightFinalX]
  );

  return (
    <svg
      width={svgWidth}
      height={svgHeight}
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      style={styles.svg}
    >
      {/* Rings with fade-in */}
      <g opacity={opacity}>
        <Ring
          size={size}
          color={color}
          centerX={leftCenterX}
          centerY={centerY}
        />
        <Ring
          size={size}
          color={color}
          centerX={rightCenterX}
          centerY={centerY}
        />
      </g>
    </svg>
  );
};

// Styles
const styles = {
  svg: {
    display: "block",
  } as React.CSSProperties,
};
