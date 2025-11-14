import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { AnimatedLogo } from "./AnimatedLogo";

export const AnimatedLogoPreview: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const delayFrames = 10;
  const fadeInDurationInFrames = 12;

  // Fade-in animation for background (same as logo rings)
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

  const backgroundOpacity = interpolate(fadeInProgress, [0, 1], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        ...styles.container,
        backgroundColor: `rgba(255, 255, 255, ${backgroundOpacity})`,
      }}
    >
      <AnimatedLogo 
        size={200} 
        color="#000000"
        durationInFrames={24}
        delayFrames={delayFrames}
        fadeInDurationInFrames={fadeInDurationInFrames}
      />
    </AbsoluteFill>
  );
};

// Styles
const styles = {
  container: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  } as React.CSSProperties,
};

