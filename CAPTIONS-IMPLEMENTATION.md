# Caption System Implementation Summary

## What We Built

A clean, two-file caption system where:

1. **Word-level timestamps** (rarely change) are separate from
2. **Word groupings** (easy to tweak)
3. **Python merges them** and passes merged data to Remotion

## Key Changes

### Python (`modules/captions.py`)

**Changed:**

- ✅ Works with `*-draft.mp4` files (not `*-rough-tight.mp4`)
- ✅ Added `--file` argument to specify custom files
- ✅ Checks for transcript JSON from `-transcribe` first
- ✅ Saves groupings as JSON with `indices` and `text` fields
- ✅ Calls Remotion render with both file paths
- ✅ Composites caption video over original with ffmpeg

**Removed:**

- ❌ All ASS subtitle code (`format_ass_time`, `create_ass_subtitles`)
- ❌ All direct ffmpeg subtitle burning (`burn_captions_with_ffmpeg`)

### Remotion

**New Files:**

- `CaptionComposition.tsx` - Wrapper that receives merged data from Python
- `example-grouping.json` - Example grouping format
- `CAPTIONS.md` - Architecture documentation

**Updated:**

- `types.ts` - Added `Grouping`, `GroupingFile` types
- `Root.tsx` - Registered `CaptionComposition` for CLI rendering
- `captions-guidelines.md` - Updated to ask GPT for new format with indices + text

## File Format

### Grouping File (`*-draft-grouping.json`)

```json
{
  "groups": [
    {
      "indices": [0, 1, 2],
      "text": "Hello everyone today"
    },
    {
      "indices": [3, 4],
      "text": "we're talking"
    }
  ]
}
```

- `indices` - Word positions (0-based) from transcript
- `text` - Human-readable preview (not used by renderer)

## Workflow

### First Run

```bash
post -captions
```

1. Finds `video-draft.mp4`
2. Checks for `video-draft.json` → Error if missing
3. Checks for `video-draft-grouping.json` → Missing
4. Calls GPT-5-mini to generate groupings
5. Saves grouping JSON
6. Renders with Remotion
7. Composites over original video
8. Output: `video-draft-captions.mp4`

### After Manual Edits

```bash
# Edit video-draft-grouping.json
# Change: {"indices": [0, 1, 2]} → {"indices": [0, 1]}

post -captions
```

1. Finds existing grouping
2. Prompts: "Reuse existing? [Y/n]" → Y
3. **Python loads and merges files**
4. Renders with Remotion (receives merged data)
5. Output updated immediately

## Benefits

✅ **Python does merge** - Avoids filesystem issues in Remotion  
✅ **Human-readable** - JSON with text preview  
✅ **Easy tweaking** - Edit indices, re-run  
✅ **Fast iteration** - No GPT calls after first run  
✅ **Clean separation** - Timing ≠ Grouping  
✅ **GPT returns full format** - With indices AND text for readability

## Technical Details

**Remotion Render Command:**

```bash
npx remotion render CaptionComposition output.mov \
  --props '{
    "groups": [
      [
        {"word": "Hello", "start": 0.5, "end": 0.8},
        {"word": "everyone", "start": 0.85, "end": 1.3}
      ]
    ],
    "videoWidth": 1920,
    "videoHeight": 1080,
    "fps": 30,
    "durationInFrames": 900
  }'
```

Note: Python loads the separate files, merges them, and passes the merged data.

**Compositing Command:**

```bash
ffmpeg -i video-draft.mp4 -i captions.mov \
  -filter_complex "[0:v][1:v]overlay" \
  -c:v h264_videotoolbox -q:v 55 \
  video-draft-captions.mp4
```

## Animation Features

- **Drop:** 6px over 400ms with cubic ease-out
- **Karaoke:** Sweeping light (70% width) across words
- **Smart effects:** Only enabled for lines ≥ 500ms
- **Positioning:** 27% from bottom, centered

## Files Modified

**Python:**

- `post/modules/captions.py` (complete rewrite)

**Remotion:**

- `remotion/src/types.ts` (added new types)
- `remotion/src/CaptionComposition.tsx` (new)
- `remotion/src/Root.tsx` (registered new composition)
- `remotion/example-grouping.json` (new)
- `remotion/CAPTIONS.md` (new)

**Documentation:**

- `post/README.md` (updated captions section)
- `post/CAPTIONS-IMPLEMENTATION.md` (this file)

## Testing Checklist

- [ ] Run `post -captions` on a `-draft.mp4` file
- [ ] Verify grouping JSON is created
- [ ] Edit grouping JSON manually
- [ ] Re-run and verify changes appear
- [ ] Test `--file` argument with custom path
- [ ] Verify error when transcript JSON is missing
- [ ] Check final video has captions with animations
