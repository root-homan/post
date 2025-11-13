import React from "react";

import { getInitials } from "../../utils/strings";
import avatarStyles from "./Avatar.module.css";

interface AvatarProps {
  name: string;
  profileSrc?: string;
  size?: number;
  borderColor?: string;
  borderWidth?: number;
  variant?: "header" | "list"; // Use header or list avatar size
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  profileSrc,
  size,
  borderColor,
  borderWidth,
  variant = "header",
}) => {
  const initials = getInitials(name);
  const containerStyle = createContainerStyle(size, borderWidth, borderColor, variant);

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
  borderColor?: string,
  variant: "header" | "list" = "header"
) => {
  const sizeVar = variant === "header" ? "var(--avatar-size-header)" : "var(--avatar-size-list)";
  
  // If size is provided as a number, calculate border width automatically
  if (size && !borderWidth) {
    borderWidth = size / 20; // Automatically scale: 80px -> 4px
  }
  
  return {
    width: size ?? sizeVar,
    height: size ?? sizeVar,
    borderRadius: size ? size / 2 : `calc(${sizeVar} / 2)`,
    overflow: "hidden" as const,
    position: "relative" as const,
    border: borderWidth 
      ? `${borderWidth}px solid ${borderColor ?? "var(--avatar-border-color)"}` 
      : `calc(${sizeVar} / var(--avatar-border-width-ratio)) solid ${borderColor ?? "var(--avatar-border-color)"}`,
  };
};
