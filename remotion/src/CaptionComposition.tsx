import React from "react";
import { CaptionScene } from "./CaptionScene";
import { CaptionData } from "./types";

interface CaptionCompositionProps {
  inputProps: CaptionData;
}

/**
 * Production wrapper for CaptionScene.
 *
 * Python reads and merges the word and grouping files, then passes
 * the complete merged data as props. This avoids file loading in the browser.
 */
export const CaptionComposition: React.FC<CaptionCompositionProps> = ({
  inputProps,
}) => {
  return <CaptionScene inputProps={inputProps} />;
};
