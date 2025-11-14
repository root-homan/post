import React from "react";
import { AbsoluteFill } from "remotion";
import { SceneBackground } from "../SceneBackground/SceneBackground";

interface SceneWrapperProps {
  children: React.ReactNode;
  backgroundColor?: string;
}

export const SceneWrapper: React.FC<SceneWrapperProps> = ({ 
  children, 
  backgroundColor = "#000000" 
}) => {
  return (
    <AbsoluteFill style={{ ...styles.container, backgroundColor }}>
      <SceneBackground />
      <div style={styles.content}>
        {children}
      </div>
    </AbsoluteFill>
  );
};

const styles = {
  container: {
    position: "relative" as const,
    width: "100%",
    height: "100%",
  },
  content: {
    position: "relative" as const,
    width: "100%",
    height: "100%",
    zIndex: 1,
  },
};

