import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

import { FocusOverlay, Region } from "./focus";
import { TokenScene } from "./TokenScene";
import { CompanySceneInput, Segment, TokenSceneInput } from "./types";

export const CompanyScene: React.FC<CompanySceneInput> = ({
  currentSegment = Segment.Holders,
  defaultSegment = Segment.Holders,
  showSegmentControl = false,
  ...rest
}) => {
  const tokenSceneProps: TokenSceneInput = {
    ...rest,
    currentSegment,
    defaultSegment,
    showSegmentControl,
  };

  const frame = useCurrentFrame();
  const { width: videoWidth, height: videoHeight } = useVideoConfig();

  const holdersRegion = useMemo(
    () => createHoldersRegion(videoWidth, videoHeight),
    [videoWidth, videoHeight]
  );

  const shouldHighlightHolders = currentSegment === Segment.Holders;
  const focusRegions: Region[] = shouldHighlightHolders ? [holdersRegion] : [];

  return (
    <AbsoluteFill style={companySceneStyles.stage}>
      <TokenScene {...tokenSceneProps} />
      <FocusOverlay
        regions={focusRegions}
        startFrame={HOLDERS_FOCUS_START_FRAME}
        duration={24}
        dimOpacity={0.25}
        spotlightRadius={40}
      />
    </AbsoluteFill>
  );
};

const companySceneStyles = {
  stage: {
    position: "relative" as const,
    width: "100%",
    height: "100%",
  },
};

const createHoldersRegion = (
  videoWidth: number,
  videoHeight: number
): Region => {
  const cardWidth = CARD_BASE_WIDTH * CARD_EXPANDED_SCALE;
  const cardHeight = CARD_VISUAL_HEIGHT;

  const cardLeft = (videoWidth - cardWidth) / 2;
  const cardTop = (videoHeight - cardHeight) / 2;

  const horizontalInset = cardWidth * CARD_HORIZONTAL_INSET_RATIO;
  const regionWidth = cardWidth - horizontalInset * 2;
  const regionHeight = cardHeight * HOLDERS_HEIGHT_RATIO;
  const regionTop = cardTop + cardHeight * HOLDERS_TOP_RATIO;

  return {
    x: cardLeft + horizontalInset,
    y: regionTop,
    width: regionWidth,
    height: regionHeight,
    note: "shared equity",
  };
};

const CARD_BASE_WIDTH = 1096;
const CARD_EXPANDED_SCALE = 1.25;
const CARD_VISUAL_HEIGHT = 1860;
const CARD_HORIZONTAL_INSET_RATIO =
  96 / (CARD_BASE_WIDTH * CARD_EXPANDED_SCALE);
const HOLDERS_TOP_RATIO = 0.38;
const HOLDERS_HEIGHT_RATIO = 0.48;

const TOKEN_APPEAR_DELAY_FRAMES = 12;
const TOKEN_APPEAR_DURATION_FRAMES = 45;
const TOKEN_EXPAND_DELAY_FRAMES =
  TOKEN_APPEAR_DELAY_FRAMES + TOKEN_APPEAR_DURATION_FRAMES + 12;
const TOKEN_EXPAND_DURATION_FRAMES = 48;
const HOLDERS_FOCUS_BUFFER_FRAMES = 6;
const HOLDERS_FOCUS_START_FRAME =
  TOKEN_EXPAND_DELAY_FRAMES +
  TOKEN_EXPAND_DURATION_FRAMES +
  HOLDERS_FOCUS_BUFFER_FRAMES;
