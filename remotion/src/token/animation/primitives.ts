import { spring, SpringConfig, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * A tuned spring inspired by iOS' default motion curves.
 * - Higher stiffness keeps the motion snappy.
 * - Higher damping prevents noticeable overshoot without feeling rigid.
 * Tweak these numbers to globally change how "bouncy" the UI feels.
 */
export const IOS_SPRING_CONFIG: SpringConfig = {
  damping: 200,
  stiffness: 170,
  mass: 0.9,
};

export interface SpringProgressOptions {
  /**
   * Frames to wait before the spring starts evaluating.
   * Helpful for sequencing multi-step reveals.
   */
  delayFrames?: number;
  /**
   * How long the spring is allowed to simulate.
   * Lower numbers feel faster; higher numbers feel softer.
   */
  durationInFrames?: number;
  /** Start value for the spring. Default: 0 */
  from?: number;
  /** Target value for the spring. Default: 1 */
  to?: number;
  /** Override the default spring config when needed. */
  config?: SpringConfig;
  /**
   * Skip the animation entirely (useful for gating with booleans).
   * When disabled, the hook returns the `to` value immediately.
   */
  disabled?: boolean;
}

/**
 * Shared hook for building beautiful, iOS-inspired spring animations.
 * Wraps Remotion's `spring` helper with the defaults above plus some light ergonomics.
 *
 * Returns a clamped numeric progress value – typically piped straight into transforms,
 * opacity, clip paths, etc.
 */
export const useSpringProgress = ({
  delayFrames = 0,
  durationInFrames,
  from = 0,
  to = 1,
  config = IOS_SPRING_CONFIG,
  disabled = false,
}: SpringProgressOptions = {}): number => {
  if (disabled) {
    return to;
  }

  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: Math.max(0, frame - delayFrames),
    fps,
    config,
    from,
    to,
    durationInFrames,
  });

  return clampProgress(progress, Math.min(from, to), Math.max(from, to));
};

/**
 * Tiny util to keep spring results predictable when they're fed into inline styles.
 */
export const clampProgress = (value: number, min = 0, max = 1) => {
  if (Number.isNaN(value)) {
    return min;
  }

  return Math.min(max, Math.max(min, value));
};

