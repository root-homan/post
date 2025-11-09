# Caption Rendering with Remotion

This directory contains the Remotion-based caption rendering engine for the `post` video pipeline.

## Overview

The captions are rendered as a separate video with transparency (ProRes 4444), which is then overlaid onto the main video using ffmpeg. This provides:

- **Modern styling** using React/CSS instead of ASS subtitle format
- **Smooth animations** with drop-in effects and karaoke-style highlighting
- **Type safety** with TypeScript
- **Easy iteration** via browser preview during development

## Architecture

- **CaptionScene.tsx**: Main composition that renders all caption lines
- **Word.tsx**: Individual word component with opacity animations
- **types.ts**: TypeScript interfaces for caption data

## Usage

This is called automatically by `post -captions`. You don't need to run Remotion directly.

## Development

To preview captions during development:

```bash
npm install
npm start
```

Then edit the components and refresh to see changes.

## Animation Parameters

Key constants you can adjust in the React components:

- `DROP_DISTANCE`: How far captions drop from (in pixels)
- `ANIMATION_DURATION_MS`: Duration of drop animation
- `MIN_WORD_DURATION_FOR_KARAOKE_MS`: Minimum word duration for karaoke effect
- `KARAOKE_FADE_BACK_MS`: Speed of opacity fade-back

## Dependencies

- Node.js >= 18
- Remotion 4.x
- React 18

