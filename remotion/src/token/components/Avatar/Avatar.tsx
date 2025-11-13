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
  size = 128,
  borderColor = "rgba(255, 255, 255, 0.32)",
  borderWidth = 4,
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
    fontWeight: 600,
    color: "var(--avatar-initial-color, #2b2f37)",
    background:
      "var(--avatar-background, linear-gradient(135deg, #f2f4f8 0%, #e2e6ef 100%))",
  },
};

const createContainerStyle = (
  size: number,
  borderWidth: number,
  borderColor: string
) => ({
  width: size,
  height: size,
  borderRadius: size / 2,
  overflow: "hidden" as const,
  position: "relative" as const,
  border: `${borderWidth}px solid ${borderColor}`,
  boxShadow: "var(--avatar-shadow, 0 10px 30px rgba(15, 25, 40, 0.12))",
});
