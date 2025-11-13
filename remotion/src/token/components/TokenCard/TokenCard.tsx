import React from "react";

import { Segment, Token } from "../../types";
import { HolderList } from "../HolderList/HolderList";
import { SegmentControl } from "../SegmentControl/SegmentControl";
import { TokenBio } from "../TokenBio/TokenBio";
import { TokenHeader } from "../TokenHeader/TokenHeader";
import tokenCardStyles from "./TokenCard.module.css";

interface TokenCardProps {
  token: Token;
  segment: Segment;
}

export const TokenCard: React.FC<TokenCardProps> = ({ token, segment }) => {
  return (
    <div className={tokenCardStyles.root} style={tokenCardStylesMap.container}>
      {/* User Group: Header + Bio */}
      <div style={tokenCardStylesMap.userGroup}>
        <TokenHeader owner={token.owner} valuation={token.valuation} />
        <TokenBio bio={token.owner.bio} />
      </div>

      {/* List Group: Segment Control + List */}
      <div style={tokenCardStylesMap.listGroup}>
        <div style={tokenCardStylesMap.segmentControlWrapper}>
          <SegmentControl currentSegment={segment} />
        </div>
        <HolderList
          holders={token.holders}
          holdings={token.holdings}
          segment={segment}
        />
      </div>
    </div>
  );
};

const tokenCardStylesMap = {
  container: {
    width: 1280,
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--token-card-surface-base)",
    border: "var(--token-card-border)",
    boxShadow: "var(--token-card-shadow)",
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden" as const,
  },
  userGroup: {
    width: "100%",
    padding: "var(--token-card-padding)",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--token-card-inner-gap)",
    borderRadius: "var(--token-card-border-radius)",
    background: "var(--token-card-surface-hero)",
    border: "var(--token-card-border)",
    boxShadow: "var(--token-card-hero-shadow)",
    position: "relative" as const,
    zIndex: 1,
  },
  listGroup: {
    width: "100%",
    padding: "var(--token-card-padding)",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--token-card-inner-gap)",
    alignItems: "flex-start" as const,
    borderRadius: 0,
    background: "var(--token-card-surface-base)",
    boxShadow: "var(--token-card-drawer-shadow)",
    border: "none",
  },
  segmentControlWrapper: {
    alignSelf: "flex-start" as const,
    width: "max-content",
  },
};
