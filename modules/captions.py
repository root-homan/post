import subprocess
import json
from pathlib import Path

try:
    from .common import StageEnvironment, build_cli_parser, call_gpt5
except ImportError:
    from common import StageEnvironment, build_cli_parser, call_gpt5


def load_words_from_json(json_path: Path):
    """
    Load word-level timing information from JSON file.
    
    Returns a list of dictionaries with keys: 'word', 'start', 'end'
    Times are in seconds (float).
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        words = json.load(f)
    
    # Filter out empty words
    words = [w for w in words if w.get('word', '').strip()]
    
    return words


def generate_groupings_with_gpt(words):
    """
    Group words into caption lines using GPT-5-mini for intelligent semantic grouping.
    
    Returns a list of grouping objects with 'indices' and 'text' fields.
    """
    if not words:
        return []
    
    # Prepare the transcript with word indices, text, and timing for GPT-5
    word_list = []
    for i, word in enumerate(words):
        start_time = word['start']
        end_time = word['end']
        duration = end_time - start_time
        # Calculate gap to next word if it exists
        if i < len(words) - 1:
            gap = words[i + 1]['start'] - end_time
            word_list.append(f"{i}: '{word['word']}' [{start_time:.2f}s - {end_time:.2f}s, duration: {duration:.2f}s, gap to next: {gap:.2f}s]")
        else:
            word_list.append(f"{i}: '{word['word']}' [{start_time:.2f}s - {end_time:.2f}s, duration: {duration:.2f}s]")
    
    transcript_text = '\n'.join(word_list)
    
    # Read the captions guidelines
    guidelines_path = Path(__file__).parent / "captions-guidelines.md"
    if not guidelines_path.exists():
        raise RuntimeError(f"Captions guidelines not found at '{guidelines_path}'")
    
    try:
        system_prompt = guidelines_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to read captions guidelines: {e}")
    
    user_prompt = f"Please group these transcript words into optimal caption lines, considering both timing and meaning:\n\n{transcript_text}"
    
    print(f"🤖 Calling GPT-5-mini to intelligently group {len(words)} words into caption lines...")
    print(f"📤 Sending {len(transcript_text)} characters to GPT...")
    
    try:
        response = call_gpt5(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            model="gpt-5-mini",
            timeout=180  # 3 minutes for longer transcripts
        )
        
        print(f"📥 Received response, parsing JSON...")
        
        # Parse the response
        try:
            response_data = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse GPT response as JSON")
            print(f"   Parse error: {e}")
            print(f"   Raw response: {response[:500]}...")
            raise
        
        # Extract groups array
        if "groups" in response_data:
            groupings = response_data["groups"]
        elif "groupings" in response_data:
            groupings = response_data["groupings"]
        elif "lines" in response_data:
            groupings = response_data["lines"]
        else:
            raise ValueError(f"Expected 'groups' key in response, got: {list(response_data.keys())}")
        
        # Handle both new format (with indices/text) and old format (just arrays)
        result = []
        for group in groupings:
            # New format: {"indices": [0, 1], "text": "..."}
            if isinstance(group, dict) and "indices" in group:
                indices = [idx for idx in group["indices"] if 0 <= idx < len(words)]
                text = group.get("text", "")
                if not text and indices:
                    # Generate text if not provided
                    text = ' '.join(words[idx]['word'] for idx in indices)
                if indices:
                    result.append({
                        "indices": indices,
                        "text": text
                    })
            # Old format: [0, 1, 2]
            elif isinstance(group, list):
                indices = [idx for idx in group if 0 <= idx < len(words)]
                if indices:
                    text = ' '.join(words[idx]['word'] for idx in indices)
                    result.append({
                        "indices": indices,
                        "text": text
                    })
        
        print(f"✅ GPT-5-mini grouped words into {len(result)} caption lines")
        
        # Show a sample of the groupings for verification
        if result:
            sample_count = min(3, len(result))
            print(f"📋 Sample groupings (first {sample_count}):")
            for i in range(sample_count):
                group = result[i]
                print(f"   {i+1}. indices={group['indices']} → \"{group['text']}\"")
        
        return result
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"⚠️  GPT-5-mini grouping failed")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")
        print(f"   Falling back to simple grouping...")
        # Fallback: simple grouping by small chunks
        result = []
        i = 0
        while i < len(words):
            chunk_size = min(4, len(words) - i)
            indices = list(range(i, i + chunk_size))
            text = ' '.join(words[idx]['word'] for idx in indices)
            result.append({
                "indices": indices,
                "text": text
            })
            i += chunk_size
        return result


def get_video_info(video_path: Path):
    """
    Get video dimensions, fps, and duration using ffprobe.
    
    Returns:
        dict with keys: width, height, fps, duration
    """
    try:
        # Get dimensions and fps
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,duration',
            '-of', 'json',
            str(video_path)
        ]
        result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        stream = data['streams'][0]
        
        width = int(stream['width'])
        height = int(stream['height'])
        
        # Parse fps (it's in format "30/1" or "30000/1001")
        fps_parts = stream['r_frame_rate'].split('/')
        fps = int(fps_parts[0]) / int(fps_parts[1])
        
        # Get duration (might be in stream or format)
        duration = float(stream.get('duration', 0))
        if duration == 0:
            # Try format duration
            format_probe = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(video_path)
            ]
            result = subprocess.run(format_probe, check=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration
        }
    except Exception as e:
        raise RuntimeError(f"Failed to get video info: {e}")


def save_grouping(grouping_path: Path, groupings):
    """
    Save the word grouping to a JSON file for reuse.
    
    Args:
        grouping_path: Path to save the grouping JSON
        groupings: List of dicts with 'indices' and 'text' fields
    """
    grouping_data = {
        "groups": groupings
    }
    with open(grouping_path, 'w', encoding='utf-8') as f:
        json.dump(grouping_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved word grouping to '{grouping_path.name}'")


def load_grouping(grouping_path: Path):
    """
    Load a previously saved word grouping from JSON.
    
    Returns:
        List of dicts with 'indices' and 'text' fields
    """
    with open(grouping_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("groups", [])


def render_captions_with_remotion(
    video_path: Path,
    words_json: Path,
    grouping_json: Path,
    video_info: dict,
    output_path: Path
):
    """
    Render captions using Remotion as a standalone file.
    
    Remotion renders a transparent video with animated captions (drop + karaoke effects).
    The output can be composited onto the original video in Final Cut Pro or other editors.
    """
    print(f"🎬 Rendering captions with Remotion...")
    
    # Get the remotion directory
    remotion_dir = Path(__file__).parent.parent / "remotion"
    if not remotion_dir.exists():
        raise RuntimeError(f"Remotion directory not found at '{remotion_dir}'")
    
    # Output will be the caption-only file (absolute path for Remotion)
    caption_output = output_path.absolute()
    
    # Calculate duration in frames
    duration_frames = int(video_info['duration'] * video_info['fps'])
    
    # Load and merge the data in Python (Remotion can't load files directly)
    words = load_words_from_json(words_json)
    groupings = load_grouping(grouping_json)
    
    # Merge: convert indices to actual word objects
    merged_groups = []
    for group in groupings:
        word_group = [words[idx] for idx in group['indices'] if idx < len(words)]
        if word_group:
            merged_groups.append(word_group)
    
    # Build the remotion render command with merged data
    # Remotion expects props wrapped in 'inputProps' key
    props_data = {
        'inputProps': {
            'groups': merged_groups,
            'videoWidth': video_info['width'],
            'videoHeight': video_info['height'],
            'fps': video_info['fps'],
            'durationInFrames': duration_frames
        }
    }
    
    print(f"📊 Rendering with:")
    print(f"   Groups: {len(merged_groups)}")
    print(f"   Dimensions: {video_info['width']}x{video_info['height']}")
    print(f"   FPS: {video_info['fps']}")
    print(f"   Duration: {duration_frames} frames ({video_info['duration']:.2f}s)")
    if merged_groups:
        sample = merged_groups[0][:2] if len(merged_groups[0]) > 2 else merged_groups[0]
        print(f"   Sample words: {[w['word'] for w in sample]}...")
    
    cmd = [
        'npx',
        'remotion',
        'render',
        'CaptionComposition',
        str(caption_output),
        '--codec', 'prores',
        '--prores-profile', '4444',  # ProRes 4444 with alpha channel
        '--pixel-format', 'yuva444p10le',  # Pixel format with alpha channel
        '--props',
        json.dumps(props_data)
    ]
    
    try:
        print(f"  Running: npx remotion render...")
        print(f"  Output file: {caption_output}")
        print()  # Empty line before Remotion output
        
        result = subprocess.run(
            cmd,
            cwd=remotion_dir,
            check=True
        )
        
        print()  # Empty line after Remotion output
        print(f"✅ Remotion render complete")
        
        # Check if the file was actually created
        if not caption_output.exists():
            print(f"❌ Caption file not found at: {caption_output}")
            raise RuntimeError(f"Remotion render completed but caption file not found at {caption_output}")
        
        print(f"✅ Caption file created: {caption_output.name}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Remotion render failed with exit code {e.returncode}")
        raise RuntimeError(f"Remotion render failed")


def run(args):
    """
    Render captions using Remotion with drop + karaoke animations.
    
    Uses Remotion to render animated captions with:
    - Drop animation (6px, 400ms)
    - Karaoke sweep effect (moving light across words)
    
    Outputs a standalone .mov file with transparent background for compositing in video editors.
    
    Dependencies:
        - A draft video `<title>-<take_id>-draft.mp4` must be present (or specify as argument)
        - A matching word timestamps file `<title>-<take_id>-draft.json` from -transcribe must exist
        - Remotion must be set up in the remotion/ directory
        - ffmpeg must be installed and available in PATH
    
    Failure behaviour:
        - Aborts when transcript JSON is missing
        - Prompts before overwriting output unless `--yes` is provided
        - Prompts whether to regenerate grouping if it exists
    
    Output:
        - Produces `<title>-<take_id>-draft-captions.mov` with animated captions (transparent background)
        - Also produces `<title>-<take_id>-draft-grouping.json` for manual tweaking
        - The .mov file can be composited onto the original video in Final Cut Pro or other editors
    
    Grouping workflow:
        - If grouping file exists, prompts whether to regenerate (unless `--yes` auto-reuses)
        - You can manually edit the grouping JSON to adjust which words are grouped together
        - The text field is for human readability - Remotion uses the indices field
        - Just re-run the command after editing to re-render with new groupings
    """
    parser = build_cli_parser(
        stage="captions",
        summary="Render captions with Remotion (drop + karaoke animations).",
    )
    parser.add_argument(
        'video_file',
        nargs='?',
        help='Video file to add captions to (if not provided, looks for *-draft.mp4)'
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="captions",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Find the video file
    if parsed.video_file:
        draft_video = Path(parsed.video_file)
        if not draft_video.exists():
            env.abort(f"Specified video file not found: '{draft_video}'")
    else:
        draft_video = env.expect_single_file("*-draft.mp4", "draft video")

    # Check for transcript JSON
    json_file = draft_video.with_suffix('.json')
    if not json_file.exists():
        env.abort(
            f"Transcript JSON not found: '{json_file.name}'\n"
            f"Please run 'post -transcribe' first to generate word-level timestamps."
        )

    captions_video = draft_video.with_name(f"{draft_video.stem}-captions.mov")
    grouping_file = draft_video.with_name(f"{draft_video.stem}-grouping.json")

    env.ensure_output_path(captions_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to render '{captions_video.name}' using '{draft_video.name}' and '{json_file.name}'."
    )

    # Get video info (dimensions, fps, duration)
    try:
        video_info = get_video_info(draft_video)
        print(f"📐 Video info: {video_info['width']}x{video_info['height']}, {video_info['fps']:.2f} fps, {video_info['duration']:.2f}s")
    except Exception as e:
        env.abort(f"Failed to get video info: {e}")

    # Step 1: Handle word grouping
    groupings = None
    if grouping_file.exists():
        print(f"📋 Found existing grouping file '{grouping_file.name}'")
        if env.auto_confirm:
            use_existing = True
            print("✓ Auto-confirming: reusing existing grouping")
        else:
            response = input("Do you want to reuse the existing grouping? [Y/n]: ").strip().lower()
            use_existing = response in ('', 'y', 'yes')
        
        if use_existing:
            print(f"📂 Loading existing grouping from '{grouping_file.name}'...")
            try:
                groupings = load_grouping(grouping_file)
                print(f"✅ Loaded {len(groupings)} caption groups from saved grouping")
            except Exception as e:
                print(f"⚠️  Failed to load grouping: {e}")
                print("Will generate new grouping instead...")
                groupings = None
        else:
            print("🔄 Will generate new grouping...")
    
    # If we don't have groupings yet, generate them
    if groupings is None:
        print(f"🤖 Generating new word grouping...")
        words = load_words_from_json(json_file)
        groupings = generate_groupings_with_gpt(words)
        # Save the grouping for future reuse
        save_grouping(grouping_file, groupings)

    # Step 2: Render with Remotion and composite
    try:
        render_captions_with_remotion(
            draft_video,
            json_file,
            grouping_file,
            video_info,
            captions_video
        )
        print(f"✅ post -captions: successfully created '{captions_video.name}'")
        print(f"   Transparent caption file ready for compositing in Final Cut Pro!")
    except Exception as e:
        env.abort(f"Failed to render captions: {e}")

