export enum Segment {
  Holders = "holders",
  Holdings = "holdings",
}

export enum TokenComponent {
  Entire = "entire",
  Name = "name",
  Valuation = "valuation",
  Bio = "bio",
  HoldersPane = "holdersPane",
  HoldingsPane = "holdingsPane",
  FirstHolder = "firstHolder",
  FirstHolding = "firstHolding",
  SecondHolder = "secondHolder",
  SecondHolding = "secondHolding",
}

export enum CameraPosition {
  Long = "long",
  Normal = "normal",
}

export interface Entity {
  name: string;
  profileSrc?: string;
  bio?: string;
}

export interface Holder {
  entity: Entity;
  percentageEquity: number;
}

export interface Holding {
  entity: Entity;
  percentageEquity: number;
  valuation: number;
}

export interface Token {
  id: string;
  owner: Entity;
  valuation: number;
  holders: Holder[];
  holdings: Holding[];
}

export interface Annotation {
  label: string;
  index: number;
}

export type LightFocus = TokenComponent[];

export type CameraFocus = CameraPosition | TokenComponent;

export interface TokenSceneInput {
  token: Token | null;
  isExpanded: boolean;
  currentSegment: Segment;
  defaultSegment: Segment;
  annotations?: Annotation[];
  lightFocus?: LightFocus;
  cameraFocus?: CameraFocus;
  showSegmentControl?: boolean;
}

export interface CompanySceneInput
  extends Omit<
    TokenSceneInput,
    "currentSegment" | "defaultSegment" | "showSegmentControl"
  > {
  currentSegment?: Segment;
  defaultSegment?: Segment;
  showSegmentControl?: boolean;
}
