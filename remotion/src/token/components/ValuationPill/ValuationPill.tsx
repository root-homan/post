import React from "react";

import { formatCurrencyCompact } from "../../utils/formatters";
import valuationStyles from "./ValuationPill.module.css";

interface ValuationPillProps {
  valuation: number;
  label?: string;
}

export const ValuationPill: React.FC<ValuationPillProps> = ({
  valuation,
  label = "Valuation",
}) => {
  return (
    <div className={valuationStyles.root} style={valuationStylesMap.container}>
      <span style={valuationStylesMap.label}>{label}</span>
      <span style={valuationStylesMap.value}>{formatCurrencyCompact(valuation)}</span>
    </div>
  );
};

const valuationStylesMap = {
  container: {
    display: "inline-flex",
    alignItems: "center",
    gap: 12,
    padding: "20px 32px",
    borderRadius: 40,
    background: "var(--valuation-pill-background)",
    color: "var(--valuation-pill-foreground)",
    fontFamily: "Sohne, Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontWeight: 600,
    fontSize: 48,
    letterSpacing: "-0.01em",
    boxShadow: "var(--valuation-pill-shadow)",
  },
  label: {
    fontSize: 32,
    fontWeight: 500,
    color: "var(--valuation-pill-label-color)",
  },
  value: {
    fontVariantNumeric: "tabular-nums" as const,
  },
};
