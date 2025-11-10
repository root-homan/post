import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path for utils import
MODULE_DIR = Path(__file__).resolve().parent
UTILS_DIR = MODULE_DIR.parent / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

from .common import StageEnvironment, build_cli_parser, find_preferred_rough_video

try:
    from video_editing import (
        probe_duration,
        concatenate_segments,
        build_keep_segments_from_cuts,
    )
except ImportError:
    # Fallback for different execution contexts
    import sys
    from pathlib import Path
    utils_path = Path(__file__).resolve().parent.parent / "utils"
    sys.path.insert(0, str(utils_path))
    from video_editing import (
        probe_duration,
        concatenate_segments,
        build_keep_segments_from_cuts,
    )


def parse_timestamp(timestamp_str: str) -> float:
    """
    Convert timestamp to seconds. Supports multiple formats:
    - MM:SS:MS (minutes:seconds:milliseconds, e.g., 1:23:45)
    - MM:SS.MS (minutes:seconds.milliseconds, e.g., 1:23.45)
    - HH:MM:SS (hours:minutes:seconds, e.g., 0:01:23)
    - Seconds as float (e.g., 83.45)
    
    Parameters
    ----------
    timestamp_str:
        Timestamp string in one of the supported formats
        
    Returns
    -------
    float:
        Time in seconds (with milliseconds as decimal)
    """
    timestamp_str = timestamp_str.strip()
    
    # If it's just a number, treat it as seconds
    try:
        return float(timestamp_str)
    except ValueError:
        pass
    
    # Split by colon
    parts = timestamp_str.split(':')
    
    if len(parts) == 2:
        # MM:SS or MM:SS.MS format
        minutes = int(parts[0])
        seconds_str = parts[1]
        
        # Check if there's a decimal point
        if '.' in seconds_str:
            seconds = float(seconds_str)
        else:
            # Assume it's MM:SS:MS format where last part is milliseconds
            seconds = float(seconds_str)
        
        return minutes * 60 + seconds
    
    elif len(parts) == 3:
        # Could be HH:MM:SS or MM:SS:MS
        # If first part is small and last part is large, it's MM:SS:MS (old format)
        # Otherwise it's HH:MM:SS
        first = int(parts[0])
        second = int(parts[1])
        third_str = parts[2]
        
        # Check if third part has decimal or is < 60 (likely seconds in HH:MM:SS)
        if '.' in third_str or int(third_str) < 60:
            # HH:MM:SS format
            hours = first
            minutes = second
            seconds = float(third_str)
            return hours * 3600 + minutes * 60 + seconds
        else:
            # MM:SS:MS format (old format where MS is centiseconds)
            minutes = first
            seconds = second
            milliseconds = int(third_str)
            return minutes * 60 + seconds + milliseconds / 100.0
    
    raise ValueError(
        f"Invalid timestamp format: {timestamp_str}. "
        f"Expected formats: HH:MM:SS, MM:SS, or seconds (e.g., 83.5)"
    )




def cut_ranges(
    input_video: Path,
    output_video: Path,
    ranges_to_cut: List[Tuple[float, float]],
    env: StageEnvironment,
) -> None:
    """
    Cut out specified timestamp ranges from the video.
    
    Parameters
    ----------
    input_video:
        Path to the source video (should be an intra-encoded video for efficiency)
    output_video:
        Path where the output video should be saved
    ranges_to_cut:
        List of (start, end) tuples in seconds representing segments to REMOVE
    env:
        Stage environment for error handling
        
    Note
    ----
    This function expects an all-intra encoded video for efficient stream copying.
    Run 'post -convert' first to generate an intra video if needed.
    """
    # Probe duration
    try:
        duration = probe_duration(input_video)
    except RuntimeError as e:
        env.abort(str(e))
    
    # Calculate segments to keep
    keep_segments = build_keep_segments_from_cuts(duration, ranges_to_cut)
    
    # Print summary
    total_cut_duration = sum(end - start for start, end in ranges_to_cut)
    total_keep_duration = sum(end - start for start, end in keep_segments)
    
    print(f"📊 post -cut: video duration: {duration:.2f}s")
    print(f"✂️  post -cut: cutting {len(ranges_to_cut)} range(s) totaling {total_cut_duration:.2f}s")
    print(f"✅ post -cut: keeping {len(keep_segments)} segment(s) totaling {total_keep_duration:.2f}s")
    
    # Format segments for display
    if ranges_to_cut:
        formatted_cuts = ", ".join(
            f"[{start:.2f}s → {end:.2f}s]" for start, end in ranges_to_cut
        )
        print(f"🗑️  post -cut: removing: {formatted_cuts}")
    
    if keep_segments:
        formatted_keeps = ", ".join(
            f"[{start:.2f}s → {end:.2f}s]" for start, end in keep_segments
        )
        print(f"🎬 post -cut: keeping: {formatted_keeps}")
    
    # Encode with cuts
    print("🚀 post -cut: stream copying video, re-encoding audio for perfect sync.")
    try:
        concatenate_segments(input_video, output_video, keep_segments)
        print(f"📦 post -cut: saved '{output_video.name}'.")
    except (ValueError, RuntimeError) as e:
        env.abort(str(e))
    
    print(f"✅ post -cut: wrote cut video to '{output_video.name}'.")


