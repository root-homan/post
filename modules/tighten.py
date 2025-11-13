import signal
import re
import sys
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Optional

MODULE_DIR = Path(__file__).resolve().parent
UTILS_DIR = MODULE_DIR.parent / "utils"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

try:
    from .common import (
        StageEnvironment,
        build_cli_parser,
        find_preferred_rough_video,
    )  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - handles execution as a standalone script
    from common import (
        StageEnvironment,
        build_cli_parser,
        find_preferred_rough_video,
    )  # type: ignore[attr-defined]

# Import shared video editing utilities
try:
    from video_editing import concatenate_segments
except ImportError:
    import sys
    from pathlib import Path
    utils_path = Path(__file__).resolve().parent.parent / "utils"
    sys.path.insert(0, str(utils_path))
    from video_editing import concatenate_segments

# ============================================================================
# SPEECH DETECTION THRESHOLDS
# ============================================================================

# High threshold: Definitely speech (strict)
HIGH_THRESHOLD_DB = -24.0

# Low threshold: Includes speech + quiet edges like consonants, breaths
# We'll use low-threshold boundaries to expand high-threshold speech regions
LOW_THRESHOLD_DB = -50.0

# Minimum silence duration: Only cut pauses that are at least this long
MIN_SILENCE_DURATION_SECONDS = 0.5

# Boundary padding: Extra buffer at each cut point (negative = tighter cuts)
BOUNDARY_PADDING_SECONDS = 0.1

# Buffer before the first segment so the intro breathes a bit.
LEADING_EDGE_PADDING_SECONDS = 0.5
# Buffer after the last segment so the outro isn't abruptly chopped.
TRAILING_EDGE_PADDING_SECONDS = 3

# Encoding configuration tuned for Apple Silicon hardware acceleration.
AUDIO_BITRATE = "192k"
TIGHTEN_AUDIO_CODEC = "pcm_s16le"
VIDEOTOOLBOX_CODEC = "h264_videotoolbox"
VIDEOTOOLBOX_GLOBAL_QUALITY = 70
VIDEOTOOLBOX_PIX_FMT = "yuv420p"

@dataclass(frozen=True)
class SilenceWindow:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _terminate_process(process: subprocess.Popen, *, verbose: bool = True) -> None:
    """Forcefully terminate a subprocess, escalating through signals if needed."""
    if process.poll() is not None:
        return
    
    if verbose:
        print("\n⚠️  post -tighten: interrupt received, stopping ffmpeg/ffprobe...", flush=True)
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            process.send_signal(sig)
        except ProcessLookupError:
            if verbose:
                print("✅ post -tighten: process already terminated.", flush=True)
            return
        try:
            process.wait(timeout=2)
            if verbose:
                print("✅ post -tighten: process stopped cleanly.", flush=True)
            return
        except subprocess.TimeoutExpired:
            continue
    
    if verbose:
        print("⚠️  post -tighten: forcing kill...", flush=True)
    try:
        process.kill()
    except ProcessLookupError:
        if verbose:
            print("✅ post -tighten: process already terminated.", flush=True)
        return
    process.wait()
    if verbose:
        print("✅ post -tighten: process killed.", flush=True)


def _ensure_tool(tool: str, env: StageEnvironment) -> None:
    if shutil.which(tool) is None:
        env.abort(
            f"Required dependency '{tool}' was not found on PATH. Install FFmpeg and try again."
        )


