import React from "react";

import { Holder, Holding, Segment } from "../../types";
import { HolderRow } from "../HolderRow/HolderRow";
import holderListStyles from "./HolderList.module.css";

interface HolderListProps {
  holders: Holder[];
  holdings: Holding[];
  segment: Segment;
}

export const HolderList: React.FC<HolderListProps> = ({
  holders,
  holdings,
  segment,
}) => {
  const isHoldersSegment = segment === Segment.Holders;
  const items = isHoldersSegment ? sortHolders(holders) : sortHoldings(holdings);

  return (
    <div className={holderListStyles.root} style={holderListStylesMap.container}>
      {items.map((item, index) => (
        <HolderRow
          key={`${item.entity.name}-${index}`}
          entity={item.entity}
          percentageEquity={item.percentageEquity}
          valuation={!isHoldersSegment ? (item as Holding).valuation : undefined}
          index={index}
        />
      ))}
    </div>
  );
};

const holderListStylesMap = {
  container: {
    width: "100%",
    display: "flex",
    flexDirection: "column" as const,
    gap: "var(--spacing-unit)", // <S> - matches all other internal spacing
  },
};

const sortHolders = (holders: Holder[]) =>
  [...holders].sort((a, b) => b.percentageEquity - a.percentageEquity);

const sortHoldings = (holdings: Holding[]) =>
  [...holdings].sort(
    (a, b) => b.percentageEquity * b.valuation - a.percentageEquity * a.valuation
  );
