# Previewing Captions in Browser

## Quick Start

```bash
cd ~/bin/post/remotion
npm start
```

This opens a browser preview where you can:
- ✨ See captions render in real-time
- 🎨 Edit styles and see instant updates
- 🎬 Scrub through the timeline
- 🔍 Inspect each frame

## Using Your Real Caption Data

The preview uses sample data from `src/PreviewData.ts`. To preview your actual video captions:

### Option 1: Quick Preview (for testing styles)
Just use the sample data - it's enough to see how animations look.

### Option 2: Load Your Real Data

Edit `src/PreviewData.ts`:

```typescript
import { CaptionData } from './types';

// Copy your grouping JSON content here
export const PREVIEW_DATA: CaptionData = {
  groups: [
    // ... paste your groups from intro-1-rough-tight-grouping.json
  ],
  videoWidth: 3840,
  videoHeight: 2160,
  fps: 23.976,
  durationInFrames: 2502,
};
```

Or load from file (if you're comfortable with TypeScript imports):

```typescript
import grouping from '../../../code/videos/0-intro/poop/intro-1-rough-tight-grouping.json';

export const PREVIEW_DATA: CaptionData = {
  groups: grouping.groups,
  videoWidth: 3840,
  videoHeight: 2160,
  fps: 23.976,
  durationInFrames: 2502,
};
```

## Workflow for Styling

1. **Start preview**: `npm start`
2. **Open browser**: Opens automatically at http://localhost:3000
3. **Edit components**: 
   - `src/CaptionScene.tsx` - Layout, positioning, font size
   - `src/Word.tsx` - Word animations, opacity
4. **See changes**: Save file → browser auto-refreshes
5. **Iterate fast**: No need to render full video!

## Keyboard Shortcuts in Preview

- **Space**: Play/pause
- **←/→**: Previous/next frame
- **J/K/L**: Rewind/pause/fast-forward
- **I/O**: Set in/out points

## Tips

- Use checkerboard background to see transparency
- Scrub slowly through animations to fine-tune timing
- Try different parts of your video by adjusting `PREVIEW_DATA`
- When happy with styles, just run `post -captions` to render!

