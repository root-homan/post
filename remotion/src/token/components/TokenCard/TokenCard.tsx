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
  showSegmentControl?: boolean;
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
  showSegmentControl = true,
}) => {
  const visibleProgress = clampProgress(appearanceProgress);
  const glow = clampProgress(glowProgress);
  const drawerProgress = isExpanded ? clampProgress(expansionProgress) : 0;
  const heroProgress = getHeroProgress(drawerProgress);
  const bioProgress = token.owner.bio ? heroProgress : 0;

  return (
    <div
      className={tokenCardStyles.root}
      style={createContainerStyle(visibleProgress, drawerProgress)}
    >
      <div aria-hidden style={createGlowStyles(glow, drawerProgress)} />

      <div style={createUserGroupStyles(heroProgress)}>
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
          {showSegmentControl ? (
            <div style={tokenCardStylesMap.segmentControlWrapper}>
              <SegmentControl currentSegment={segment} />
            </div>
          ) : null}
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

const createContainerStyle = (visible: number, expansion: number) => ({
  ...tokenCardStylesMap.container,
  opacity: visible,
  borderRadius: getAnimatedRadius(expansion),
  width: getAnimatedWidth(expansion),
});

const createGlowStyles = (progress: number, expansion: number) => {
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
  const blurScale = 1 + (1 - expansion) * 0.35;
  const mask =
    "radial-gradient(circle, transparent calc(100% - 3px), #000 100%)";

  return {
    position: "absolute" as const,
    inset: 0,
    borderRadius: getAnimatedRadius(expansion),
    pointerEvents: "none" as const,
    zIndex: 2,
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
    filter: `blur(calc(var(--token-card-glow-blur) * ${blurScale.toFixed(2)}))`,
    mixBlendMode: "screen" as const,
    maskImage: mask,
    WebkitMaskImage: mask,
    maskMode: "alpha",
    WebkitMaskRepeat: "no-repeat",
    maskRepeat: "no-repeat" as const,
  };
};

const createUserGroupStyles = (progress: number) => ({
  ...tokenCardStylesMap.userGroup,
  gap: `calc(var(--token-card-inner-gap) * ${formatScale(progress)})`,
  justifyContent: progress < 0.05 ? "center" : "flex-start",
  borderRadius: getAnimatedRadius(progress),
  padding: getAnimatedPadding(progress),
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

const getAnimatedRadius = (progress: number) => {
  const scale = 1 + (1 - progress);
  return `calc(var(--token-card-border-radius) * ${formatScale(scale)})`;
};

const getAnimatedPadding = (progress: number) => {
  const scale = 0.5 + 0.5 * progress;
  return `calc(var(--token-card-padding) * ${formatScale(scale)})`;
};

const formatScale = (value: number) => value.toFixed(3).replace(/\.?0+$/, "");

const tokenCardStylesMap = {
  container: {
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

const getAnimatedWidth = (progress: number) => {
  const widthProgress = Math.min(
    progress / WIDTH_EXPANSION_COMPLETION_POINT,
    1
  );
  const scale = 1 + 0.25 * widthProgress;
  return `calc(var(--token-card-width) * ${formatScale(scale)})`;
};

const WIDTH_EXPANSION_COMPLETION_POINT = 0.5;
const HERO_COMPLETION_POINT = 0.5;

const getHeroProgress = (progress: number) => {
  if (progress <= 0) {
    return 0;
  }

  return clampProgress(progress / HERO_COMPLETION_POINT);
};
