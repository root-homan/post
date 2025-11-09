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


def group_words_into_lines(words):
    """
    Group words into caption lines using GPT-5-mini for intelligent semantic grouping.
    
    Uses GPT-5-mini to understand meaning, powerful words, concept boundaries, and sentence structure
    to create optimal caption groupings, while respecting timing constraints.
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
    
    try:
        response = call_gpt5(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            model="gpt-5-mini"
        )
        
        # Parse the response
        response_data = json.loads(response)
        
        # Handle different possible JSON structures
        if "groups" in response_data:
            groupings = response_data["groups"]
        elif "groupings" in response_data:
            groupings = response_data["groupings"]
        elif "lines" in response_data:
            groupings = response_data["lines"]
        elif isinstance(response_data, list):
            groupings = response_data
        else:
            # If we got an unexpected structure, try to find the first array value
            for value in response_data.values():
                if isinstance(value, list):
                    groupings = value
                    break
            else:
                raise ValueError(f"Unexpected response structure: {response_data}")
        
        # Convert groupings (lists of indices) back to lists of word dictionaries
        lines = []
        for group in groupings:
            if not isinstance(group, list):
                continue
            line_words = [words[idx] for idx in group if 0 <= idx < len(words)]
            if line_words:  # Only add non-empty lines
                lines.append(line_words)
        
        print(f"✅ GPT-5-mini grouped words into {len(lines)} caption lines")
        return lines
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"⚠️  GPT-5-mini grouping failed ({e}), falling back to simple grouping")
        # Fallback: simple grouping by small chunks
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(current_line) >= 4:  # Simple fallback: 4 words per line
                lines.append(current_line)
                current_line = []
        if current_line:
            lines.append(current_line)
        return lines


def format_ass_time(seconds):
    """Convert seconds (float) to ASS timestamp format: H:MM:SS.CC"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def save_grouping(grouping_path: Path, lines):
    """
    Save the word grouping to a JSON file for reuse.
    
    Args:
        grouping_path: Path to save the grouping JSON
        lines: List of lists, where each inner list contains word dictionaries
    """
    # Convert to a serializable format (just save the word data)
    grouping_data = {
        "groups": lines
    }
    with open(grouping_path, 'w', encoding='utf-8') as f:
        json.dump(grouping_data, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved word grouping to '{grouping_path.name}'")


def load_grouping(grouping_path: Path):
    """
    Load a previously saved word grouping from JSON.
    
    Returns:
        List of lists, where each inner list contains word dictionaries
    """
    with open(grouping_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("groups", [])


def generate_ass_file(json_path: Path, ass_path: Path, video_width=2880, video_height=2160, lines=None):
    """
    Generate an ASS subtitle file with karaoke-style word highlighting and drop-in animation.
    
    Style specs:
    - 96px SF Pro Medium font
    - White color
    - Bottom center position
    - 20% up from bottom (margin = 20% of height)
    - Animation: Each word drops in from above when it's time to be spoken
    
    Args:
        json_path: Path to the word timestamps JSON file
        ass_path: Path to write the ASS file
        video_width: Video width in pixels
        video_height: Video height in pixels
        lines: Optional pre-computed grouping. If None, will generate new grouping.
    """
    words = load_words_from_json(json_path)
    
    # Use provided grouping or generate new one
    if lines is None:
        lines = group_words_into_lines(words)
    
    # Calculate margin (20% from bottom)
    margin_v = int(video_height * 0.15)
    
    # ASS file header
    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: " + str(video_width),
        "PlayResY: " + str(video_height),
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # Style with SF Pro Medium font - no outline, no shadow. We control opacity via inline tags.
        # Colors in ASS are &HAABBGGRR where AA is alpha (00=opaque, FF=transparent)
        f"Style: Default,SF Pro Medium,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,0,2,20,20,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    
    # Animation parameters - adjust these for different visual effects
    DROP_DISTANCE = 8  # pixels: how far the line drops from above (lower = more subtle)
    ANIMATION_DURATION = 64  # milliseconds: how long the drop animation takes
    MIN_WORD_DURATION_FOR_KARAOKE = 200  # milliseconds: minimum word duration to do opacity animation
    KARAOKE_FADE_BACK = 80  # milliseconds: how quickly words return to the inactive opacity
 
    # Generate events for each line with entire line dropping together
    for line_words in lines:
        if not line_words:
            continue
 
        line_start = line_words[0]['start']
        line_end = line_words[-1]['end']
 
        # Calculate positions
        center_x = video_width // 2
        baseline_y = video_height - margin_v
 
        # Starting position (above) and ending position for the drop animation
        start_y = baseline_y - DROP_DISTANCE
        end_y = baseline_y
 
        # Check if we should do karaoke effect (opacity transitions)
        # Only if words are long enough
        use_karaoke = all(
            (word['end'] - word['start']) * 1000 >= MIN_WORD_DURATION_FOR_KARAOKE 
            for word in line_words
        )
 
        line_duration_ms = max(1, int((line_end - line_start) * 1000))

        if use_karaoke:
            # Build per-word opacity animations using \t transforms
            segments = []

            for word in line_words:
                word_text = word['word']
                highlight_start = max(0, int((word['start'] - line_start) * 1000))
                highlight_end = max(highlight_start + 1, int((word['end'] - line_start) * 1000))
                fade_back_end = min(highlight_end + KARAOKE_FADE_BACK, line_duration_ms)

                segment = (
                    "{\\alpha&H4D&"
                    f"\\t({highlight_start},{highlight_end},\\alpha&H00&)"
                    f"\\t({highlight_end},{fade_back_end},\\alpha&H4D&)"
                    f"}}{word_text}"
                )
                segments.append(segment)

            full_text = " ".join(segments)
            anim_text = f"{{\\move({center_x},{start_y},{center_x},{end_y},0,{ANIMATION_DURATION})}}{full_text}"
            ass_content.append(
                f"Dialogue: 0,{format_ass_time(line_start)},{format_ass_time(line_end)},Default,,0,0,0,,{anim_text}"
            )
        else:
            # No karaoke - show all words at full opacity
            full_text = " ".join([word['word'] for word in line_words])
            anim_text = f"{{\\move({center_x},{start_y},{center_x},{end_y},0,{ANIMATION_DURATION})\\alpha&H00&}}{full_text}"
            ass_content.append(
                f"Dialogue: 0,{format_ass_time(line_start)},{format_ass_time(line_end)},Default,,0,0,0,,{anim_text}"
            )
 
    # Write ASS file
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ass_content))


