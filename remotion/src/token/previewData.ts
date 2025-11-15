import {
  CameraPosition,
  CompanySceneInput,
  PersonalTokenSceneInput,
  Segment,
  TokenSceneInput,
} from "./types";
import { ALICE_IDENTITY } from "./characters";

export const TOKEN_SCENE_PREVIEW_PROPS: TokenSceneInput = {
  token: {
    id: "alice-token",
    valuation: 10_000_000,
    owner: ALICE_IDENTITY,
    holders: [
      {
        entity: ALICE_IDENTITY,
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
        companyValuation: 10_000_000,
      },
      {
        entity: {
          name: "Narrative Ventures",
          profileSrc:
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80&sat=-100",
        },
        percentageEquity: 15,
        companyValuation: 5_000_000,
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

export const COMPANY_SCENE_PREVIEW_PROPS: CompanySceneInput = {
  token: {
    id: "acme-company-token",
    valuation: 42_000_000,
    owner: {
      name: "Acme",
      bio: "Acme is deploying autonomous build crews to deliver high-quality, affordable homes at scale.",
    },
    holders: [
      {
        entity: {
          name: "Naila Peretz",
          profileSrc:
            "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 32,
      },
      {
        entity: {
          name: "Luis Andrade",
          profileSrc:
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 24,
      },
      {
        entity: {
          name: "Jun Park",
          profileSrc:
            "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 18,
      },
      {
        entity: {
          name: "Aurora Forge",
          profileSrc:
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 15,
      },
      {
        entity: {
          name: "Habitat Seed Fund",
        },
        percentageEquity: 11,
      },
    ],
    holdings: [],
  },
  isExpanded: true,
  currentSegment: Segment.Holders,
  defaultSegment: Segment.Holders,
  showSegmentControl: false,
  annotations: [
    { label: "Company identity", index: 0 },
    { label: "Ambitious mission", index: 1 },
    { label: "Shareholder roster", index: 3 },
  ],
  lightFocus: [],
  cameraFocus: CameraPosition.Normal,
};

export const PERSONAL_TOKEN_SCENE_PROPS: PersonalTokenSceneInput = {
  token: {
    id: "alice-personal-token",
    valuation: 100_000_000,
    owner: ALICE_IDENTITY,
    holders: [
      {
        entity: {
          ...ALICE_IDENTITY,
          name: "Alice (self)",
        },
        percentageEquity: 93,
      },
      {
        entity: {
          name: "Maya",
          profileSrc:
            "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 4,
      },
      {
        entity: {
          name: "Dan",
          profileSrc:
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 2,
      },
      {
        entity: {
          name: "Bob",
          profileSrc:
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
        },
        percentageEquity: 1,
      },
    ],
    holdings: [
      {
        entity: {
          name: "Alpha",
        },
        percentageEquity: 4,
        companyValuation: 200_000_000, // 4% of 200M = 8M
      },
      {
        entity: {
          name: "Beta",
        },
        percentageEquity: 3,
        companyValuation: 200_000_000, // 3% of 200M = 6M
      },
      {
        entity: {
          name: "Gamma",
        },
        percentageEquity: 3,
        companyValuation: 100_000_000, // 3% of 100M = 3M
      },
      {
        entity: {
          name: "Delta",
        },
        percentageEquity: 1,
        companyValuation: 100_000_000, // 1% of 100M = 1M
      },
    ],
  },
  annotations: [
    { label: "Alice's identity", index: 0 },
    { label: "Token bio", index: 1 },
  ],
  lightFocus: [],
  cameraFocus: CameraPosition.Normal,
  showSegmentControl: true,
};
