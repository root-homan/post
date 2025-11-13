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
        <Avatar 
          name={entity.name} 
          profileSrc={entity.profileSrc}
          variant="list"
        />
        <span style={holderRowStylesMap.name}>{entity.name}</span>
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
    padding: "var(--list-item-padding-vertical) var(--list-item-padding-horizontal)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--holder-row-background)",
    width: "100%", // Adapts to container width
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
    flexDirection: "column" as const,
    alignItems: "flex-end" as const,
    gap: "var(--holder-row-meta-gap)",
    fontFamily: "'Geist Mono', 'SF Mono', Monaco, Consolas, monospace",
    fontWeight: "var(--holder-row-meta-font-weight)",
    fontSize: "var(--holder-row-meta-font-size)",
    color: "var(--holder-row-meta-color)",
    letterSpacing: "var(--holder-row-meta-letter-spacing)",
    fontVariantNumeric: "tabular-nums" as const,
  },
  secondaryMeta: {
    fontSize: "var(--holder-row-meta-font-size)",
    fontWeight: "var(--holder-row-meta-font-weight)",
    color: "var(--holder-row-secondary-meta-color)",
  },
};
