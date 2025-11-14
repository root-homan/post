import React, { useId } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Region } from "./types";

type FocusOverlayProps = {
  regions: Region[];
  duration?: number;
  dimOpacity?: number;
  spotlightRadius?: number;
  startFrame?: number;
};

export const FocusOverlay: React.FC<FocusOverlayProps> = ({
  regions,
  duration = 30,
  dimOpacity = 0.55,
  spotlightRadius = 32,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const idBase = useId().replace(/[^a-zA-Z0-9-_]/g, "");
  const maskId = `${idBase}-mask`;
  const filterId = `${idBase}-blur`;

  // Pure function of frame: only show spotlight when regions exist AND frame is in range
  const hasRegions = regions.length > 0;

  const focusProgress = hasRegions
    ? interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: (t) => {
          // Smooth easing curve similar to spring
          const c1 = 1.70158;
          const c3 = c1 + 1;
          return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
        },
      })
    : 0;

  const dimStrength = focusProgress * dimOpacity;
  const spotlightIntensity = focusProgress;

  // If no regions or fully transparent, don't render anything
  if (!hasRegions || dimStrength < 0.01) {
    return null;
  }

  return (
    <div style={styles.container}>
      <svg style={styles.svg}>
        <defs>
          <filter
            id={filterId}
            x="-25%"
            y="-25%"
            width="150%"
            height="150%"
            filterUnits="objectBoundingBox"
            colorInterpolationFilters="sRGB"
          >
            <feGaussianBlur
              in="SourceGraphic"
              stdDeviation={spotlightRadius * 0.55}
              result="blurred"
            />
          </filter>
          <mask id={maskId}>
            {/* White rectangle covers entire screen */}
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {/* Black rectangles create "holes" where spotlight shines */}
            <g filter={`url(#${filterId})`}>
              {regions.map((region, index) => (
                <rect
                  key={index}
                  x={region.x}
                  y={region.y}
                  width={region.width}
                  height={region.height}
                  fill="black"
                  rx={spotlightRadius}
                />
              ))}
            </g>
          </mask>
        </defs>
        {/* Dark overlay with mask applied */}
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="black"
          mask={`url(#${maskId})`}
          opacity={dimStrength}
        />
      </svg>
      <div style={styles.highlights}>
        {regions.map((region, index) => (
          <div
            key={`highlight-${index}`}
            style={createHighlightStyles(
              region,
              spotlightIntensity,
              spotlightRadius
            )}
          />
        ))}
      </div>
    </div>
  );
};

// Styles
const styles = {
  container: {
    position: "absolute" as const,
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none" as const,
    zIndex: 1000,
  },
  svg: {
    width: "100%",
    height: "100%",
  },
  highlights: {
    position: "absolute" as const,
    inset: 0,
    pointerEvents: "none" as const,
    zIndex: 1001,
  },
};

const createHighlightStyles = (
  region: Region,
  intensity: number,
  radius: number
) => {
  const blurRadius = radius * 2.8;
  return {
    position: "absolute" as const,
    left: region.x,
    top: region.y,
    width: region.width,
    height: region.height,
    borderRadius: radius * 1.1,
    background:
      "radial-gradient(circle at 50% 40%, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0.15) 55%, rgba(255,255,255,0) 85%)",
    opacity: intensity,
    filter: `blur(${(radius * 0.4).toFixed(2)}px)`,
    boxShadow: `0 0 ${blurRadius}px rgba(255,255,255,${(
      0.22 * intensity
    ).toFixed(3)})`,
    mixBlendMode: "screen" as const,
    pointerEvents: "none" as const,
    transform: `scale(${(1 + 0.03 * intensity).toFixed(3)})`,
  };
};
