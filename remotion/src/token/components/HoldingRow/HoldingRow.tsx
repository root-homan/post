import React from "react";

import { Entity } from "../../types";
import {
  formatCurrencyCompact,
  formatPercentage,
} from "../../utils/formatters";
import { Avatar } from "../Avatar/Avatar";
import { ValuationPill } from "../ValuationPill/ValuationPill";
import holdingRowStyles from "./HoldingRow.module.css";

interface HoldingRowProps {
  entity: Entity;
  percentageEquity: number;
  companyValuation: number;
}

export const HoldingRow: React.FC<HoldingRowProps> = ({
  entity,
  percentageEquity,
  companyValuation,
}) => {
  const equityValue = calculateEquityValue(percentageEquity, companyValuation);
  const calculationLabel = createCalculationLabel(
    percentageEquity,
    companyValuation
  );

  return (
    <div
      className={holdingRowStyles.root}
      style={holdingRowStylesMap.container}
    >
      <div style={holdingRowStylesMap.profile}>
        <Avatar
          name={entity.name}
          profileSrc={entity.profileSrc}
          variant="list"
        />
        <span style={holdingRowStylesMap.name}>{entity.name}</span>
      </div>
      <div style={holdingRowStylesMap.meta}>
        <span style={holdingRowStylesMap.math}>{calculationLabel}</span>
        <ValuationPill valuation={equityValue} />
      </div>
    </div>
  );
};

const calculateEquityValue = (
  percentageEquity: number,
  companyValuation: number
) => {
  return (percentageEquity / 100) * companyValuation;
};

const createCalculationLabel = (
  percentageEquity: number,
  companyValuation: number
) => {
  return `(${formatPercentage(percentageEquity)} x ${formatCurrencyCompact(
    companyValuation
  )})`;
};

const holdingRowStylesMap = {
  container: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    justifyContent: "space-between",
    padding:
      "var(--list-item-padding-vertical) var(--list-item-padding-horizontal)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--holder-row-background)",
    width: "100%",
    height: "136px",
    gap: "var(--holder-row-gap)",
  },
  profile: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    gap: "var(--holder-row-profile-gap)",
  },
  name: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: "var(--token-card-heading-font-size)",
    fontWeight: "var(--holder-row-name-font-weight)",
    color: "var(--holder-row-name-color)",
    letterSpacing: "var(--holder-row-name-letter-spacing)",
  },
  meta: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    gap: "24px",
    fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, monospace",
    fontSize: "calc(45px * var(--geist-mono-size-adjustment))",
    color: "var(--holder-row-meta-color)",
    fontVariantNumeric: "tabular-nums" as const,
  },
  math: {
    fontSize: "calc(45px * var(--geist-mono-size-adjustment) * 0.9)",
    fontWeight: "var(--holder-row-meta-font-weight)",
    letterSpacing: "var(--holder-row-meta-letter-spacing)",
    color: "rgba(0, 0, 0, 0.4)",
  },
};
