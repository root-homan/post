import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, random } from "remotion";
import { Logo } from "../Logo/Logo";

export const SceneBackground: React.FC = () => {
  const frame = useCurrentFrame();

  // Generate noise pattern that changes every frame
  const noisePattern1 = useMemo(() => {
    const baseFreq = 0.85 + random(`freq1-${frame}`) * 0.2;
    const seed = frame * 10;
    return `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter1-${frame}'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='${baseFreq}' numOctaves='4' seed='${seed}'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter1-${frame})'/%3E%3C/svg%3E")`;
  }, [frame]);

  const noisePattern2 = useMemo(() => {
    const baseFreq = 0.55 + random(`freq2-${frame}`) * 0.15;
    const seed = frame * 15 + 1000;
    return `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter2-${frame}'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='${baseFreq}' numOctaves='3' seed='${seed}'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter2-${frame})'/%3E%3C/svg%3E")`;
  }, [frame]);

  // Dynamic properties that change based on frame
  const noiseLayer1 = {
    opacity: 0.18 + random(`noise1-${Math.floor(frame / 2)}`) * 0.06,
    transform: `translate(${random(`x1-${Math.floor(frame / 2)}`) * 8 - 4}px, ${
      random(`y1-${Math.floor(frame / 2)}`) * 8 - 4
    }px) scale(${1 + random(`scale1-${Math.floor(frame / 2)}`) * 0.03})`,
  };

  const noiseLayer2 = {
    opacity: 0.15 + random(`noise2-${Math.floor(frame / 3)}`) * 0.05,
    transform: `translate(${
      random(`x2-${Math.floor(frame / 3)}`) * 10 - 5
    }px, ${random(`y2-${Math.floor(frame / 3)}`) * 10 - 5}px) scale(${
      1 + random(`scale2-${Math.floor(frame / 3)}`) * 0.04
    })`,
  };

  return (
    <AbsoluteFill style={styles.container}>
      {/* Base gradient layer for depth */}
      <div style={styles.gradientLayer} />

      {/* Noise layer 1 - finer grain */}
      <div
        style={{
          ...styles.noiseLayer,
          backgroundImage: noisePattern1,
          backgroundSize: "200px 200px",
          ...noiseLayer1,
        }}
      />

      {/* Noise layer 2 - coarser grain */}
      <div
        style={{
          ...styles.noiseLayer,
          backgroundImage: noisePattern2,
          backgroundSize: "300px 300px",
          ...noiseLayer2,
        }}
      />

      {/* Logo at bottom right */}
      <div style={styles.logoContainer}>
        <Logo size={60} color="#000" />
      </div>
    </AbsoluteFill>
  );
};

const styles = {
  container: {
    position: "absolute" as const,
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none" as const,
    zIndex: 10,
  },
  gradientLayer: {
    position: "absolute" as const,
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    background:
      "radial-gradient(ellipse at center, rgba(255, 255, 255, 0.02) 0%, rgba(0, 0, 0, 0.01) 100%)",
    opacity: 0.8,
  },
  noiseLayer: {
    position: "absolute" as const,
    top: "-50%",
    left: "-50%",
    width: "200%",
    height: "200%",
    mixBlendMode: "screen" as const,
    filter: "contrast(1.5) brightness(1.2)",
  },
  logoContainer: {
    position: "absolute" as const,
    bottom: "40px",
    right: "40px",
    zIndex: 100,
    opacity: 0.9,
  },
};
