import React, { useMemo } from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { SceneWrapper } from "./components/SceneWrapper";
import { FocusOverlay, Region } from "./focus";
import { calculateCardBounds } from "./layout";
import {
  TokenScene,
  TOKEN_EXPAND_DELAY_FRAMES,
  TOKEN_EXPAND_DURATION_FRAMES,
} from "./TokenScene";
import {
  PersonalTokenSceneInput,
  Segment,
  SegmentAnimation,
  TokenSceneInput,
} from "./types";

export const PersonalTokenScene: React.FC<PersonalTokenSceneInput> = ({
  showSegmentControl = true,
  ...rest
}) => {
  const frame = useCurrentFrame();
  const { width: videoWidth, height: videoHeight } = useVideoConfig();

  const segmentSwitchProgress = interpolateSegmentSwitch(frame);
  const segmentAnimation = resolveSegmentAnimation(segmentSwitchProgress);
  const currentSegment =
    segmentSwitchProgress >= 1 ? Segment.Holdings : Segment.Holders;

  const tokenSceneProps: TokenSceneInput = {
    ...rest,
    isExpanded: true,
    currentSegment,
    defaultSegment: Segment.Holders,
    showSegmentControl,
    segmentAnimation,
  };

  const valuationColumnRegion = useMemo(
    () => createValuationColumnRegion(videoWidth, videoHeight),
    [videoWidth, videoHeight]
  );

  return (
    <SceneWrapper>
      <AbsoluteFill style={stageStyles.container}>
        <TokenScene {...tokenSceneProps} />
        <FocusOverlay
          regions={[valuationColumnRegion]}
          startFrame={VALUATION_OVERLAY_START_FRAME}
          duration={VALUATION_OVERLAY_DURATION_FRAMES}
          dimOpacity={0.35}
          spotlightRadius={140}
        />
      </AbsoluteFill>
    </SceneWrapper>
  );
};

const interpolateSegmentSwitch = (frame: number) => {
  return interpolate(
    frame,
    [
      SEGMENT_SWITCH_START_FRAME,
      SEGMENT_SWITCH_START_FRAME + SEGMENT_SWITCH_DURATION_FRAMES,
    ],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );
};

const resolveSegmentAnimation = (
  progress: number
): SegmentAnimation | undefined => {
  if (progress <= 0 || progress >= 1) {
    return undefined;
  }

  return {
    from: Segment.Holders,
    to: Segment.Holdings,
    progress,
  };
};

const createValuationColumnRegion = (
  videoWidth: number,
  videoHeight: number
): Region => {
  const bounds = calculateCardBounds(videoWidth, videoHeight);
  const columnWidth = bounds.width * VALUATION_COLUMN_WIDTH_RATIO;
  const columnLeft =
    bounds.left +
    bounds.width -
    columnWidth -
    bounds.width * VALUATION_COLUMN_HORIZONTAL_OFFSET_RATIO;

  return {
    x: columnLeft,
    y: bounds.top + bounds.height * VALUATION_COLUMN_TOP_RATIO,
    width: columnWidth,
    height: bounds.height * VALUATION_COLUMN_HEIGHT_RATIO,
    note: "value grounded in equity",
  };
};

const stageStyles = {
  container: {
    position: "relative" as const,
    width: "100%",
    height: "100%",
  },
};

const SEGMENT_SWITCH_START_FRAME =
  TOKEN_EXPAND_DELAY_FRAMES + TOKEN_EXPAND_DURATION_FRAMES + 12;
const SEGMENT_SWITCH_DURATION_FRAMES = 36;
const VALUATION_OVERLAY_DELAY_AFTER_SWITCH = 18;
const VALUATION_OVERLAY_START_FRAME =
  SEGMENT_SWITCH_START_FRAME +
  SEGMENT_SWITCH_DURATION_FRAMES +
  VALUATION_OVERLAY_DELAY_AFTER_SWITCH;
const VALUATION_OVERLAY_DURATION_FRAMES = 36;

const VALUATION_COLUMN_WIDTH_RATIO = 0.25;
const VALUATION_COLUMN_HORIZONTAL_OFFSET_RATIO = 0.045;
const VALUATION_COLUMN_TOP_RATIO = 0.07;
const VALUATION_COLUMN_HEIGHT_RATIO = 0.86;
