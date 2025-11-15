export interface Word {
  word: string;
  start: number; // seconds
  end: number; // seconds
}

export interface WordGroup {
  words: Word[];
  start: number;
  end: number;
}

export interface Grouping {
  indices: number[];
  text: string;
}

export interface GroupingFile {
  groups: Grouping[];
}

export interface CaptionData {
  groups: Word[][];
  videoWidth: number;
  videoHeight: number;
  fps: number;
  durationInFrames: number;
}
