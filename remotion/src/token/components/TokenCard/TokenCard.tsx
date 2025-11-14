import React, { CSSProperties } from "react";

import { clampProgress } from "../../animation/primitives";
import { Segment, Token } from "../../types";
import { HolderList } from "../HolderList/HolderList";
import { SegmentControl } from "../SegmentControl/SegmentControl";
import { TokenBio } from "../TokenBio/TokenBio";
import { TokenHeader } from "../TokenHeader/TokenHeader";
import tokenCardStyles from "./TokenCard.module.css";

interface TokenCardProps {
  token: Token;
  segment: Segment;
  isExpanded: boolean;
  appearanceProgress: number;
  glowProgress: number;
  expansionProgress: number;
}

const BIO_MAX_HEIGHT = 420;
const DRAWER_MAX_HEIGHT = 1800;

export const TokenCard: React.FC<TokenCardProps> = ({
  token,
  segment,
  isExpanded,
  appearanceProgress,
  glowProgress,
  expansionProgress,
}) => {
  const visibleProgress = clampProgress(appearanceProgress);
  const glow = clampProgress(glowProgress);
  const drawerProgress = isExpanded ? clampProgress(expansionProgress) : 0;
  const bioProgress = token.owner.bio ? drawerProgress : 0;

  return (
    <div
      className={tokenCardStyles.root}
      style={createContainerStyle(visibleProgress)}
    >
      <div aria-hidden style={createGlowStyles(glow)} />

      <div style={createUserGroupStyles(drawerProgress)}>
        <TokenHeader owner={token.owner} valuation={token.valuation} />

        {token.owner.bio ? (
          <div style={createBioWrapperStyles(bioProgress)}>
            <div style={createBioContentStyles(bioProgress)}>
              <TokenBio bio={token.owner.bio} />
            </div>
          </div>
        ) : null}
      </div>

      <div style={createDrawerWrapperStyles(drawerProgress)}>
        <div style={createDrawerContentStyles(drawerProgress)}>
          <div style={tokenCardStylesMap.segmentControlWrapper}>
            <SegmentControl currentSegment={segment} />
          </div>
          <HolderList
            holders={token.holders}
            holdings={token.holdings}
            segment={segment}
          />
        </div>
      </div>
    </div>
  );
};

const createContainerStyle = (progress: number) => ({
  ...tokenCardStylesMap.container,
  opacity: progress,
});

const createGlowStyles = (progress: number) => {
  if (progress <= 0) {
    return {
      opacity: 0,
      pointerEvents: "none" as const,
    };
  }

  const sweep = 36;
  const startAngle = -135 + progress * 360;
  const highlightStart = `${startAngle.toFixed(2)}deg`;
  const highlightMid = `${(startAngle + sweep * 0.5).toFixed(2)}deg`;
  const highlightEnd = `${(startAngle + sweep).toFixed(2)}deg`;
  const mask =
    "radial-gradient(circle, transparent calc(100% - 4px), #000 100%)";

  return {
    position: "absolute" as const,
    inset: 0,
    borderRadius: "var(--token-card-border-radius)",
    pointerEvents: "none" as const,
    zIndex: 0,
    opacity: Math.min(1, progress * 1.2),
    background: `conic-gradient(
      from -135deg,
      transparent 0deg,
      transparent ${highlightStart},
      var(--token-card-glow-soft) ${highlightStart},
      var(--token-card-glow-strong) ${highlightMid},
      transparent ${highlightEnd},
      transparent 360deg
    )`,
    filter: "blur(var(--token-card-glow-blur))",
    mask,
    WebkitMask: mask,
  };
};

const createUserGroupStyles = (progress: number) => ({
  ...tokenCardStylesMap.userGroup,
  gap: `calc(var(--token-card-inner-gap) * ${0.35 + 0.65 * progress})`,
});

const createBioWrapperStyles = (progress: number) => ({
  width: "100%",
  overflow: "hidden",
  maxHeight: `${BIO_MAX_HEIGHT * progress}px`,
});

const createBioContentStyles = (progress: number) => ({
  opacity: progress,
  transform: `translateY(${(1 - progress) * 24}px)`,
});

const createDrawerWrapperStyles = (progress: number) => ({
  width: "100%",
  overflow: "hidden",
  maxHeight: `${DRAWER_MAX_HEIGHT * progress}px`,
});

const createDrawerContentStyles = (progress: number) => {
  const pointerState: CSSProperties["pointerEvents"] =
    progress > 0.95 ? "auto" : "none";

  return {
    ...tokenCardStylesMap.listGroup,
    opacity: progress,
    transform: `translateY(${(1 - progress) * 48}px)`,
    pointerEvents: pointerState,
  };
};

const tokenCardStylesMap = {
  container: {
    width: "var(--token-card-width)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--token-card-surface-base)",
    border: "var(--token-card-border)",
    boxShadow: "var(--token-card-shadow)",
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden" as const,
    position: "relative" as const,
    isolation: "isolate" as const,
  },
  userGroup: {
    width: "100%",
    padding: "var(--token-card-padding)",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--token-card-inner-gap)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--token-card-surface-hero)",
    border: "var(--token-card-border)",
    boxShadow: "var(--token-card-hero-shadow)",
    position: "relative" as const,
    zIndex: 1,
  },
  listGroup: {
    width: "100%",
    padding: "var(--token-card-padding)",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--token-card-inner-gap)",
    alignItems: "flex-start" as const,
    borderRadius: 0,
    background: "var(--token-card-surface-base)",
    boxShadow: "var(--token-card-drawer-shadow)",
    border: "none",
  },
  segmentControlWrapper: {
    alignSelf: "flex-start" as const,
    width: "max-content",
  },
};
