import React from "react";

import bioStyles from "./TokenBio.module.css";

interface TokenBioProps {
  bio?: string;
}

export const TokenBio: React.FC<TokenBioProps> = ({ bio }) => {
  if (!bio) {
    return null;
  }

  return (
    <p className={bioStyles.root} style={bioStylesMap.container}>
      {bio}
    </p>
  );
};

const bioStylesMap = {
  container: {
    width: "100%",
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 48,
    fontWeight: 450,
    color: "var(--token-bio-color)",
    letterSpacing: "-0.01em",
    lineHeight: 1.35,
  },
};
