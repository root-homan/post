import { CameraPosition, Segment, TokenSceneInput } from "./types";

export const TOKEN_SCENE_PREVIEW_PROPS: TokenSceneInput = {
  token: {
    id: "alice-token",
    valuation: 10_000_000,
    owner: {
      name: "Alice",
      profileSrc:
        "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=200&q=80",
      bio: "i <3 design and storytelling.",
    },
    holders: [
      {
        entity: {
          name: "_self",
          profileSrc:
            "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=200&q=80",
        },
        percentageEquity: 99,
      },
      {
        entity: {
          name: "Bob",
          profileSrc:
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=200&q=80",
        },
        percentageEquity: 1,
      },
    ],
    holdings: [
      {
        entity: {
          name: "StoryLab",
          profileSrc:
            "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=200&q=80",
        },
        percentageEquity: 35,
        valuation: 3_500_000,
      },
      {
        entity: {
          name: "Narrative Ventures",
          profileSrc:
            "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=200&q=80",
        },
        percentageEquity: 15,
        valuation: 1_500_000,
      },
    ],
  },
  isExpanded: true,
  currentSegment: Segment.Holders,
  defaultSegment: Segment.Holders,
  annotations: [
    { label: "Owner profile", index: 0 },
    { label: "Bio snippet", index: 1 },
    { label: "Focus on holders", index: 3 },
  ],
  lightFocus: [],
  cameraFocus: CameraPosition.Normal,
};
