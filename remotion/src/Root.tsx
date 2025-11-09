import { Composition } from "remotion";
import { CaptionScene } from "./CaptionScene";
import { CaptionScenePreview } from "./CaptionScenePreview";
import { CaptionData } from "./types";
import { PREVIEW_DATA } from "./PreviewData";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Main composition - used by CLI render (transparent) */}
      <Composition
        id="CaptionScene"
        component={CaptionScene}
        durationInFrames={PREVIEW_DATA.durationInFrames}
        fps={PREVIEW_DATA.fps}
        width={PREVIEW_DATA.videoWidth}
        height={PREVIEW_DATA.videoHeight}
        defaultProps={{
          inputProps: PREVIEW_DATA,
        }}
        calculateMetadata={({ props }) => {
          const { inputProps } = props;
          return {
            durationInFrames: inputProps.durationInFrames,
            fps: inputProps.fps,
            width: inputProps.videoWidth,
            height: inputProps.videoHeight,
          };
        }}
      />

      {/* Preview composition - with black background for visibility */}
      <Composition
        id="CaptionScenePreview"
        component={CaptionScenePreview}
        durationInFrames={PREVIEW_DATA.durationInFrames}
        fps={PREVIEW_DATA.fps}
        width={PREVIEW_DATA.videoWidth}
        height={PREVIEW_DATA.videoHeight}
        defaultProps={{
          inputProps: PREVIEW_DATA,
        }}
      />
    </>
  );
};
