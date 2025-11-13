import React from "react";

import { Entity } from "../../types";
import { deriveHandle } from "../../utils/strings";
import { Avatar } from "../Avatar/Avatar";
import { ValuationPill } from "../ValuationPill/ValuationPill";
import headerStyles from "./TokenHeader.module.css";

interface TokenHeaderProps {
  owner: Entity;
  valuation: number;
}

export const TokenHeader: React.FC<TokenHeaderProps> = ({ owner, valuation }) => {
  const handle = deriveHandle(owner.name);

  return (
    <div className={headerStyles.root} style={headerStylesMap.container}>
      <div style={headerStylesMap.identity}>
        <Avatar name={owner.name} profileSrc={owner.profileSrc} size={152} />
        <div style={headerStylesMap.textStack}>
          <span style={headerStylesMap.name}>{owner.name}</span>
          <span style={headerStylesMap.handle}>{handle}</span>
        </div>
      </div>
      <ValuationPill valuation={valuation} label="Valuation" />
    </div>
  );
};

const headerStylesMap = {
  container: {
    width: "100%",
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    justifyContent: "space-between",
    gap: 48,
  },
  identity: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    gap: 36,
  },
  textStack: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 12,
  },
  name: {
    fontFamily: "Sohne, Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 72,
    fontWeight: 650,
    color: "var(--token-header-name-color)",
    letterSpacing: "-0.01em",
  },
  handle: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 40,
    fontWeight: 500,
    color: "var(--token-header-handle-color)",
    letterSpacing: "-0.01em",
  },
};
