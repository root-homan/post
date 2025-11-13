import React from "react";

import { getInitials } from "../../utils/strings";
import avatarStyles from "./Avatar.module.css";

interface AvatarProps {
  name: string;
  profileSrc?: string;
  size?: number;
  borderColor?: string;
  borderWidth?: number;
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  profileSrc,
  size,
  borderColor,
  borderWidth,
}) => {
  const initials = getInitials(name);
  const containerStyle = createContainerStyle(size, borderWidth, borderColor);

  return (
    <div className={avatarStyles.root} style={containerStyle}>
      {profileSrc ? (
        <img
          src={profileSrc}
          alt={name}
          style={baseStyles.image}
          loading="lazy"
        />
      ) : (
        <div style={baseStyles.fallback}>
          <span>{initials}</span>
        </div>
      )}
    </div>
  );
};

const baseStyles = {
  image: {
    width: "100%",
    height: "100%",
    objectFit: "cover" as const,
    display: "block",
  },
  fallback: {
    width: "100%",
    height: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Sohne, Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    fontWeight: "var(--avatar-fallback-font-weight)",
    color: "var(--avatar-fallback-color)",
    background: "var(--avatar-fallback-background)",
  },
};

const createContainerStyle = (
  size?: number,
  borderWidth?: number,
  borderColor?: string
) => ({
  width: size ?? "var(--avatar-size)",
  height: size ?? "var(--avatar-size)",
  borderRadius: size ? size / 2 : "calc(var(--avatar-size) / 2)",
  overflow: "hidden" as const,
  position: "relative" as const,
  border: `${borderWidth ?? "var(--avatar-border-width)"} solid ${borderColor ?? "var(--avatar-border-color)"}`,
});
