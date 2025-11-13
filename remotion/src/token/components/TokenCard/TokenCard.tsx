import React, { useMemo } from "react";

import {
  Annotation,
  CameraFocus,
  Segment,
  Token,
  TokenComponent,
} from "../../types";
import { HolderList } from "../HolderList/HolderList";
import { SegmentControl } from "../SegmentControl/SegmentControl";
import { TokenBio } from "../TokenBio/TokenBio";
import { TokenHeader } from "../TokenHeader/TokenHeader";
import tokenCardStyles from "./TokenCard.module.css";

interface TokenCardProps {
  token: Token;
  segment: Segment;
  isExpanded: boolean;
  annotations?: Annotation[];
  lightFocus?: TokenComponent[];
  cameraFocus?: CameraFocus;
}

export const TokenCard: React.FC<TokenCardProps> = ({
  token,
  segment,
  isExpanded: _isExpanded,
  annotations: _annotations,
  lightFocus,
  cameraFocus: _cameraFocus,
}) => {
  const headerOpacity = useSectionOpacity(lightFocus, [
    TokenComponent.Name,
    TokenComponent.Valuation,
  ]);
  const bioOpacity = useSectionOpacity(lightFocus, [TokenComponent.Bio]);
  const controlOpacity = useSectionOpacity(lightFocus, [
    TokenComponent.HoldersPane,
    TokenComponent.HoldingsPane,
  ]);
  const listOpacity = useSectionOpacity(lightFocus, [
    segment === Segment.Holders
      ? TokenComponent.HoldersPane
      : TokenComponent.HoldingsPane,
  ]);

  return (
    <div className={tokenCardStyles.root} style={tokenCardStylesMap.container}>
      <div style={{ ...tokenCardStylesMap.header, ...tokenCardStylesMap.row(headerOpacity) }}>
        <TokenHeader owner={token.owner} valuation={token.valuation} />
      </div>
      <div style={tokenCardStylesMap.row(bioOpacity)}>
        <TokenBio bio={token.owner.bio} />
      </div>
      <div style={tokenCardStylesMap.row(controlOpacity)}>
        <SegmentControl currentSegment={segment} />
      </div>
      <div style={tokenCardStylesMap.row(listOpacity)}>
        <HolderList
          holders={token.holders}
          holdings={token.holdings}
          segment={segment}
        />
      </div>
    </div>
  );
};

const useSectionOpacity = (
  lightFocus: TokenComponent[] | undefined,
  componentTargets: TokenComponent[]
) => {
  return useMemo(() => {
    if (!lightFocus || lightFocus.length === 0) {
      return 1;
    }

    if (lightFocus.includes(TokenComponent.Entire)) {
      return 1;
    }

    return componentTargets.some((component) => lightFocus.includes(component))
      ? 1
      : 0.25;
  }, [lightFocus, componentTargets]);
};

const tokenCardStylesMap = {
  container: {
    width: 1280,
    borderRadius: 72,
    background: "var(--token-card-background)",
    padding: "96px 120px",
    boxShadow: "var(--token-card-shadow)",
    display: "flex",
    flexDirection: "column" as const,
    gap: 64,
  },
  header: {
    width: "100%",
  },
  row: (opacity: number) => ({
    opacity,
    transition: "opacity 200ms ease",
  }),
};
