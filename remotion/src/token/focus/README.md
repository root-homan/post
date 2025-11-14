# Focus System

A simple, decoupled spotlight/focus system for Remotion scenes.

## Overview

This system allows you to spotlight specific regions of your scene by:

1. **Dimming** everything except specified rectangular regions
2. **Centering** the camera on a single region (when only one region is focused)

## Components

### `FocusOverlay`

Creates a dark overlay with "holes" (spotlights) for focused regions.

### `CameraView`

Wraps content and smoothly moves the camera to center single focused regions.

### `Region` Type

```typescript
type Region = {
  x: number; // pixels from left
  y: number; // pixels from top
  width: number; // pixels
  height: number; // pixels
};
```

## Usage

### 1. Wrap your scene content

```typescript
import { CameraView, FocusOverlay, Region } from "./focus";

// Define regions
const regions: Region[] = [{ x: 400, y: 450, width: 1120, height: 550 }];

return (
  <AbsoluteFill>
    <CameraView regions={regions} duration={30}>
      {/* Your scene content */}
    </CameraView>
    <FocusOverlay regions={regions} duration={30} />
  </AbsoluteFill>
);
```

### 2. Control focus timing

```typescript
const frame = useCurrentFrame();
const focusRegions = frame >= 120 ? HOLDER_REGIONS : [];
```

### 3. Multiple regions

```typescript
// Focus multiple areas simultaneously
const regions: Region[] = [
  { x: 100, y: 50, width: 800, height: 120 }, // Header
  { x: 50, y: 300, width: 400, height: 200 }, // Holder 1
  { x: 50, y: 520, width: 400, height: 200 }, // Holder 2
];
```

## Behavior

- **Empty array**: No focus, normal view
- **One region**: Spotlight + camera centers on that region
- **Multiple regions**: Spotlight on all, camera stays in original position

## Animation

Both components use Remotion's spring animations with these settings:

- `damping: 200`
- `mass: 0.5`
- Default `duration: 30` frames (~1 second at 30fps)

## Tips

### Finding Region Coordinates

1. Use browser dev tools on the rendered scene
2. Inspect elements to find their bounding boxes
3. Use those coordinates in your Region definitions

### Timing Your Focuses

Calculate when other animations complete:

```typescript
const FOCUS_START = EXPAND_DELAY + EXPAND_DURATION + 15;
```

### Smooth Transitions

Keep `duration` consistent between all focus changes for smooth, predictable animations.
