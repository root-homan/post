import React from "react";

import { formatCurrencyCompact } from "../../utils/formatters";
import valuationStyles from "./ValuationPill.module.css";

interface ValuationPillProps {
  valuation: number;
}

export const ValuationPill: React.FC<ValuationPillProps> = ({ valuation }) => {
  return (
    <div className={valuationStyles.root} style={valuationStylesMap.container}>
      <span style={valuationStylesMap.value}>{formatCurrencyCompact(valuation)}</span>
    </div>
  );
};

const valuationStylesMap = {
  container: {
    display: "inline-flex",
    alignItems: "center",
    padding: "var(--valuation-pill-padding-vertical) var(--valuation-pill-padding-horizontal)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--valuation-pill-background)",
    color: "var(--valuation-pill-foreground)",
  },
  value: {
    fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, monospace",
    fontSize: "var(--valuation-pill-font-size)",
    fontWeight: "var(--valuation-pill-font-weight)",
    fontVariantNumeric: "tabular-nums" as const,
    letterSpacing: "var(--valuation-pill-letter-spacing)",
  },
};
