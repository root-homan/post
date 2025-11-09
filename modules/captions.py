import subprocess
import json
import shutil
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


def render_captions_with_remotion(
    grouping_path: Path,
    output_video: Path,
    video_width: int,
    video_height: int,
    fps: float,
    duration: float
):
    """
    Render captions using Remotion.
    
    Args:
        grouping_path: Path to the grouping JSON file
        output_video: Path to write the caption video
        video_width: Video width in pixels
        video_height: Video height in pixels
        fps: Frames per second
        duration: Duration in seconds
    """
    # Get the remotion directory
    remotion_dir = Path(__file__).parent.parent / "remotion"
    
    if not remotion_dir.exists():
        raise RuntimeError(f"Remotion directory not found at '{remotion_dir}'")
    
    # Check if node_modules exists, if not, install dependencies
    node_modules = remotion_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing Remotion dependencies (first time only)...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=remotion_dir,
                check=True,
                capture_output=True
            )
            print("✅ Dependencies installed!")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to install npm dependencies: {e}")
    
    # Load the grouping data
    with open(grouping_path, 'r', encoding='utf-8') as f:
        grouping_data = json.load(f)
    
    # Prepare props for Remotion
    # Note: Must match the structure expected by CaptionScene component
    duration_in_frames = int(duration * fps)
    remotion_props = {
        "inputProps": {
            "groups": grouping_data["groups"],
            "videoWidth": video_width,
            "videoHeight": video_height,
            "fps": fps,
            "durationInFrames": duration_in_frames
        }
    }
    
    # Write props to a temporary file
    props_file = remotion_dir / "caption-props.json"
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(remotion_props, f)
    
    print(f"🎬 Rendering captions with Remotion ({duration_in_frames} frames at {fps} fps)...")
    
    # Call Remotion CLI to render
    # Note: Remotion adds the extension automatically based on codec, so we pass path without extension
    output_without_ext = output_video.with_suffix('')
    
    try:
        cmd = [
            "npx",
            "remotion", "render",
            "CaptionScene",
            str(output_without_ext),
            "--props", str(props_file),
            "--codec", "prores",  # Use ProRes for transparency support
            "--prores-profile", "4444",  # 4444 profile supports alpha channel
            "--pixel-format", "yuva444p10le",  # Ensure alpha channel is preserved
        ]
        
        subprocess.run(
            cmd,
            cwd=remotion_dir,
            check=True,
            capture_output=False
        )
        
        # Remotion will create the file with .mov extension automatically
        # Check if it exists and rename if needed to match our expected path
        remotion_output = Path(str(output_without_ext) + '.mov')
        if remotion_output.exists() and remotion_output != output_video:
            remotion_output.rename(output_video)
        
        # Clean up props file
        props_file.unlink()
        
        print(f"✅ Caption video rendered successfully!")
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Remotion render failed: {e}")


def overlay_captions(video_path: Path, caption_video_path: Path, output_path: Path):
    """
    Use ffmpeg to overlay the caption video (with transparency) onto the main video.
    """
    cmd = [
        'ffmpeg',
        '-i', str(video_path),  # Main video
        '-i', str(caption_video_path),  # Caption video with alpha
        '-filter_complex', '[0:v][1:v]overlay=format=auto',  # Overlay with alpha channel support
        '-c:a', 'copy',  # Copy audio without re-encoding
        '-pix_fmt', 'yuv420p',  # Ensure output is in standard format
        '-y',  # Overwrite output file
        str(output_path)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=False)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg overlay failed: {e}")


def run(args):
    """
    Dependencies:
        - A tightened video `<title>-<take_id>-rough-tight.mp4` must be present in the working directory.
        - A matching word timestamps file `<title>-<take_id>-rough-tight.json` (same basename as the video) must exist.
        - ffmpeg must be installed and available in PATH.
        - Node.js and npm must be installed (for Remotion).
    Failure behaviour:
        - Aborts when either artefact is missing, when multiple candidates exist, or when the basenames differ.
        - Prompts before overwriting `<title>-<take_id>-rough-tight-captions.mp4` unless `--yes` is provided.
    Output:
        - Produces `<title>-<take_id>-rough-tight-captions.mp4`, augmenting the tightened video with rendered captions.
        - Also produces an intermediate `<title>-<take_id>-rough-tight-captions-only.mov` (ProRes with alpha) containing just the captions.
        - Also produces `<title>-<take_id>-rough-tight-grouping.json` containing the word grouping for reuse.
    Grouping workflow:
        - If a grouping file exists, prompts whether to reuse it (unless `--yes` is provided, which auto-reuses).
        - This allows regenerating captions with different styling without re-running GPT grouping.
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
    caption_only_video = tightened_video.with_name(f"{tightened_video.stem}-captions-only.mov")
    grouping_file = tightened_video.with_name(f"{tightened_video.stem}-grouping.json")

    env.ensure_output_path(captions_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to render '{captions_video.name}' using '{tightened_video.name}' and '{json_file.name}'."
    )

    # Get video info (dimensions, fps, duration)
    try:
        video_info = get_video_info(tightened_video)
        print(f"📐 Video info: {video_info['width']}x{video_info['height']}, {video_info['fps']:.2f} fps, {video_info['duration']:.2f}s")
    except Exception as e:
        env.abort(f"Failed to get video info: {e}")

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

    # Step 2: Render captions with Remotion
    print(f"🎬 post -captions: rendering captions with Remotion...")
    try:
        render_captions_with_remotion(
            grouping_file,
            caption_only_video,
            video_info['width'],
            video_info['height'],
            video_info['fps'],
            video_info['duration']
        )
        print(f"✅ post -captions: caption video rendered successfully!")
    except Exception as e:
        env.abort(f"Failed to render captions: {e}")

    # Step 3: Overlay captions onto main video
    print(f"🎬 post -captions: overlaying captions onto video...")
    try:
        overlay_captions(tightened_video, caption_only_video, captions_video)
        print(f"✅ post -captions: successfully created '{captions_video.name}' with captions!")
    except Exception as e:
        env.abort(f"Failed to overlay captions: {e}")

