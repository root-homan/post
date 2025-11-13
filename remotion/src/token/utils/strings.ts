const WHITESPACE_REGEX = /\s+/;

export const getInitials = (name: string): string => {
  if (!name) {
    return "?";
  }

  const parts = name.trim().split(WHITESPACE_REGEX).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  const [first, last] = [parts[0], parts[parts.length - 1]];
  return `${first[0]}${last[0]}`.toUpperCase();
};

export const deriveHandle = (name: string): string => {
  if (!name) {
    return "@unknown";
  }

  const normalized = name
    .trim()
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .split(WHITESPACE_REGEX)
    .filter(Boolean)
    .join("");

  return normalized ? `@${normalized}` : "@unknown";
};
