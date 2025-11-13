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
    margin: 0, // Remove default <p> margins
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: "var(--token-bio-font-size)",
    fontWeight: "var(--token-bio-font-weight)",
    color: "var(--token-bio-color)",
    letterSpacing: "var(--token-bio-letter-spacing)",
    lineHeight: "var(--token-bio-line-height)",
  },
};
