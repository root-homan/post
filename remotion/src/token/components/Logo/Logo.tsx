import React from "react";
import { Ring } from "./AnimatedLogo";

interface LogoProps {
  size?: number;
  color?: string;
}

export const Logo: React.FC<LogoProps> = ({
  size = 100,
  color = "#000000",
}) => {
  const radius = size / 2;
  const strokeWidth = size * 0.1;
  const padding = strokeWidth;

  // Final offset for the collapsed state
  const offset = size * 0.45;

  // Calculate SVG dimensions
  const svgWidth = padding + radius + offset + radius + padding;
  const svgHeight = size + padding * 2;
  const centerY = radius + padding;

  // Calculate ring positions
  const leftCenterX = padding + radius;
  const rightCenterX = padding + radius + offset;

  return (
    <svg
      width={svgWidth}
      height={svgHeight}
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      style={styles.svg}
    >
      <Ring size={size} color={color} centerX={leftCenterX} centerY={centerY} />
      <Ring
        size={size}
        color={color}
        centerX={rightCenterX}
        centerY={centerY}
      />
    </svg>
  );
};

// Styles
const styles = {
  svg: {
    display: "block",
  } as React.CSSProperties,
};
