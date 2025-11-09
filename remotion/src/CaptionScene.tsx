import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptionData, Word as WordType } from "./types";
import { Word } from "./Word";

interface CaptionSceneProps {
  inputProps: CaptionData;
}

const DROP_DISTANCE = 6; // pixels
const ANIMATION_DURATION_MS = 400;
const MIN_WORD_DURATION_FOR_KARAOKE_MS = 500; // Lower threshold - more lines get karaoke

export const CaptionScene: React.FC<CaptionSceneProps> = ({ inputProps }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const { groups, videoHeight } = inputProps;

  // Calculate margin (15% from bottom, matching the Python code)
  const marginV = Math.floor(videoHeight * 0.27);
  const baselineY = videoHeight - marginV;

  // Process groups to calculate timing
  const processedGroups = groups.map((wordGroup) => {
    const lineStart = wordGroup[0].start;
    const lineEnd = wordGroup[wordGroup.length - 1].end;

    // Calculate line duration
    const lineDurationMs = (lineEnd - lineStart) * 1000;

    // Drop animation and karaoke are always together
    // Only enable if line is long enough for both effects to look good
    const enableEffects = lineDurationMs >= MIN_WORD_DURATION_FOR_KARAOKE_MS;

    return {
      words: wordGroup,
      lineStart,
      lineEnd,
      enableEffects, // Single flag for both drop and karaoke
      startFrame: Math.floor(lineStart * fps),
      endFrame: Math.floor(lineEnd * fps),
    };
  });

  return (
    <AbsoluteFill style={styles.container}>
      {processedGroups.map((group, groupIndex) => {
        const {
          startFrame,
          endFrame,
          words,
          lineStart,
          lineEnd,
          enableEffects,
        } = group;

        // Only render if this line is active
        if (frame < startFrame || frame >= endFrame) {
          return null;
        }

        // Calculate drop animation (only if effects are enabled)
        let currentY = baselineY;
        if (enableEffects) {
          const animationDurationFrames = Math.floor(
            (ANIMATION_DURATION_MS / 1000) * fps
          );
          const animationProgress = Math.min(
            1,
            (frame - startFrame) / animationDurationFrames
          );

          currentY = interpolate(
            animationProgress,
            [0, 1],
            [baselineY - DROP_DISTANCE, baselineY],
            {
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic), // Fast start, smooth ease into final position
            }
          );
        }

        // Calculate word positions (0 = leftmost, 1 = rightmost)
        // We'll use a simple approach: divide the line into equal segments
        const wordCount = words.length;

        return (
          <div
            key={`${groupIndex}-${startFrame}`}
            style={{
              ...styles.captionLine,
              top: currentY,
            }}
          >
            {words.map((word, wordIndex) => {
              // Calculate position ratio for this word
              // Add 0.5 to center each word in its segment
              const wordPositionRatio =
                wordCount > 1 ? (wordIndex + 0.5) / wordCount : 0.5;

              return (
                <Word
                  key={wordIndex}
                  word={word}
                  lineStartFrame={startFrame}
                  isKaraokeEnabled={enableEffects}
                  wordPositionRatio={wordPositionRatio}
                  lineEndTime={lineEnd}
                />
              );
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// Styles
const styles = {
  container: {
    backgroundColor: "transparent",
  },
  captionLine: {
    position: "absolute" as const,
    left: "50%",
    transform: "translateX(-50%)",
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontWeight: 460,
    fontSize: "96px",
    color: "white",
    textAlign: "center" as const,
    whiteSpace: "nowrap" as const,
    letterSpacing: "-0.01em",
  },
};
