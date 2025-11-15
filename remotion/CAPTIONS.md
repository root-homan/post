# Caption System Documentation

## Overview

The caption system renders animated captions with:

- **Drop animation** (6px, 400ms) when a line appears
- **Karaoke sweep effect** - moving light across words based on timing

## Architecture

### Input Files (Separate)

1. **Words JSON** (`video-draft.json`) - from Whisper transcription:

```json
[
  { "word": "Hello", "start": 0.5, "end": 0.8 },
  { "word": "everyone", "start": 0.85, "end": 1.3 },
  { "word": "today", "start": 1.9, "end": 2.2 }
]
```

2. **Grouping JSON** (`video-draft-grouping.json`) - human-editable:

```json
{
  "groups": [
    { "indices": [0, 1], "text": "Hello everyone" },
    { "indices": [2, 3, 4], "text": "today we're talking" }
  ]
}
```

### Components

**CaptionComposition** (`CaptionComposition.tsx`)

- Entry point for CLI rendering
- Receives pre-merged data from Python
- Simple wrapper that passes data to CaptionScene
- Note: Merge happens in Python because Remotion can't access filesystem

**CaptionScene** (`CaptionScene.tsx`)

- Receives merged word groups
- Handles line-level timing and positioning
- Animates drop effect
- Renders Word components

**Word** (`Word.tsx`)

- Individual word rendering
- Implements karaoke sweep animation
- Opacity transitions based on timing

## Rendering Process

1. **Python loads and merges files:**

```python
words = load_words_from_json(words_json)
groupings = load_grouping(grouping_json)
merged = [
  [words[idx] for idx in group['indices']]
  for group in groupings
]
```

2. **Python calls Remotion with merged data:**

```bash
npx remotion render CaptionComposition output.mov \
  --props '{"groups": [...], "videoWidth": 1920, ...}'
```

3. **CaptionComposition passes data to CaptionScene**

4. **CaptionScene renders with animations**

5. **ffmpeg composites onto video:**

```bash
ffmpeg -i original.mp4 -i captions.mov \
  -filter_complex "[0:v][1:v]overlay" output.mp4
```

## Editing Workflow

### Adjust Word Groupings

Edit `video-draft-grouping.json`:

```json
{
  "groups": [{ "indices": [0, 1, 2], "text": "Hello everyone today" }]
}
```

Run: `post -captions` → Uses new grouping immediately

### Adjust Word Timing

Edit `video-draft.json`:

```json
[{ "word": "Hello", "start": 0.5, "end": 0.85 }]
```

Run: `post -captions` → Karaoke timing updates

## Benefits of Separation

✅ **Clean separation** - word timing separate from grouping decisions  
✅ **Human-readable groupings** - JSON with indices and text preview  
✅ **Independent edits** - change timing OR grouping separately  
✅ **No regeneration needed** - edit grouping JSON and re-render  
✅ **Merge in Python** - avoids filesystem issues in Remotion

## Animation Details

**Drop Animation:**

- Distance: 6px
- Duration: 400ms
- Easing: cubic ease-out
- Only for lines ≥ 500ms duration

**Karaoke Sweep:**

- Light width: 70% of line width
- Active opacity: 100%
- Inactive opacity: 67.5%
- Sweeps linearly across word positions over line duration

## Composition Registry

Root.tsx registers three caption compositions:

1. **CaptionComposition** - Production (receives merged data from Python)
2. **CaptionScene** - Direct rendering (can be used standalone)
3. **CaptionScenePreview** - Preview with black background for visibility
