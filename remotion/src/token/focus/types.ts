export type Region = {
  x: number; // pixels from left
  y: number; // pixels from top
  width: number; // pixels
  height: number; // pixels
};

export type FocusState = {
  regions: Region[];
  startFrame: number; // when to start the focus
  duration: number; // how long the transition takes (in frames)
};
