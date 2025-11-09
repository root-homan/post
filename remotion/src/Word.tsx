import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Word as WordType } from "./types";

interface WordProps {
  word: WordType;
  lineStartFrame: number; // Absolute frame when line starts
  isKaraokeEnabled: boolean;
}

// Animation constants
const ANIMATION_DURATION_MS = 64;
const MIN_WORD_DURATION_FOR_KARAOKE_MS = 100;
const KARAOKE_FADE_BACK_MS = 80;

// Opacity constants - easily tweakable
const ACTIVE_OPACITY = 1.0; // Opacity when word is being spoken
const INACTIVE_OPACITY = 0.7; // Opacity for words not yet/already spoken

export const Word: React.FC<WordProps> = ({
  word,
  lineStartFrame,
  isKaraokeEnabled,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculate absolute frame numbers for this word
  const wordStartFrame = Math.floor(word.start * fps);
  const wordEndFrame = Math.floor(word.end * fps);
  const fadeBackEndFrame = Math.floor(
    (word.end + KARAOKE_FADE_BACK_MS / 1000) * fps
  );

  // Calculate frame relative to line start (for logic)
  const relativeFrame = frame - lineStartFrame;
  const relativeWordStart = wordStartFrame - lineStartFrame;
  const relativeWordEnd = wordEndFrame - lineStartFrame;
  const relativeFadeBackEnd = fadeBackEndFrame - lineStartFrame;

  // Karaoke is determined at the line level, not per-word
  const shouldUseKaraoke = isKaraokeEnabled;

  // Calculate opacity based on timing
  let opacity = INACTIVE_OPACITY; // Default inactive opacity

  if (shouldUseKaraoke) {
    if (relativeFrame >= relativeWordStart && relativeFrame < relativeWordEnd) {
      // Fade to full opacity during word
      const progress =
        (relativeFrame - relativeWordStart) /
        Math.max(1, relativeWordEnd - relativeWordStart);
      opacity = interpolate(
        progress,
        [0, 1],
        [INACTIVE_OPACITY, ACTIVE_OPACITY],
        {
          extrapolateRight: "clamp",
        }
      );
    } else if (
      relativeFrame >= relativeWordEnd &&
      relativeFrame < relativeFadeBackEnd
    ) {
      // Fade back to inactive
      const progress =
        (relativeFrame - relativeWordEnd) /
        Math.max(1, relativeFadeBackEnd - relativeWordEnd);
      opacity = interpolate(
        progress,
        [0, 1],
        [ACTIVE_OPACITY, INACTIVE_OPACITY],
        {
          extrapolateRight: "clamp",
        }
      );
    } else if (relativeFrame >= relativeFadeBackEnd) {
      opacity = INACTIVE_OPACITY;
    }
  } else {
    // No karaoke - always full opacity
    opacity = ACTIVE_OPACITY;
  }

  return <span style={{ ...styles.word, opacity }}>{word.word}</span>;
};

// Styles
const styles = {
  word: {
    marginRight: "0.3em",
  },
};
