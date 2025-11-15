import React from "react";

import { Holder, Holding, Segment, SegmentAnimation } from "../../types";
import { HolderRow } from "../HolderRow/HolderRow";
import { HoldingRow } from "../HoldingRow/HoldingRow";
import holderListStyles from "./HolderList.module.css";

interface HolderListProps {
  holders: Holder[];
  holdings: Holding[];
  segment: Segment;
  segmentAnimation?: SegmentAnimation;
}

export const HolderList: React.FC<HolderListProps> = ({
  holders,
  holdings,
  segment,
  segmentAnimation,
}) => {
  // Determine which segment to display (instantaneous switch at 50% if animating)
  const displaySegment = segmentAnimation
    ? segmentAnimation.progress < 0.5
      ? segmentAnimation.from
      : segmentAnimation.to
    : segment;

  return (
    <div className={holderListStyles.root} style={holderListStylesMap.list}>
      {renderItems(holders, holdings, displaySegment)}
    </div>
  );
};

const renderItems = (
  holders: Holder[],
  holdings: Holding[],
  segment: Segment
) => {
  if (segment === Segment.Holders) {
    return sortHolders(holders).map((holder, index) => (
      <HolderRow
        key={`holder-${holder.entity.name}-${index}`}
        entity={holder.entity}
        percentageEquity={holder.percentageEquity}
        index={index}
      />
    ));
  }

  return sortHoldings(holdings).map((holding, index) => (
    <HoldingRow
      key={`holding-${holding.entity.name}-${index}`}
      entity={holding.entity}
      percentageEquity={holding.percentageEquity}
      companyValuation={holding.companyValuation}
    />
  ));
};

const holderListStylesMap = {
  list: {
    width: "100%",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--spacing-unit)",
  },
};

const sortHolders = (holders: Holder[]) =>
  [...holders].sort((a, b) => b.percentageEquity - a.percentageEquity);

const sortHoldings = (holdings: Holding[]) =>
  [...holdings].sort(
    (a, b) =>
      b.percentageEquity * b.companyValuation -
      a.percentageEquity * a.companyValuation
  );
