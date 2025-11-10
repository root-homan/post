import signal
import re
import sys
import shutil
import subprocess
import json
import torch
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
SILENCE_THRESHOLD_DB = -24.0
# SILENCE_THRESHOLD_DB = -17.0 (for the wireless go 3 mic).

# Minimum silence length (seconds) before we consider trimming it out.
MIN_SILENCE_DURATION_SECONDS = 0.5
# Extra audio to keep around each internal silence boundary (negative tightens).
BOUNDARY_PADDING_SECONDS = -0.1

# Buffer before the first segment so the intro breathes a bit.
LEADING_EDGE_PADDING_SECONDS = 1
# Buffer after the last segment so the outro isn't abruptly chopped.
TRAILING_EDGE_PADDING_SECONDS = 5
# Maximum gap between words to keep them in the same segment (prevents mid-sentence cuts).
WORD_MERGE_TOLERANCE_SECONDS = 0.7

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


def _run_stable_whisper(
    path: Path,
    env: StageEnvironment,
    model_name: str = "large-v2",
) -> List[dict]:
    """
    Run stable-ts on the video file and return word-level timestamps.
    Returns the words list.
    """
    try:
        import stable_whisper
    except ImportError:
        env.abort(
            "stable-ts is not installed. Install it with: pip3 install --break-system-packages stable-ts"
        )

    # Detect device
    # Note: MPS has numerical stability issues with Whisper, so we use CPU on macOS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\n{'='*80}")
    print(f"🎤 STABLE-TS TRANSCRIPTION")
    print(f"{'='*80}")
    print(f"  Device: {device.upper()}")
    print(f"  Model: {model_name}")
    print(f"  Source: {path.name}")
    print(f"{'='*80}\n")
    
    # Load model
    print(f"⏳ [1/3] Loading Whisper model '{model_name}'...", flush=True)
    model = stable_whisper.load_model(model_name, device=device)
    print(f"✅ [1/3] Model loaded successfully.\n", flush=True)
    
    # Transcribe with word-level timestamps
    print(f"⏳ [2/3] Transcribing audio with word-level precision (this may take a minute)...", flush=True)
    result = model.transcribe(str(path), word_timestamps=True)
    print(f"✅ [2/3] Transcription complete.\n", flush=True)
    
    # Extract words with timestamps
    print(f"⏳ [3/3] Extracting word-level timestamps...", flush=True)
    words = []
    for segment in result.segments:
        for word in segment.words:
            words.append({
                'word': word.word.strip(),
                'start': word.start,
                'end': word.end
            })
    print(f"✅ [3/3] Extracted {len(words)} words.\n", flush=True)
    
    # Save to persistent file in the working directory
    output_path = env.directory / "silence.json"
    with open(output_path, 'w') as f:
        json.dump(words, f, indent=2)
    
    print(f"💾 Saved transcription to: {output_path.name}")
    print(f"{'='*80}\n")
    
    return words


def _extract_speech_segments_from_words(
    words: List[dict],
    duration: float,
    leading_padding: float,
    trailing_padding: float,
    merge_tolerance: float = WORD_MERGE_TOLERANCE_SECONDS,
) -> List[Tuple[float, float]]:
    """
    Extract speech segments from word-level timestamps.
    Returns list of (start, end) tuples representing where speech occurs.
    
    Args:
        words: List of word dictionaries with 'start' and 'end' timestamps
        duration: Total duration of the video
        leading_padding: Padding before the first segment
        trailing_padding: Padding after the last segment
        merge_tolerance: Maximum gap between words to keep in same segment (prevents mid-sentence cuts)
    """
    if not words:
        return [(0.0, duration)]
    
    # Extract all word boundaries
    speech_ranges: List[Tuple[float, float]] = []
    
    for word in words:
        start = word.get("start")
        end = word.get("end")
        if start is not None and end is not None:
            speech_ranges.append((start, end))
    
    if not speech_ranges:
        return [(0.0, duration)]
    
    # Merge overlapping or nearby ranges (within merge_tolerance)
    speech_ranges.sort(key=lambda x: x[0])
    merged: List[Tuple[float, float]] = [speech_ranges[0]]
    
    for start, end in speech_ranges[1:]:
        last_start, last_end = merged[-1]
        gap = start - last_end
        
        # Merge if overlapping or gap is within tolerance
        if gap <= merge_tolerance:
            # Keep the same start, extend to the new end
            merged[-1] = (last_start, max(last_end, end))
        else:
            # Gap is too large, create a new segment (this is where we'll cut)
            merged.append((start, end))
    
    # Apply padding to first and last segments
    if merged:
        first_start, first_end = merged[0]
        adjusted_first_start = _clamp(first_start - leading_padding, 0.0, first_end)
        merged[0] = (adjusted_first_start, first_end)
        
        last_start, last_end = merged[-1]
        adjusted_last_end = _clamp(last_end + trailing_padding, last_start, duration)
        merged[-1] = (last_start, adjusted_last_end)
    
    return merged


