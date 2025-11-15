import React, { useMemo } from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";

import { SceneWrapper } from "./components/SceneWrapper";
import { FocusOverlay, Region } from "./focus";
import { calculateCardBounds, CARD_HORIZONTAL_INSET_RATIO } from "./layout";
import {
  TokenScene,
  TOKEN_EXPAND_DELAY_FRAMES,
  TOKEN_EXPAND_DURATION_FRAMES,
} from "./TokenScene";
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

  const { width: videoWidth, height: videoHeight } = useVideoConfig();

  const holdersRegion = useMemo(
    () => createHoldersRegion(videoWidth, videoHeight),
    [videoWidth, videoHeight]
  );

  const shouldHighlightHolders = currentSegment === Segment.Holders;
  const focusRegions: Region[] = shouldHighlightHolders ? [holdersRegion] : [];

  return (
    <SceneWrapper>
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
    </SceneWrapper>
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
  const { width, height, left, top } = calculateCardBounds(
    videoWidth,
    videoHeight
  );

  const horizontalInset = width * CARD_HORIZONTAL_INSET_RATIO;
  const regionWidth = width - horizontalInset * 2;
  const regionHeight = height * HOLDERS_HEIGHT_RATIO;
  const regionTop = top + height * HOLDERS_TOP_RATIO;

  return {
    x: left + horizontalInset,
    y: regionTop,
    width: regionWidth,
    height: regionHeight,
    note: "shared equity",
  };
};

const HOLDERS_TOP_RATIO = 0.38;
const HOLDERS_HEIGHT_RATIO = 0.48;

const HOLDERS_FOCUS_BUFFER_FRAMES = 0;
const HOLDERS_FOCUS_START_FRAME =
  TOKEN_EXPAND_DELAY_FRAMES +
  TOKEN_EXPAND_DURATION_FRAMES +
  HOLDERS_FOCUS_BUFFER_FRAMES;
