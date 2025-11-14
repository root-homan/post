import { Composition } from "remotion";
import { CaptionScene } from "./CaptionScene";
import { CaptionScenePreview } from "./CaptionScenePreview";
import { PREVIEW_DATA } from "./PreviewData";
import { CompanyScene } from "./token/CompanyScene";
import { TokenScene } from "./token/TokenScene";
import {
  COMPANY_SCENE_PREVIEW_PROPS,
  TOKEN_SCENE_PREVIEW_PROPS,
} from "./token/previewData";

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

      <Composition
        id="TokenScene"
        component={TokenScene}
        durationInFrames={180}
        fps={30}
        width={2880}
        height={2160}
        defaultProps={TOKEN_SCENE_PREVIEW_PROPS}
      />

      <Composition
        id="CompanyScene"
        component={CompanyScene}
        durationInFrames={180}
        fps={30}
        width={2880}
        height={2160}
        defaultProps={COMPANY_SCENE_PREVIEW_PROPS}
      />
    </>
  );
};
