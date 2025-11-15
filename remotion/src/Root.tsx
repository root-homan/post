import { Composition } from "remotion";
import { CaptionScene } from "./CaptionScene";
import { CaptionScenePreview } from "./CaptionScenePreview";
import { CaptionComposition } from "./CaptionComposition";
import { PREVIEW_DATA } from "./PreviewData";
import { CompanyScene } from "./token/CompanyScene";
import { LogoScene } from "./token/LogoScene";
import { PersonalTokenScene } from "./token/PersonalTokenScene";
import { TokenScene } from "./token/TokenScene";
import {
  COMPANY_SCENE_PREVIEW_PROPS,
  PERSONAL_TOKEN_SCENE_PROPS,
  TOKEN_SCENE_PREVIEW_PROPS,
} from "./token/previewData";
import { AnimatedLogoPreview } from "./token/components/Logo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Production composition - receives merged data from Python */}
      <Composition
        id="CaptionComposition"
        component={CaptionComposition}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          inputProps: {
            groups: [],
            videoWidth: 1920,
            videoHeight: 1080,
            fps: 30,
            durationInFrames: 300,
          },
        }}
        calculateMetadata={({ props }) => {
          const data = props as {
            inputProps: {
              durationInFrames: number;
              fps: number;
              videoWidth: number;
              videoHeight: number;
            };
          };
          return {
            durationInFrames: data.inputProps.durationInFrames,
            fps: data.inputProps.fps,
            width: data.inputProps.videoWidth,
            height: data.inputProps.videoHeight,
          };
        }}
      />

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
          const data = props as {
            inputProps: {
              durationInFrames: number;
              fps: number;
              videoWidth: number;
              videoHeight: number;
            };
          };
          return {
            durationInFrames: data.inputProps.durationInFrames,
            fps: data.inputProps.fps,
            width: data.inputProps.videoWidth,
            height: data.inputProps.videoHeight,
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

      <Composition
        id="PersonalTokenScene"
        component={PersonalTokenScene}
        durationInFrames={210}
        fps={30}
        width={2880}
        height={2160}
        defaultProps={PERSONAL_TOKEN_SCENE_PROPS}
      />

      <Composition
        id="LogoScene"
        component={LogoScene}
        durationInFrames={90}
        fps={30}
        width={2880}
        height={2160}
      />

      <Composition
        id="ClosingScene"
        component={AnimatedLogoPreview}
        durationInFrames={180}
        fps={30}
        width={2880}
        height={2160}
      />
    </>
  );
};
