import React from "react";

import { Entity } from "../../types";
import { formatCurrencyCompact, formatPercentage } from "../../utils/formatters";
import { Avatar } from "../Avatar/Avatar";
import holderRowStyles from "./HolderRow.module.css";

interface HolderRowProps {
  entity: Entity;
  percentageEquity: number;
  valuation?: number;
  index: number;
}

export const HolderRow: React.FC<HolderRowProps> = ({
  entity,
  percentageEquity,
  valuation,
  index,
}) => {
  return (
    <div className={holderRowStyles.root} style={holderRowStylesMap.container}>
      <div style={holderRowStylesMap.profile}>
        <Avatar name={entity.name} profileSrc={entity.profileSrc} size={100} />
        <div style={holderRowStylesMap.textStack}>
          <span style={holderRowStylesMap.name}>{entity.name}</span>
          <span style={holderRowStylesMap.subtitle}>Rank #{index + 1}</span>
        </div>
      </div>
      <div style={holderRowStylesMap.meta}>
        <span>{formatPercentage(percentageEquity)}</span>
        {valuation !== undefined && (
          <span style={holderRowStylesMap.secondaryMeta}>
            {formatCurrencyCompact(valuation)}
          </span>
        )}
      </div>
    </div>
  );
};

const holderRowStylesMap = {
  container: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    justifyContent: "space-between",
    padding: "28px 36px",
    borderRadius: 52,
    background: "var(--holder-row-background)",
    boxShadow: "var(--holder-row-shadow)",
    minWidth: 680,
    gap: 36,
  },
  profile: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    gap: 24,
  },
  textStack: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 4,
  },
  name: {
    fontFamily: "Sohne, Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 44,
    fontWeight: 600,
    color: "var(--holder-row-name-color)",
    letterSpacing: "-0.01em",
  },
  subtitle: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 32,
    fontWeight: 500,
    color: "var(--holder-row-subtitle-color)",
    letterSpacing: "-0.01em",
  },
  meta: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "flex-end" as const,
    gap: 6,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontWeight: 600,
    fontSize: 40,
    color: "var(--holder-row-meta-color)",
    letterSpacing: "-0.01em",
  },
  secondaryMeta: {
    fontSize: 32,
    fontWeight: 500,
    color: "var(--holder-row-secondary-meta-color)",
  },
};