def burn_subtitles(video_path: Path, ass_path: Path, output_path: Path):
    """
    Use ffmpeg to burn ASS subtitles onto the video.
    """
    # Escape the ASS path for ffmpeg filter
    # On Windows, we need to escape backslashes and colons differently
    ass_path_str = str(ass_path).replace('\\', '/').replace(':', '\\:')
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vf', f"ass='{ass_path_str}'",
        '-c:a', 'copy',  # Copy audio without re-encoding
        '-y',  # Overwrite output file
        str(output_path)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=False)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed: {e}")


def run(args):
    """
    Dependencies:
        - A tightened video `<title>-<take_id>-rough-tight.mp4` must be present in the working directory.
        - A matching word timestamps file `<title>-<take_id>-rough-tight.json` (same basename as the video) must exist.
        - ffmpeg must be installed and available in PATH.
    Failure behaviour:
        - Aborts when either artefact is missing, when multiple candidates exist, or when the basenames differ.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-captions.mp4` unless `--yes` is provided.
    Output:
        - Produces `<title>-<take_id>-rough-tight-captions.mp4`, augmenting the tightened video with burnt-in captions.
        - Also produces an intermediate `<title>-<take_id>-rough-tight.ass` file with karaoke-style subtitles.
        - Also produces `<title>-<take_id>-rough-tight-grouping.json` containing the word grouping for reuse.
    Grouping workflow:
        - If a grouping file exists, prompts whether to reuse it (unless `--yes` is provided, which auto-reuses).
        - This allows regenerating the .ass file with different styling without re-running GPT grouping.
        - To force new grouping: delete the grouping file or respond 'n' to the prompt.
    """
    parser = build_cli_parser(
        stage="captions",
        summary="Render the tightened take with burnt-in captions from word timestamps.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="captions",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    tightened_video = env.expect_single_file("*-rough-tight.mp4", "tightened video")
    json_file = env.expect_single_file("*-rough-tight.json", "word timestamps file required for captions")

    if tightened_video.stem != json_file.stem:
        env.abort(
            "Word timestamps file and video do not share the same basename. "
            f"Expected '{tightened_video.stem}', found '{json_file.stem}'."
        )

    captions_video = tightened_video.with_name(f"{tightened_video.stem}-captions.mp4")
    ass_file = tightened_video.with_suffix(".ass")
    grouping_file = tightened_video.with_name(f"{tightened_video.stem}-grouping.json")

    env.ensure_output_path(captions_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to render '{captions_video.name}' using '{tightened_video.name}' and '{json_file.name}'."
    )

    # Get video dimensions for proper subtitle positioning
    try:
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            str(tightened_video)
        ]
        result = subprocess.run(probe_cmd, check=True, capture_output=True, text=True)
        dimensions = result.stdout.strip().split('x')
        video_width = int(dimensions[0])
        video_height = int(dimensions[1])
        print(f"📐 Detected video dimensions: {video_width}x{video_height}")
    except Exception as e:
        env.abort(f"Failed to get video dimensions: {e}")

    # Step 1: Handle word grouping (separate from ASS generation)
    lines = None
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
                lines = load_grouping(grouping_file)
                print(f"✅ Loaded {len(lines)} caption groups from saved grouping")
            except Exception as e:
                print(f"⚠️  Failed to load grouping: {e}")
                print("Will generate new grouping instead...")
                lines = None
        else:
            print("🔄 Will generate new grouping...")
    
    # If we don't have lines yet, generate them
    if lines is None:
        print(f"🤖 Generating new word grouping...")
        words = load_words_from_json(json_file)
        lines = group_words_into_lines(words)
        # Save the grouping for future reuse
        save_grouping(grouping_file, lines)

    # Step 2: Generate ASS file from grouping
    print(f"📝 post -captions: generating ASS subtitle file '{ass_file.name}' with karaoke-style timing...")
    try:
        generate_ass_file(json_file, ass_file, video_width, video_height, lines=lines)
        print(f"✅ post -captions: ASS file generated successfully!")
    except Exception as e:
        env.abort(f"Failed to generate ASS file: {e}")

    # Step 3: Burn subtitles onto video
    print(f"🎬 post -captions: burning subtitles onto video...")
    try:
        burn_subtitles(tightened_video, ass_file, captions_video)
        print(f"✅ post -captions: successfully created '{captions_video.name}' with burnt-in captions!")
    except Exception as e:
        env.abort(f"Failed to burn subtitles: {e}")

