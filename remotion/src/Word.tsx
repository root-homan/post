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

// Light effect constants - three-stage softbox style
const LIGHT_WIDTH = 0.7; // How wide the light beam is (0-1, proportion of line width)
const UNREACHED_OPACITY = 0.35; // Opacity for words not yet reached - subtle gray
const ACTIVE_OPACITY = 1.0; // Full opacity when currently active
const REACHED_OPACITY = 1.0; // Opacity for already-reached words - same as active

export const Word: React.FC<WordProps> = ({
  word,
  lineStartFrame,
  isKaraokeEnabled,
  wordPositionRatio,
  lineEndTime,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Remove punctuation and convert to lowercase
  const displayText = word.word.replace(/[^\w\s]|_/g, "").toLowerCase();

  if (!isKaraokeEnabled) {
    // No karaoke - always full opacity
    return <span style={styles.word}>{displayText}</span>;
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

  // Determine the word's state based on light position
  const distanceFromLight = wordPositionRatio - lightPosition;

  let opacity: number;

  if (distanceFromLight < -LIGHT_WIDTH) {
    // Word is beyond the light - already reached
    opacity = REACHED_OPACITY;
  } else if (Math.abs(distanceFromLight) <= LIGHT_WIDTH) {
    // Word is in the light beam - interpolate between states
    if (distanceFromLight < 0) {
      // Light has partially passed - transitioning to "reached"
      opacity = interpolate(
        distanceFromLight,
        [-LIGHT_WIDTH, 0],
        [REACHED_OPACITY, ACTIVE_OPACITY],
        { extrapolateRight: "clamp" }
      );
    } else {
      // Light is approaching - transitioning from "unreached"
      opacity = interpolate(
        distanceFromLight,
        [0, LIGHT_WIDTH],
        [ACTIVE_OPACITY, UNREACHED_OPACITY],
        { extrapolateLeft: "clamp" }
      );
    }
  } else {
    // Word hasn't been reached yet
    opacity = UNREACHED_OPACITY;
  }

  return (
    <span
      style={{
        ...styles.word,
        opacity,
      }}
    >
      {displayText}
    </span>
  );
};

// Styles
const styles = {
  word: {
    marginRight: "0.3em",
  },
};
