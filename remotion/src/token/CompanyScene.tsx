import React from "react";

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

  return <TokenScene {...tokenSceneProps} />;
};

