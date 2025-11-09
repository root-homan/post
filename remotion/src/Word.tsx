import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Word as WordType } from "./types";

interface WordProps {
  word: WordType;
  lineStartFrame: number;
  isKaraokeEnabled: boolean;
  wordPositionRatio: number; // Position of this word in the line (0 = leftmost, 1 = rightmost)
  lineEndTime: number; // End time of the entire line in seconds
}

// Opacity constants
const ACTIVE_OPACITY = 1.0; // Opacity when light is on the word
const INACTIVE_OPACITY = 0.675; // Opacity for unlit words
const LIGHT_WIDTH = 0.7; // How wide the light beam is (0-1, proportion of line width)

export const Word: React.FC<WordProps> = ({
  word,
  lineStartFrame,
  isKaraokeEnabled,
  wordPositionRatio,
  lineEndTime,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!isKaraokeEnabled) {
    // No karaoke - always full opacity
    return <span style={styles.word}>{word.word}</span>;
  }

  // Calculate the current time position of the light sweep (0 to 1 across the line)
  const lineStartTime = lineStartFrame / fps;
  const lineDuration = lineEndTime - lineStartTime;
  const currentTime = frame / fps;
  const timeProgress = Math.max(
    0,
    Math.min(1, (currentTime - lineStartTime) / lineDuration)
  );

  // The light sweeps from -LIGHT_WIDTH to 1+LIGHT_WIDTH
  // This ensures smooth entry and exit
  const lightPosition = interpolate(
    timeProgress,
    [0, 1],
    [-LIGHT_WIDTH, 1 + LIGHT_WIDTH],
    { extrapolateRight: "clamp" }
  );

  // Calculate distance from light center to this word's position
  const distanceFromLight = Math.abs(wordPositionRatio - lightPosition);

  // Calculate opacity based on distance from light
  // Words close to the light are bright, words far away are dim
  const opacity = interpolate(
    distanceFromLight,
    [0, LIGHT_WIDTH],
    [ACTIVE_OPACITY, INACTIVE_OPACITY],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  return <span style={{ ...styles.word, opacity }}>{word.word}</span>;
};

// Styles
const styles = {
  word: {
    marginRight: "0.3em",
  },
};
