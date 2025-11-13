import React from "react";
import { AbsoluteFill } from "remotion";

import { TokenCard } from "./components/TokenCard/TokenCard";
import tokenSceneStyles from "./TokenScene.module.css";
import { TOKEN_SCENE_PREVIEW_PROPS } from "./previewData";
import {
  Segment,
  Token,
  TokenComponent,
  TokenSceneInput,
} from "./types";

export const TokenScene: React.FC<TokenSceneInput> = ({
  token,
  currentSegment,
  defaultSegment,
  isExpanded,
  annotations,
  lightFocus,
  cameraFocus,
}) => {
  const effectiveToken = resolveToken(token);
  const activeSegment = resolveSegment(currentSegment, defaultSegment);
  const focusTargets = resolveLightFocus(lightFocus);

  if (!effectiveToken) {
    return (
      <AbsoluteFill
        className={tokenSceneStyles.root}
        style={sceneStyles.container}
      />
    );
  }

  return (
    <AbsoluteFill
      className={tokenSceneStyles.root}
      style={sceneStyles.container}
    >
      <div style={sceneStyles.content}>
        <TokenCard
          token={effectiveToken}
          segment={activeSegment}
          isExpanded={isExpanded}
          annotations={annotations}
          lightFocus={focusTargets}
          cameraFocus={cameraFocus}
        />
      </div>
    </AbsoluteFill>
  );
};

const sceneStyles = {
  container: {
    width: "100%",
    height: "100%",
    background: "var(--token-scene-background)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "var(--token-scene-padding)",
    position: "relative" as const,
  },
  content: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
  },
};

const resolveToken = (token: Token | null | undefined): Token | null => {
  if (token) {
    return token;
  }

  return TOKEN_SCENE_PREVIEW_PROPS.token ?? null;
};

const resolveSegment = (
  currentSegment: Segment,
  defaultSegment: Segment
): Segment => {
  return currentSegment ?? defaultSegment;
};

const resolveLightFocus = (lightFocus?: TokenComponent[]) => {
  return lightFocus ?? [];
};
