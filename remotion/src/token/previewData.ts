import { CameraPosition, Segment, TokenSceneInput } from "./types";

export const TOKEN_SCENE_PREVIEW_PROPS: TokenSceneInput = {
  token: {
    id: "alice-token",
    valuation: 10_000_000,
    owner: {
      name: "Alice",
      profileSrc:
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80&sat=-100",
      bio: "i <3 design, storytelling & exploring interesting ideas.",
    },
    holders: [
      {
        entity: {
          name: "_self",
          profileSrc:
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80&sat=-100",
        },
        percentageEquity: 99,
      },
      {
        entity: {
          name: "Bob",
          profileSrc:
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80&sat=-100",
        },
        percentageEquity: 1,
      },
    ],
    holdings: [
      {
        entity: {
          name: "StoryLab",
          profileSrc:
            "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=400&q=80&sat=-100",
        },
        percentageEquity: 35,
        valuation: 3_500_000,
      },
      {
        entity: {
          name: "Narrative Ventures",
          profileSrc:
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80&sat=-100",
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
