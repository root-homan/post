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

# dB floor below which audio counts as silence; tune to your mic noise.
# HIGHER absolute value, the LESS aggressively it cuts.
SILENCE_THRESHOLD_DB = -22.0
# SILENCE_THRESHOLD_DB = -22.0 # (for the wireless go 3 mic).

# Minimum silence length (seconds) before we consider trimming it out.
MIN_SILENCE_DURATION_SECONDS = 0.5
# Extra audio to keep around each internal silence boundary (negative tightens).
BOUNDARY_PADDING_SECONDS = 0.1

# Buffer before the first segment so the intro breathes a bit.
LEADING_EDGE_PADDING_SECONDS = 0.2
# Buffer after the last segment so the outro isn't abruptly chopped.
TRAILING_EDGE_PADDING_SECONDS = 3

# Encoding configuration tuned for Apple Silicon hardware acceleration.
AUDIO_BITRATE = "192k"
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


def _build_segments_from_silences(
    duration: float,
    silences: Sequence[SilenceWindow],
    boundary_padding: float,
    leading_padding: float,
    trailing_padding: float,
) -> List[Tuple[float, float]]:
    """
    Build segments by cutting at silences.
    
    Args:
        duration: Total video duration
        silences: Detected silence windows from waveform
        boundary_padding: Padding at cut points (negative = tighter)
        leading_padding: Padding before first segment
        trailing_padding: Padding after last segment
    
    Returns:
        Final segments based purely on silence detection
    """
    
    # Step 1: Build list of what we're CUTTING (the silence regions with boundary padding)
    cut_regions: List[Tuple[float, float]] = []
    
    for silence in silences:
        # With boundary_padding = -0.1, we cut TIGHTER (remove more)
        # silence [10.0 → 12.0] with boundary_padding -0.1 means:
        # - Cut from (10.0 + (-0.1)) = 9.9 to (12.0 - (-0.1)) = 12.1
        # This is because negative padding means "cut into the non-silence"
        cut_start = silence.start + boundary_padding  # For -0.1: start + (-0.1) = start - 0.1
        cut_end = silence.end - boundary_padding      # For -0.1: end - (-0.1) = end + 0.1
        
        cut_start = max(0.0, cut_start)
        cut_end = min(duration, cut_end)
        
        if cut_end > cut_start + 0.01:
            cut_regions.append((cut_start, cut_end))
    
    
    # Step 2: Build segments by inverting the cut regions
    segments: List[Tuple[float, float]] = []
    cursor = 0.0
    
    for cut_start, cut_end in cut_regions:
        # Keep the audio before this cut
        if cut_start > cursor:
            segments.append((cursor, cut_start))
        
        # Move cursor to after this cut
        cursor = max(cursor, cut_end)
    
    # Keep anything after the last cut
    if cursor < duration:
        segments.append((cursor, duration))
    
    # Filter out very short segments
    segments = [(start, end) for start, end in segments if end - start > 0.01]
    
    if not segments:
        segments = [(0.0, duration)]
    
    # Step 3: Apply leading/trailing padding
    final_segments = []
    
    for i, (seg_start, seg_end) in enumerate(segments):
        is_first = (i == 0)
        is_last = (i == len(segments) - 1)
        
        # Apply leading/trailing padding
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
    print("🚀 post -tighten: stream copying video, re-encoding audio for perfect sync.")
    
    try:
        concatenate_segments(source, destination, segments, audio_bitrate=AUDIO_BITRATE)
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
        default=SILENCE_THRESHOLD_DB,
        help=f"Silence threshold in dB (default: {SILENCE_THRESHOLD_DB})",
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
    
    # Detect silences
    print(f"🔊 Detecting silences...")
    print(f"    Threshold: {threshold_db:.1f} dB, Min duration: {min_silence:.2f}s\n")
    
    silences = _detect_silences(rough_video, env, threshold_db, min_silence)
    
    # Calculate silence statistics
    total_silence_duration = sum(s.duration for s in silences)
    remaining_duration = duration - total_silence_duration
    
    print(f"✅ Silences detected: {len(silences)} region(s)")
    print(f"    Cutting: {total_silence_duration:.2f}s")
    print(f"    Remaining: {remaining_duration:.2f}s\n")
    
    # Build segments from silences
    keep_segments = _build_segments_from_silences(
        duration,
        silences,
        boundary_padding=boundary_padding,
        leading_padding=leading_padding,
        trailing_padding=trailing_padding,
    )

    # Encode the tightened video
    _encode_tightened(rough_video, tightened_video, keep_segments, env)

    print(
        f"✅ post -tighten: wrote tightened cut to '{tightened_video.name}'."
    )
