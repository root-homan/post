import { CaptionData } from "./types";

// Sample caption data for preview
// Replace this with your actual grouping data when previewing
export const PREVIEW_DATA: CaptionData = {
  groups: [
    [
      { word: "Great", start: 0.14, end: 0.32 },
      { word: "ideas", start: 0.32, end: 0.62 },
      { word: "change", start: 0.62, end: 1.06 },
    ],
    [
      { word: "the", start: 1.06, end: 1.46 },
      { word: "world.", start: 1.46, end: 1.82 },
    ],
    [
      { word: "Our", start: 2.02, end: 2.14 },
      { word: "progress", start: 2.14, end: 2.62 },
      { word: "literally", start: 2.62, end: 3.12 },
      { word: "depends", start: 3.12, end: 3.56 },
    ],
    [
      { word: "on", start: 3.56, end: 3.68 },
      { word: "them.", start: 3.68, end: 4.04 },
    ],
    [
      { word: "But", start: 4.32, end: 4.54 },
      { word: "where", start: 4.54, end: 4.78 },
      { word: "do", start: 4.78, end: 4.9 },
      { word: "they", start: 4.9, end: 5.04 },
    ],
    [
      { word: "come", start: 5.04, end: 5.38 },
      { word: "from?", start: 5.38, end: 5.9 },
    ],
  ],
  videoWidth: 3840,
  videoHeight: 2160,
  fps: 23.976,
  durationInFrames: 144, // ~6 seconds at 24fps
};

// Helper: Load your own grouping data for preview
// Copy this file, uncomment below, and paste your grouping JSON:
/*
import myGrouping from '../../path/to/your-grouping.json';

export const PREVIEW_DATA: CaptionData = {
  groups: myGrouping.groups,
  videoWidth: 3840,
  videoHeight: 2160,
  fps: 23.976,
  durationInFrames: 2502, // Adjust to match your video
};
*/
