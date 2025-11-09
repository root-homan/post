# Remotion Caption Setup

## First-Time Setup

The dependencies will be installed automatically the first time you run `post -captions`. 

If you want to install them manually:

```bash
cd ~/bin/post/remotion
npm install
```

## Requirements

- **Node.js** >= 18.0.0
- **npm** (comes with Node.js)
- **ffmpeg** (for final video overlay)

Check your Node.js version:
```bash
node --version
```

If you need to install Node.js, use [nvm](https://github.com/nvm-sh/nvm):
```bash
nvm install 18
nvm use 18
```

## How It Works

1. **Python (`captions.py`)** orchestrates the pipeline:
   - Loads word timestamps from JSON
   - Calls GPT-5 for intelligent grouping
   - Calls Remotion to render caption video

2. **Remotion** renders captions as ProRes 4444 video with alpha channel:
   - Transparent background
   - White text with animations
   - Drop-in effects and karaoke highlighting

3. **ffmpeg** overlays the caption video onto the main video

## Output Files

When you run `post -captions`, you'll get:

- `*-rough-tight-captions.mp4` - Final video with captions
- `*-rough-tight-captions-only.mov` - Caption-only video (ProRes with transparency)
- `*-rough-tight-grouping.json` - Word grouping (cached for reuse)

## Workflow

```bash
# Standard workflow (will reuse existing grouping)
post -captions --yes

# Force new grouping (delete grouping file first)
rm *-grouping.json
post -captions

# Or decline to reuse when prompted
post -captions
# Answer 'n' when asked about reusing grouping
```

## Customizing Animations

Edit these files to customize caption appearance:

- `src/CaptionScene.tsx` - Overall layout, positioning, font size
- `src/Word.tsx` - Individual word animations, opacity transitions
- Constants at the top of each file control animation parameters

After editing, the changes will be used automatically on the next `post -captions` run.

## Previewing in Browser

To preview captions during development:

```bash
cd ~/bin/post/remotion
npm start
```

This opens a browser where you can:
- See captions render in real-time
- Scrub through the timeline
- Edit code and see instant updates

Note: You'll need to provide sample props by editing `Root.tsx` temporarily for preview.