def _find_nearest_silence_edge(
    target_time: float,
    silences: Sequence[SilenceWindow],
    direction: str = "after",
    max_search: float = 0.5,
) -> Optional[float]:
    """
    Find the nearest silence edge to a target time.
    
    Args:
        target_time: The time we want to find silence near
        silences: List of silence windows
        direction: "before" or "after" - which direction to search
        max_search: Maximum distance to search for silence (seconds)
    
    Returns:
        Time of nearest silence edge, or None if no silence found within max_search
    """
    if direction == "before":
        # Look for silence end (where speech starts) before target_time
        candidates = [
            s.end for s in silences 
            if s.end <= target_time and (target_time - s.end) <= max_search
        ]
        return max(candidates) if candidates else None
    else:  # "after"
        # Look for silence start (where speech ends) after target_time
        candidates = [
            s.start for s in silences 
            if s.start >= target_time and (s.start - target_time) <= max_search
        ]
        return min(candidates) if candidates else None


def _get_words_in_segment(
    words: List[dict],
    seg_start: float,
    seg_end: float,
) -> str:
    """Extract and format the words that fall within a time segment."""
    words_in_segment = []
    for word in words:
        word_start = word.get("start", 0)
        word_end = word.get("end", 0)
        # Include word if it overlaps with the segment
        if word_end > seg_start and word_start < seg_end:
            words_in_segment.append(word.get("word", "").strip())
    
    if not words_in_segment:
        return "(no words detected)"
    
    # Join words and limit length for readability
    phrase = " ".join(words_in_segment)
    if len(phrase) > 80:
        phrase = phrase[:77] + "..."
    return f'"{phrase}"'


def _validate_segments_with_silence(
    segments: List[Tuple[float, float]],
    words: List[dict],
    silences: Sequence[SilenceWindow],
    duration: float,
    boundary_padding: float = -0.1,
    trailing_padding: float = 2.0,
    search_tolerance: float = 0.5,
) -> List[Tuple[float, float]]:
    """
    Adjust Whisper-based segments to cut at actual silence points in the waveform.
    
    This ensures we never cut in the middle of audio - we only cut where the
    waveform actually falls to silence.
    
    Args:
        segments: Initial segments from Whisper word grouping
        words: Original word list from Whisper (for displaying text)
        silences: Detected silence windows from waveform analysis
        duration: Total video duration
        boundary_padding: Padding to apply at cut points (negative = tighter)
        trailing_padding: Extra padding for the last segment
        search_tolerance: How far to search for silence around boundaries
    
    Returns:
        Adjusted segments that cut at actual silence points
    """
    if not segments:
        return [(0.0, duration)]
    
    adjusted = []
    
    print(f"\n{'='*88}")
    print(f"🌊 WAVEFORM VALIDATION")
    print(f"{'='*88}")
    print(f"Validating {len(segments)} segment(s) against waveform silence...\n")
    
    for i, (seg_start, seg_end) in enumerate(segments):
        is_first = (i == 0)
        is_last = (i == len(segments) - 1)
        
        original_start = seg_start
        original_end = seg_end
        
        # Get the phrase for this segment
        phrase = _get_words_in_segment(words, seg_start, seg_end)
        
        # Track validation status
        start_validated = is_first  # First segment start is always OK
        end_validated = False
        start_adjusted = False
        end_adjusted = False
        
        # For segment start: find where silence actually ends before this segment
        if not is_first:
            silence_end = _find_nearest_silence_edge(
                seg_start, silences, direction="before", max_search=search_tolerance
            )
            if silence_end is not None:
                adjusted_start = silence_end - boundary_padding
                if abs(adjusted_start - seg_start) > 0.05:
                    start_adjusted = True
                seg_start = adjusted_start
                start_validated = True
            else:
                start_validated = False
        
        # For segment end: find where silence actually starts after this segment
        if not is_last:
            silence_start = _find_nearest_silence_edge(
                seg_end, silences, direction="after", max_search=search_tolerance
            )
            if silence_start is not None:
                adjusted_end = silence_start + boundary_padding
                if abs(adjusted_end - seg_end) > 0.05:
                    end_adjusted = True
                seg_end = adjusted_end
                end_validated = True
            else:
                end_validated = False
        else:
            # Last segment - search further forward
            silence_start = _find_nearest_silence_edge(
                seg_end, silences, direction="after", 
                max_search=trailing_padding + search_tolerance
            )
            if silence_start is not None:
                adjusted_end = min(silence_start + boundary_padding + trailing_padding, duration)
                if abs(adjusted_end - seg_end) > 0.05:
                    end_adjusted = True
                seg_end = adjusted_end
                end_validated = True
            else:
                # No silence found - extend anyway
                adjusted_end = min(seg_end + trailing_padding, duration)
                end_adjusted = True
                seg_end = adjusted_end
                end_validated = False
        
        # Ensure segment is valid
        seg_start = _clamp(seg_start, 0.0, duration)
        seg_end = _clamp(seg_end, seg_start + 0.01, duration)
        
        adjusted.append((seg_start, seg_end))
        
        # Print detailed segment info
        print(f"Segment {i+1}:")
        print(f"  Phrase: {phrase}")
        print(f"  Time:   [{original_start:.2f}s → {original_end:.2f}s]", end="")
        if start_adjusted or end_adjusted:
            print(f" → [{seg_start:.2f}s → {seg_end:.2f}s]")
        else:
            print()
        
        # Validation status
        if is_first and is_last:
            status = "✅ Only segment (no cuts needed)"
        elif is_first:
            if end_validated:
                status = "✅ Waveform agrees (end)" if not end_adjusted else "📍 Adjusted to silence (end)"
            else:
                status = "⚠️  No silence found for end cut"
        elif is_last:
            if start_validated:
                if end_validated:
                    status = "✅ Waveform agrees (start+end)" if not (start_adjusted or end_adjusted) else "📍 Adjusted to silence (start+end)"
                else:
                    status_start = "✅" if not start_adjusted else "📍"
                    status = f"{status_start} Start validated, end extended (+{trailing_padding}s)"
            else:
                status = "⚠️  No silence found for start cut"
        else:
            if start_validated and end_validated:
                if not start_adjusted and not end_adjusted:
                    status = "✅ Waveform agrees"
                else:
                    status = "📍 Adjusted to silence"
            elif start_validated:
                status = "📍 Start validated, ⚠️  end not validated"
            elif end_validated:
                status = "⚠️  Start not validated, 📍 end validated"
            else:
                status = "⚠️  No silence found for cuts"
        
        print(f"  Status: {status}")
        print()
    
    print(f"{'='*88}")
    print(f"✅ Waveform validation complete.\n")
    return adjusted


