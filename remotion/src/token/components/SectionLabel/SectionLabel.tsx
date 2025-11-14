import React from "react";

import sectionLabelStyles from "./SectionLabel.module.css";

interface SectionLabelProps {
  children: string;
}

export const SectionLabel: React.FC<SectionLabelProps> = ({ children }) => {
  return (
    <span className={sectionLabelStyles.root} style={labelStylesMap.label}>
      {children.toUpperCase()}
    </span>
  );
};

const labelStylesMap = {
  label: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 42,
    fontWeight: 460,
    color: "var(--section-label-color)",
    letterSpacing: "0.05em",
    textTransform: "uppercase" as const,
  },
};