def parse_cut_ranges(ranges_str: str) -> List[Tuple[float, float]]:
    """
    Parse cut ranges from command line argument.
    
    Expected format: "start1,end1,start2,end2,..."
    Timestamps can be in formats: HH:MM:SS, MM:SS, or seconds
    
    Parameters
    ----------
    ranges_str:
        Comma-separated list of timestamps (alternating start,end pairs)
        
    Returns
    -------
    List of (start, end) tuples in seconds
    
    Examples
    --------
    >>> parse_cut_ranges("10.5,15.2,30,35.5")
    [(10.5, 15.2), (30.0, 35.5)]
    
    >>> parse_cut_ranges("0:10:30,0:15:45")
    [(630.0, 945.0)]
    
    >>> parse_cut_ranges("1:30,2:45,5:00,6:15,10:00,11:30")
    [(90.0, 165.0), (300.0, 375.0), (600.0, 690.0)]
    """
    # Remove brackets if present
    ranges_str = ranges_str.strip()
    if ranges_str.startswith('['):
        ranges_str = ranges_str[1:]
    if ranges_str.endswith(']'):
        ranges_str = ranges_str[:-1]
    
    # Split by comma
    parts = [p.strip() for p in ranges_str.split(',') if p.strip()]
    
    if len(parts) % 2 != 0:
        raise ValueError(
            f"Expected an even number of timestamps (start,end pairs), got {len(parts)} values"
        )
    
    ranges = []
    for i in range(0, len(parts), 2):
        start = parse_timestamp(parts[i])
        end = parse_timestamp(parts[i + 1])
        
        if end <= start:
            raise ValueError(
                f"Invalid range: end time ({parts[i+1]} = {end:.2f}s) must be after "
                f"start time ({parts[i]} = {start:.2f}s)"
            )
        
        ranges.append((start, end))
    
    return ranges


def run(args):
    """
    Cut out specified timestamp ranges from a video.
    
    Usage:
        post -cut start1,end1,start2,end2,...
        post -cut [start1,end1,start2,end2,...]
    
    Timestamps can be in formats:
        - HH:MM:SS (e.g., 0:01:30 for 1 minute 30 seconds)
        - MM:SS (e.g., 1:30 for 1 minute 30 seconds)
        - Seconds (e.g., 90.5 for 90.5 seconds)
    
    Dependencies:
        - Requires an intra-encoded rough cut (e.g., `<title>-<take>-intra-rough.mp4`)
        - Run 'post -convert' first if you don't have an intra video
          
    Failure behaviour:
        - Exits if no intra-rough video is found
        - Exits if timestamp ranges are invalid
        - Prompts before overwriting output unless `--yes` is specified
          
    Output:
        - Generates `<title>-<take>-intra-rough-cut.mp4`
        
    Examples:
        # Cut out two ranges: 10.5s-15.2s and 30s-35.5s
        post -cut 10.5,15.2,30,35.5
        
        # Cut out three ranges using MM:SS format
        post -cut 1:30,2:45,5:00,6:15,10:00,11:30
        
        # Cut out using HH:MM:SS format
        post -cut 0:01:30,0:02:45,0:05:00,0:06:30
        
        # Mix formats (seconds and MM:SS)
        post -cut 10.5,15.2,1:30,2:45
    """
    parser = build_cli_parser(
        stage="cut",
        summary="Cut out specified timestamp ranges from a video.",
    )
    parser.add_argument(
        "ranges",
        nargs="?",
        help="Comma-separated timestamp ranges to cut (start1,end1,start2,end2,...)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output filename (default: adds '-cut' suffix to input name)",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="cut",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )
    
    # Find the intra-rough video
    rough_video = find_preferred_rough_video(env)
    if "-intra-" not in rough_video.stem:
        env.abort(
            "Cut requires an all-intra rough cut. "
            "Run 'post -convert' first to generate '<title>-<take>-intra-rough.mp4'."
        )
    
    # Parse cut ranges
    if not parsed.ranges:
        env.abort(
            "No timestamp ranges provided. "
            "Usage: post -cut start1,end1,start2,end2,... "
            "Example: post -cut 10.5,15.2,30,35.5"
        )
    
    try:
        ranges_to_cut = parse_cut_ranges(parsed.ranges)
    except Exception as e:
        env.abort(f"Failed to parse cut ranges: {e}")
    
    # Determine output filename
    if parsed.output:
        output_video = env.directory / parsed.output
    else:
        base_name = rough_video.name[: -len("-rough.mp4")]
        output_video = rough_video.with_name(f"{base_name}-rough-cut.mp4")
    
    env.ensure_output_path(output_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to cut {len(ranges_to_cut)} range(s) from '{rough_video.name}'."
    )
    
    # Perform the cut
    cut_ranges(rough_video, output_video, ranges_to_cut, env)