def _print_transcript(words: List[dict]) -> None:
    """Print the full transcript from word list in a readable format."""
    if not words:
        print("📄 post -tighten: no transcript detected.")
        return
    
    print(f"\n📄 post -tighten: words detected → {len(words)} words")
    print("=" * 80)
    
    # Build transcript from words
    transcript_words = [w.get("word", "").strip() for w in words]
    transcript_text = " ".join(transcript_words)
    print(transcript_text)
    print("=" * 80)
    print()


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
    Dependencies:
        - Requires a single rough cut named `<title>-<take_id>-rough.mp4` in the working directory.
    Failure behaviour:
        - Exits without modifying files when the rough cut is absent or when more than one candidate rough cut exists.
        - Prompts before overwriting `<title>-<take_id>-rough-tight.mp4` unless `--yes` is specified.
    Output:
        - Generates `<title>-<take_id>-rough-tight.mp4`, i.e., the same base filename with `-tight` appended before `.mp4`.
    """
    parser = build_cli_parser(
        stage="tighten",
        summary="Remove leading, trailing, and mid-take silences from a rough cut using Whisper (default) or silence detection.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=None,
        help=f"Use silence detection instead of Whisper. Silence threshold in dB (e.g., {SILENCE_THRESHOLD_DB})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SILENCE_THRESHOLD_DB,
        help=f"(Deprecated: use --silence-threshold) Silence threshold in dB (default: {SILENCE_THRESHOLD_DB})",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=MIN_SILENCE_DURATION_SECONDS,
        help=f"Minimum silence duration in seconds to remove (only for silence detection mode, default: {MIN_SILENCE_DURATION_SECONDS})",
    )
    parser.add_argument(
        "--boundary-padding",
        type=float,
        default=BOUNDARY_PADDING_SECONDS,
        help=f"Padding around silence boundaries in seconds, negative values tighten more (only for silence detection mode, default: {BOUNDARY_PADDING_SECONDS})",
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
        "--merge-tolerance",
        type=float,
        default=WORD_MERGE_TOLERANCE_SECONDS,
        help=f"Maximum gap between words to keep in same segment, prevents mid-sentence cuts (only for Whisper mode, default: {WORD_MERGE_TOLERANCE_SECONDS}s)",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="large-v2",
        help="Whisper model to use for transcription (default: large-v2)",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="tighten",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

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
    leading_padding = parsed.leading_padding
    trailing_padding = parsed.trailing_padding
    duration = _probe_duration(rough_video, env)
    
    # Determine which mode to use
    use_silence_detection = parsed.silence_threshold is not None
    
    if use_silence_detection:
        # SILENCE DETECTION MODE (legacy path)
        print("🔊 post -tighten: using silence detection mode")
        
        threshold_db = parsed.silence_threshold
        min_silence = parsed.min_silence
        boundary_padding = parsed.boundary_padding
        
        print(
            f"🎧 post -tighten: detecting silences (threshold={threshold_db:.1f} dB, "
            f"min_duration={min_silence:.1f}s, padding={boundary_padding:.2f}s, "
            f"start_edge={leading_padding:.2f}s, end_edge={trailing_padding:.2f}s)."
        )
        silences = _detect_silences(rough_video, env, threshold_db, min_silence)
        print(f"🔍 post -tighten: raw silences detected: {_format_windows(silences)}.")

        long_silences = [
            window
            for window in silences
            if window.duration >= min_silence
        ]
        print(f"🪵 post -tighten: silences ≥ {min_silence:.1f}s: {_format_windows(long_silences)}.")

        keep_segments = _build_keep_segments(
            duration, long_silences, boundary_padding, leading_padding, trailing_padding
        )
        
        print(
            f"🔊 post -tighten: detected {len(long_silences)} silence window(s) ≥ {min_silence:.1f}s with threshold {threshold_db:.1f} dB."
        )
    else:
        # WHISPER MODE (default path using stable-ts)
        print("🎤 post -tighten: using Whisper mode (detecting speech boundaries with stable-ts)")
        
        # Check if we have a cached transcription
        silence_json = env.directory / "silence.json"
        words = None
        
        if silence_json.exists():
            if env.auto_confirm:
                reuse = True
                print(f"♻️  post -tighten: found existing '{silence_json.name}', reusing it (--yes mode).")
            else:
                response = input(f"♻️  post -tighten: found existing '{silence_json.name}'. Reuse it? [Y/n]: ").strip().lower()
                reuse = response not in ("n", "no")
            
            if reuse:
                try:
                    with open(silence_json, 'r') as f:
                        words = json.load(f)
                    print(f"✅ post -tighten: loaded {len(words)} words from '{silence_json.name}'.")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"⚠️  post -tighten: failed to load '{silence_json.name}': {e}")
                    print(f"⏳ post -tighten: running fresh transcription...")
                    words = None
        
        # Run stable-ts if we don't have cached words
        if words is None:
            words = _run_stable_whisper(
                rough_video, env, model_name=parsed.whisper_model
            )
        
        # Print transcript
        _print_transcript(words)
        
        # Extract initial speech segments from Whisper word grouping
        initial_segments = _extract_speech_segments_from_words(
            words, duration, leading_padding, trailing_padding, merge_tolerance=parsed.merge_tolerance
        )
        
        print(f"🎤 post -tighten: detected {len(words)} word(s) from Whisper transcription.")
        print(f"🔗 post -tighten: merging words within {parsed.merge_tolerance:.2f}s to prevent mid-sentence cuts.")
        print(f"📊 post -tighten: initial segments from Whisper: {len(initial_segments)}")
        
        # Run silence detection to find actual quiet points in the waveform
        # Use a sensitive threshold to catch all quiet moments
        silence_threshold_db = -40.0  # More sensitive than full silence detection
        min_silence_duration = 0.1  # Catch even brief pauses
        
        print(f"\n🔍 post -tighten: analyzing waveform for silence points (threshold={silence_threshold_db:.1f} dB)...")
        silences = _detect_silences(rough_video, env, silence_threshold_db, min_silence_duration)
        print(f"✅ post -tighten: found {len(silences)} silence window(s) in waveform.")
        
        # Validate and adjust segments to cut at actual silence points
        keep_segments = _validate_segments_with_silence(
            initial_segments,
            words,
            silences,
            duration,
            boundary_padding=parsed.boundary_padding,
            trailing_padding=trailing_padding,
            search_tolerance=0.5,
        )

    # Common output for both modes
    formatted_segments = (
        ", ".join(
            f"[{start:.2f}s → {end:.2f}s | {(end-start):.2f}s]" for start, end in keep_segments
        )
        if keep_segments
        else "none"
    )
    print(f"🎬 post -tighten: segments to keep: {formatted_segments}.")
    
    print(
        f"✂️  post -tighten: keeping {len(keep_segments)} segment(s) totalling {_segments_total(keep_segments):.1f}s out of {duration:.1f}s."
    )

    _encode_tightened(rough_video, tightened_video, keep_segments, env)

    print(
        f"✅ post -tighten: wrote tightened cut to '{tightened_video.name}'."
    )
