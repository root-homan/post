import React from "react";

import { Segment } from "../../types";
import segmentControlStyles from "./SegmentControl.module.css";

interface SegmentControlProps {
  currentSegment: Segment;
  onChange?: (segment: Segment) => void;
}

const SEGMENT_OPTIONS: Array<{ label: string; value: Segment }> = [
  { label: "Holders", value: Segment.Holders },
  { label: "Holdings", value: Segment.Holdings },
];

export const SegmentControl: React.FC<SegmentControlProps> = ({
  currentSegment,
  onChange,
}) => {
  return (
    <div
      className={segmentControlStyles.root}
      style={segmentStyles.container}
      role="tablist"
      aria-label="Token segment control"
    >
      {SEGMENT_OPTIONS.map((option) => {
        const isActive = option.value === currentSegment;
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

const segmentStyles = {
  container: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 12,
    gap: 12,
    borderRadius: 56,
    background: "var(--segment-control-background)",
    boxShadow: "var(--segment-control-shadow)",
  },
  optionBase: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "20px 72px",
    borderRadius: 48,
    fontFamily: "Sohne, Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 40,
    fontWeight: 600,
    letterSpacing: "-0.01em",
    cursor: "pointer",
    transition: "all 200ms ease",
  },
  getOptionStyle: (isActive: boolean) => ({
    color: isActive
      ? "var(--segment-control-active-color)"
      : "var(--segment-control-inactive-color)",
    background: isActive
      ? "var(--segment-control-active-background)"
      : "transparent",
    boxShadow: isActive ? "var(--segment-control-active-shadow)" : "none",
  }),
};
