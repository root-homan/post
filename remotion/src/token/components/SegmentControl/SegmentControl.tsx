import React from "react";

import { Segment, SegmentAnimation } from "../../types";
import segmentControlStyles from "./SegmentControl.module.css";

interface SegmentControlProps {
  currentSegment: Segment;
  segmentAnimation?: SegmentAnimation;
  onChange?: (segment: Segment) => void;
}

const SEGMENT_OPTIONS: Array<{ label: string; value: Segment }> = [
  { label: "Holders", value: Segment.Holders },
  { label: "Holdings", value: Segment.Holdings },
];

export const SegmentControl: React.FC<SegmentControlProps> = ({
  currentSegment,
  segmentAnimation,
  onChange,
}) => {
  // Determine the effective segment to show based on animation progress
  const displaySegment = getDisplaySegment(currentSegment, segmentAnimation);

  return (
    <div
      className={segmentControlStyles.root}
      style={segmentStyles.container}
      role="tablist"
      aria-label="Token segment control"
    >
      {SEGMENT_OPTIONS.map((option) => {
        const isActive = option.value === displaySegment;
        const optionStyle = {
          ...segmentStyles.optionBase,
          ...segmentStyles.getOptionStyle(isActive),
        };

        return (
          <div
            key={option.value}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            style={optionStyle}
            onClick={() => onChange?.(option.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onChange?.(option.value);
              }
            }}
          >
            {option.label}
          </div>
        );
      })}
    </div>
  );
};

const getDisplaySegment = (
  currentSegment: Segment,
  animation?: SegmentAnimation
): Segment => {
  if (!animation) {
    return currentSegment;
  }

  // Switch at 50% progress for a synchronized transition
  return animation.progress < 0.5 ? animation.from : animation.to;
};

const segmentStyles = {
  container: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "flex-start",
    padding: "var(--segment-control-padding)",
    gap: "var(--segment-control-gap)",
    borderRadius: "var(--token-card-border-radius)",
    border: "var(--segment-control-border)",
    background: "var(--segment-control-background)",
  },
  optionBase: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "var(--segment-control-pill-padding-vertical) var(--segment-control-pill-padding-horizontal)",
    borderRadius: "var(--segment-control-pill-radius)",
    border: "1px solid transparent",
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: "var(--segment-control-label-size)",
    fontWeight: "var(--segment-control-label-font-weight)",
    letterSpacing: "var(--segment-control-label-letter-spacing)",
    cursor: "pointer",
    transition: "all 200ms ease",
  },
  getOptionStyle: (isActive: boolean) => ({
    borderRadius: "var(--segment-control-pill-radius)",
    color: isActive
      ? "var(--segment-control-active-color)"
      : "var(--segment-control-inactive-color)",
    background: isActive
      ? "var(--segment-control-active-background)"
      : "transparent",
  }),
};
