import React from "react";

import { Entity } from "../../types";
import { Avatar } from "../Avatar/Avatar";
import { ValuationPill } from "../ValuationPill/ValuationPill";
import headerStyles from "./TokenHeader.module.css";

interface TokenHeaderProps {
  owner: Entity;
  valuation: number;
}

export const TokenHeader: React.FC<TokenHeaderProps> = ({
  owner,
  valuation,
}) => {
  return (
    <div className={headerStyles.root} style={headerStylesMap.container}>
      <div style={headerStylesMap.identity}>
        <Avatar
          name={owner.name}
          profileSrc={owner.profileSrc}
        />
        <span style={headerStylesMap.name}>{owner.name}</span>
      </div>
      <ValuationPill valuation={valuation} />
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
    gap: "var(--token-header-gap)",
  },
  identity: {
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "center",
    gap: "var(--token-header-identity-gap)",
  },
  name: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: "var(--token-card-heading-font-size)",
    fontWeight: "var(--token-header-name-font-weight)",
    color: "var(--token-header-name-color)",
    letterSpacing: "var(--token-header-name-letter-spacing)",
  },
};
