import React from "react";
import { AbsoluteFill } from "remotion";

import { useSpringProgress } from "./animation/primitives";
import { TokenCard } from "./components/TokenCard/TokenCard";
import tokenSceneStyles from "./TokenScene.module.css";
import { TOKEN_SCENE_PREVIEW_PROPS } from "./previewData";
import { Segment, Token, TokenSceneInput } from "./types";

export const TokenScene: React.FC<TokenSceneInput> = ({
  token,
  currentSegment,
  defaultSegment,
  isExpanded,
}) => {
  const effectiveToken = resolveToken(token);
  const activeSegment = resolveSegment(currentSegment, defaultSegment);

  const tokenAppearanceProgress = useSpringProgress({
    delayFrames: TOKEN_APPEAR_DELAY_FRAMES,
    durationInFrames: TOKEN_APPEAR_DURATION_FRAMES,
    to: effectiveToken ? 1 : 0,
    disabled: !effectiveToken,
  });

  const expansionProgress = useSpringProgress({
    delayFrames: TOKEN_EXPAND_DELAY_FRAMES,
    durationInFrames: TOKEN_EXPAND_DURATION_FRAMES,
    to: isExpanded ? 1 : 0,
  });

  const displayedToken =
    tokenAppearanceProgress > 0.001 && effectiveToken ? effectiveToken : null;

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
        {displayedToken ? (
          <TokenCard
            token={displayedToken}
            segment={activeSegment}
            isExpanded={isExpanded}
            appearanceProgress={tokenAppearanceProgress}
            glowProgress={tokenAppearanceProgress}
            expansionProgress={expansionProgress}
          />
        ) : null}
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

const TOKEN_APPEAR_DELAY_FRAMES = 12;
const TOKEN_APPEAR_DURATION_FRAMES = 45;
const TOKEN_EXPAND_DELAY_FRAMES =
  TOKEN_APPEAR_DELAY_FRAMES + TOKEN_APPEAR_DURATION_FRAMES + 12;
const TOKEN_EXPAND_DURATION_FRAMES = 48;