def _probe_duration(path: Path, env: StageEnvironment) -> float:
    process = subprocess.Popen(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = process.communicate()
        return_code = process.returncode
    except KeyboardInterrupt:
        _terminate_process(process)
        raise

    if return_code != 0:
        env.abort(f"ffprobe failed for '{path.name}': {stderr.strip()}")

    try:
        return float(stdout.strip())
    except ValueError:
        env.abort(f"Unable to parse duration from ffprobe output: {stdout!r}")
    raise AssertionError("unreachable")  # pragma: no cover


def _probe_dimensions(path: Path, env: StageEnvironment) -> Tuple[int, int]:
    """Probe video dimensions and return (width, height)."""
    process = subprocess.Popen(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = process.communicate()
        return_code = process.returncode
    except KeyboardInterrupt:
        _terminate_process(process)
        raise

    if return_code != 0:
        env.abort(f"ffprobe failed for '{path.name}': {stderr.strip()}")

    try:
        width_str, height_str = stdout.strip().split(",")
        return int(width_str), int(height_str)
    except (ValueError, AttributeError):
        env.abort(f"Unable to parse dimensions from ffprobe output: {stdout!r}")
    raise AssertionError("unreachable")  # pragma: no cover


def _parse_silences(log_output: str, env: StageEnvironment, duration: float) -> Sequence[SilenceWindow]:
    start_pattern = re.compile(r"silence_start:\s*([0-9.+-]+)")
    end_pattern = re.compile(r"silence_end:\s*([0-9.+-]+)")

    silences: List[SilenceWindow] = []
    current_start: float | None = None

    for line in log_output.splitlines():
        if match := start_pattern.search(line):
            try:
                current_start = float(match.group(1))
            except ValueError:
                current_start = None
        elif match := end_pattern.search(line):
            if current_start is None:
                continue
            try:
                end_time = float(match.group(1))
            except ValueError:
                current_start = None
                continue
            silences.append(SilenceWindow(start=current_start, end=end_time))
            current_start = None

    if current_start is not None:
        silences.append(SilenceWindow(start=current_start, end=duration))

    silences.sort(key=lambda window: window.start)
    return tuple(silences)


def _detect_silences(
    path: Path,
    env: StageEnvironment,
    threshold_db: float,
    min_duration: float,
) -> Sequence[SilenceWindow]:
    detect_filter = (
        f"silencedetect=noise={threshold_db}dB:d={min_duration}"
    )
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-threads", "0",  # Use all available CPU cores
            "-i",
            str(path),
            "-vn",  # Skip video processing entirely - only analyze audio
            "-af",
            detect_filter,
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = process.communicate()
        return_code = process.returncode
    except KeyboardInterrupt:
        _terminate_process(process)
        raise

    if return_code != 0:
        message = stderr.strip() or stdout.strip() or "unknown error"
        env.abort(f"ffmpeg silencedetect failed: {message}")

    duration = _probe_duration(path, env)
    return _parse_silences(stderr, env, duration)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _merge_overlapping_regions(regions: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Merge overlapping or adjacent regions.
    
    Args:
        regions: List of (start, end) tuples
    
    Returns:
        Merged list with no overlaps
    """
    if not regions:
        return regions
    
    # Sort by start time
    sorted_regions = sorted(regions, key=lambda x: x[0])
    merged = [sorted_regions[0]]
    
    for start, end in sorted_regions[1:]:
        prev_start, prev_end = merged[-1]
        
        # If this region overlaps or is adjacent to the previous one, merge them
        if start <= prev_end:
            # Extend the previous region
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            # No overlap, add as new region
            merged.append((start, end))
    
    return merged


def _expand_to_low_threshold_boundaries(
    high_speech_regions: List[Tuple[float, float]],
    low_speech_regions: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """
    Expand high-threshold speech regions to low-threshold boundaries.
    
    For each high-threshold speech region, find the low-threshold region(s)
    that contain or overlap with it, and use those boundaries instead.
    This captures quiet consonants/word edges without including pure silence.
    
    Args:
        high_speech_regions: Speech regions at high threshold (e.g., -25dB)
        low_speech_regions: Speech regions at low threshold (e.g., -40dB)
    
    Returns:
        Expanded speech regions using low-threshold boundaries
    """
    if not high_speech_regions:
        return high_speech_regions
    
    expanded = []
    
    for high_start, high_end in high_speech_regions:
        # Find all low-threshold regions that overlap with this high-threshold region
        matching_low_regions = []
        for low_start, low_end in low_speech_regions:
            # Check if they overlap
            if low_end >= high_start and low_start <= high_end:
                matching_low_regions.append((low_start, low_end))
        
        if matching_low_regions:
            # Use the boundaries from the matching low-threshold regions
            # Take the earliest start and latest end
            expanded_start = min(start for start, _ in matching_low_regions)
            expanded_end = max(end for _, end in matching_low_regions)
            expanded.append((expanded_start, expanded_end))
        else:
            # No matching low region (shouldn't happen), keep original
            expanded.append((high_start, high_end))
    
    # CRITICAL: Merge overlapping regions!
    # Multiple high regions might expand into the same low region
    return _merge_overlapping_regions(expanded)


def _build_segments_from_silences(
    duration: float,
    high_silences: Sequence[SilenceWindow],
    low_silences: Sequence[SilenceWindow],
    boundary_padding: float,
    leading_padding: float,
    trailing_padding: float,
) -> List[Tuple[float, float]]:
    """
    Build segments by expanding high-threshold speech to low-threshold boundaries.
    
    Args:
        duration: Total video duration
        high_silences: Silence windows at high threshold (e.g., -25dB)
        low_silences: Silence windows at low threshold (e.g., -40dB)
        boundary_padding: Padding at cut points (negative = tighter)
        leading_padding: Padding before first segment
        trailing_padding: Padding after last segment
    
    Returns:
        Final segments using low-threshold boundaries where high-threshold speech exists
    """
    
    # Helper to build speech regions from silences
    def build_speech_regions(silences: Sequence[SilenceWindow]) -> List[Tuple[float, float]]:
        regions: List[Tuple[float, float]] = []
        cursor = 0.0
        
        for silence in silences:
            cut_start = max(0.0, silence.start + boundary_padding)
            cut_end = min(duration, silence.end - boundary_padding)
            
            if cut_start > cursor:
                regions.append((cursor, cut_start))
            
            cursor = max(cursor, cut_end)
        
        if cursor < duration:
            regions.append((cursor, duration))
        
        # Filter out very short regions
        regions = [(start, end) for start, end in regions if end - start > 0.01]
        
        return regions if regions else [(0.0, duration)]
    
    # Step 1: Build speech regions at both thresholds
    high_speech = build_speech_regions(high_silences)
    low_speech = build_speech_regions(low_silences)
    
    print(f"\n🔍 Expanding speech boundaries...")
    print(f"    High-threshold speech regions: {len(high_speech)}")
    print(f"    Low-threshold speech regions: {len(low_speech)}")
    
    # Step 2: Expand high-threshold regions to low-threshold boundaries
    expanded_regions = _expand_to_low_threshold_boundaries(high_speech, low_speech)
    
    # Calculate how much we expanded
    high_duration = sum(end - start for start, end in high_speech)
    low_duration = sum(end - start for start, end in low_speech)
    expanded_duration = sum(end - start for start, end in expanded_regions)
    expansion_gained = expanded_duration - high_duration
    
    print(f"    High-threshold duration: {high_duration:.2f}s")
    print(f"    Low-threshold duration: {low_duration:.2f}s")
    print(f"    Expanded regions: {len(expanded_regions)}")
    print(f"    Captured additional: {expansion_gained:.2f}s of quiet sounds")
    
    # Step 3: Apply leading/trailing padding
    final_segments = []
    
    for i, (seg_start, seg_end) in enumerate(expanded_regions):
        is_first = (i == 0)
        is_last = (i == len(expanded_regions) - 1)
        
        if is_first:
            seg_start = max(0.0, seg_start - leading_padding)
        if is_last:
            seg_end = min(duration, seg_end + trailing_padding)
        
        final_segments.append((seg_start, seg_end))
    
    # Clean up segments
    final_segments = [(max(0.0, s), min(duration, e)) for s, e in final_segments]
    final_segments = [(s, e) for s, e in final_segments if e > s + 0.01]
    
    if not final_segments:
        final_segments = [(0.0, duration)]
    
    # Calculate final duration
    final_duration = sum(end - start for start, end in final_segments)
    total_cut = duration - final_duration
    
    print(f"\n📊 FINAL:")
    print(f"    Original duration: {duration:.2f}s")
    print(f"    Total cut: {total_cut:.2f}s ({total_cut/duration*100:.1f}%)")
    print(f"    Remaining: {final_duration:.2f}s\n")
    
    return final_segments


def _build_keep_segments(
    duration: float,
    silences: Sequence[SilenceWindow],
    boundary_padding: float,
    leading_padding: float,
    trailing_padding: float,
) -> List[Tuple[float, float]]:
    segments: List[Tuple[float, float]] = []
    cursor = 0.0

    for silence in silences:
        start = _clamp(silence.start - boundary_padding, cursor, duration)
        if start > cursor:
            segments.append((cursor, start))
        cursor = _clamp(silence.end + boundary_padding, cursor, duration)

    if cursor < duration:
        segments.append((cursor, duration))

    cleaned = [(start, end) for start, end in segments if end - start > 1e-3]
    if not cleaned:
        cleaned.append((0.0, duration))
    else:
        first_start, first_end = cleaned[0]
        adjusted_first_start = _clamp(
            first_start - leading_padding, 0.0, first_end
        )
        cleaned[0] = (adjusted_first_start, first_end)

        last_start, last_end = cleaned[-1]
        adjusted_last_end = _clamp(
            last_end + trailing_padding, last_start, duration
        )
        cleaned[-1] = (last_start, adjusted_last_end)
    return cleaned


def _format_ts(value: float) -> str:
    safe_value = max(0.0, value)
    return f"{safe_value:.3f}".rstrip("0").rstrip(".") or "0"


def _segments_total(segments: Iterable[Tuple[float, float]]) -> float:
    return sum(end - start for start, end in segments)


def _format_windows(windows: Sequence[SilenceWindow]) -> str:
    if not windows:
        return "none"

    parts = []
    for window in windows:
        parts.append(
            f"[{window.start:.2f}s → {window.end:.2f}s | {window.duration:.2f}s]"
        )
    return ", ".join(parts)


def _encode_tightened(
    source: Path,
    destination: Path,
    segments: Sequence[Tuple[float, float]],
    env: StageEnvironment,
) -> None:
    """Concatenate segments using stream copy (requires all-intra source)."""
    print(
        f"🚀 post -tighten: stream copying video, encoding audio to lossless PCM ({TIGHTEN_AUDIO_CODEC})."
    )
    
    try:
        concatenate_segments(
            source,
            destination,
            segments,
            audio_codec=TIGHTEN_AUDIO_CODEC,
        )
    except (ValueError, RuntimeError) as e:
        env.abort(str(e))
    
    print(f"📦 post -tighten: saved '{destination.name}'.")


def _run_ffmpeg_with_progress(
    cmd: List[str],
    destination: Path,
    total_duration: float,
    env: StageEnvironment,
) -> None:
    stderr_output = ""

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    progress_template = (
        "📈 post -tighten: encoding… {percent:5.1f}% "
        "({elapsed:5.1f}s / {total:5.1f}s)"
    )

    return_code: int | None = None

    try:
        if process.stdout is not None:
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("out_time_ms="):
                    try:
                        out_time_seconds = float(line.split("=", 1)[1]) / 1_000_000.0
                    except ValueError:
                        continue
                    clamped = min(out_time_seconds, max(total_duration, 0.0))
                    percent = (
                        (clamped / total_duration) * 100.0
                        if total_duration > 0.0
                        else 100.0
                    )
                    print(
                        "\r"
                        + progress_template.format(
                            percent=percent,
                            elapsed=clamped,
                            total=total_duration,
                        ),
                        end="",
                        flush=True,
                    )
                elif line == "progress=end":
                    break

        if process.stderr is not None:
            stderr_output = process.stderr.read()
        return_code = process.wait()
    except BaseException:
        _terminate_process(process)
        raise
    finally:
        print("\r" + " " * 80 + "\r", end="", flush=True)

    if return_code != 0:
        env.abort(
            f"ffmpeg tighten encode failed with exit code {return_code}. "
            f"Details: {stderr_output.strip()}"
        )

    print(f"📦 post -tighten: saved '{destination.name}'.")


def run(args):
    """
    Remove silences from video using silence threshold detection.
    
    Algorithm:
        1. Detect silences in the audio waveform using threshold
        2. Cut at silence boundaries with boundary padding
    
    Dependencies:
        - By default, operates on the LONGEST filename ending with `-rough.mp4` in the working directory.
        - Alternatively, accepts an optional filepath argument to specify which video to process.
    
    Failure behaviour:
        - Exits without modifying files when no rough cut is found or when the specified file doesn't exist.
        - Prompts before overwriting `<title>-<take_id>-rough-tight.mp4` unless `--yes` is specified.
    
    Output:
        - Generates `<title>-<take_id>-rough-tight.mp4`, i.e., the same base filename with `-tight` appended before `.mp4`.
    """
    parser = build_cli_parser(
        stage="tighten",
        summary="Remove silences from rough cut by detecting silence thresholds.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=HIGH_THRESHOLD_DB,
        help=f"High threshold in dB (default: {HIGH_THRESHOLD_DB})",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=MIN_SILENCE_DURATION_SECONDS,
        help=f"Minimum silence duration in seconds to remove (default: {MIN_SILENCE_DURATION_SECONDS})",
    )
    parser.add_argument(
        "--boundary-padding",
        type=float,
        default=BOUNDARY_PADDING_SECONDS,
        help=f"Padding around silence boundaries in seconds, negative values tighten more (default: {BOUNDARY_PADDING_SECONDS})",
    )
    parser.add_argument(
        "--leading-padding",
        type=float,
        default=LEADING_EDGE_PADDING_SECONDS,
        help=f"Padding before the first segment in seconds (default: {LEADING_EDGE_PADDING_SECONDS})",
    )
    parser.add_argument(
        "--trailing-padding",
        type=float,
        default=TRAILING_EDGE_PADDING_SECONDS,
        help=f"Padding after the last segment in seconds (default: {TRAILING_EDGE_PADDING_SECONDS})",
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default=None,
        help="Optional path to the video file to tighten (defaults to longest '*-rough.mp4' file)",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="tighten",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Use provided filepath or find the longest rough video
    if parsed.filepath:
        rough_video = Path(parsed.filepath).expanduser().resolve()
        if not rough_video.exists():
            env.abort(f"Specified video file '{parsed.filepath}' does not exist.")
        if not rough_video.is_file():
            env.abort(f"Specified path '{parsed.filepath}' is not a file.")
        if not rough_video.name.endswith("-rough.mp4"):
            print(f"⚠️  Warning: File '{rough_video.name}' does not follow the '*-rough.mp4' naming convention.")
    else:
        rough_video = find_preferred_rough_video(env)
    
    if "-intra-" not in rough_video.stem:
        env.abort(
            "Tighten now expects an all-intra rough cut. "
            "Run 'post -convert' first to generate '<title>-<take>-intra-rough.mp4'."
        )
    base_name = rough_video.name[: -len("-rough.mp4")]
    tightened_video = rough_video.with_name(f"{base_name}-rough-tight.mp4")

    env.ensure_output_path(tightened_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to tighten '{rough_video.name}' into '{tightened_video.name}'."
    )

    _ensure_tool("ffmpeg", env)
    _ensure_tool("ffprobe", env)

    # Extract parameters from parsed args
    threshold_db = parsed.threshold
    min_silence = parsed.min_silence
    boundary_padding = parsed.boundary_padding
    leading_padding = parsed.leading_padding
    trailing_padding = parsed.trailing_padding
    duration = _probe_duration(rough_video, env)
    
    # Detect silences at high threshold (strict speech detection)
    print(f"🔊 Detecting high-threshold silences...")
    print(f"    High threshold: {threshold_db:.1f} dB, Min duration: {min_silence:.2f}s")
    
    high_silences = _detect_silences(rough_video, env, threshold_db, min_silence)
    
    print(f"✅ High-threshold silences detected: {len(high_silences)} region(s)\n")
    
    # Detect silences at low threshold (includes quiet word edges)
    print(f"🔊 Detecting low-threshold silences...")
    print(f"    Low threshold: {LOW_THRESHOLD_DB:.1f} dB, Min duration: {min_silence:.2f}s")
    
    low_silences = _detect_silences(rough_video, env, LOW_THRESHOLD_DB, min_silence)
    
    print(f"✅ Low-threshold silences detected: {len(low_silences)} region(s)\n")
    
    # Build segments by expanding high-threshold speech to low-threshold boundaries
    keep_segments = _build_segments_from_silences(
        duration,
        high_silences,
        low_silences,
        boundary_padding=boundary_padding,
        leading_padding=leading_padding,
        trailing_padding=trailing_padding,
    )

    # Encode the tightened video
    _encode_tightened(rough_video, tightened_video, keep_segments, env)

    print(
        f"✅ post -tighten: wrote tightened cut to '{tightened_video.name}'."
    )
