import signal
import re
import sys
import shutil
import subprocess
import tempfile
import json
import torch
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Optional

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

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

# dB floor below which audio counts as silence; tune to your mic noise.
SILENCE_THRESHOLD_DB = -24.0
# Minimum silence length (seconds) before we consider trimming it out.
MIN_SILENCE_DURATION_SECONDS = 0.5
# Extra audio to keep around each internal silence boundary (negative tightens).
BOUNDARY_PADDING_SECONDS = -0.1

# Buffer before the first segment so the intro breathes a bit.
LEADING_EDGE_PADDING_SECONDS = 0.5
# Buffer after the last segment so the outro isn’t abruptly chopped.
TRAILING_EDGE_PADDING_SECONDS = 2

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


def _run_whisperx(
    path: Path,
    env: StageEnvironment,
    model_name: str = "large-v2",
) -> Tuple[dict, Path]:
    """
    Run WhisperX on the video file and return the transcription result.
    Returns a tuple of (result_dict, temp_file_path).
    """
    try:
        import whisperx
    except ImportError:
        env.abort(
            "WhisperX is not installed. Install it with: pip install whisperx"
        )

    # Detect device
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    compute_type = "float16" if device in ["cuda", "mps"] else "int8"
    
    print(f"\n{'='*80}")
    print(f"🎤 WHISPERX TRANSCRIPTION")
    print(f"{'='*80}")
    print(f"  Device: {device.upper()}")
    print(f"  Model: {model_name}")
    print(f"  Compute Type: {compute_type}")
    print(f"  Source: {path.name}")
    print(f"{'='*80}\n")
    
    # Load model
    print(f"⏳ [1/4] Loading WhisperX model '{model_name}'...", flush=True)
    try:
        model = whisperx.load_model(model_name, device, compute_type=compute_type)
    except AttributeError as error:
        message = str(error)
        if "AudioMetaData" in message:
            env.abort(
                "WhisperX requires a recent PyTorch audio stack, but the installed "
                "torchaudio build is missing 'AudioMetaData'.\n\n"
                "Fix it by reinstalling the PyTorch packages built for Apple Silicon:\n"
                "    pip3 uninstall torchaudio\n"
                "    pip3 install --break-system-packages --pre torch torchvision torchaudio "
                "--index-url https://download.pytorch.org/whl/nightly/cpu\n\n"
                "If you continue to see this message, install Python 3.12 (PyTorch does not "
                "yet ship wheels for Python 3.13) and rerun the install commands."
            )
        raise
    print(f"✅ [1/4] Model loaded successfully.\n", flush=True)
    
    # Load audio
    print(f"⏳ [2/4] Loading audio from '{path.name}'...", flush=True)
    audio = whisperx.load_audio(str(path))
    audio_duration = len(audio) / 16000  # WhisperX uses 16kHz
    print(f"✅ [2/4] Audio loaded ({audio_duration:.1f}s).\n", flush=True)
    
    # Transcribe with progress
    print(f"⏳ [3/4] Transcribing audio (this may take a minute)...", flush=True)
    result = model.transcribe(audio, batch_size=16, print_progress=True)
    print(f"✅ [3/4] Transcription complete.\n", flush=True)
    
    # Align whisper output
    print(f"⏳ [4/4] Aligning transcript for word-level precision...", flush=True)
    detected_language = result.get("language", "en")
    print(f"    Detected language: {detected_language}", flush=True)
    
    model_a, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
    result = whisperx.align(
        result["segments"], 
        model_a, 
        metadata, 
        audio, 
        device, 
        return_char_alignments=False
    )
    print(f"✅ [4/4] Alignment complete.\n", flush=True)
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='-whisperx.json')
    temp_path = Path(temp_file.name)
    
    with open(temp_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"💾 Saved WhisperX output to: {temp_path}")
    print(f"{'='*80}\n")
    
    return result, temp_path


def _extract_speech_segments_from_whisperx(
    whisperx_result: dict,
    duration: float,
    leading_padding: float,
    trailing_padding: float,
) -> List[Tuple[float, float]]:
    """
    Extract speech segments from WhisperX result.
    Returns list of (start, end) tuples representing where speech occurs.
    """
    segments = whisperx_result.get("segments", [])
    
    if not segments:
        return [(0.0, duration)]
    
    # Extract all word boundaries
    speech_ranges: List[Tuple[float, float]] = []
    
    for segment in segments:
        words = segment.get("words", [])
        if not words:
            # Fallback to segment-level timing if no word-level timing
            start = segment.get("start", 0.0)
            end = segment.get("end", duration)
            speech_ranges.append((start, end))
        else:
            # Use word-level timing for precision
            for word in words:
                start = word.get("start")
                end = word.get("end")
                if start is not None and end is not None:
                    speech_ranges.append((start, end))
    
    if not speech_ranges:
        return [(0.0, duration)]
    
    # Merge overlapping or adjacent ranges
    speech_ranges.sort(key=lambda x: x[0])
    merged: List[Tuple[float, float]] = [speech_ranges[0]]
    
    for start, end in speech_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            # Merge overlapping ranges
            merged[-1] = (last_start, max(last_end, end))
        else:
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


def _print_whisperx_transcript(whisperx_result: dict) -> None:
    """Print the full transcript from WhisperX result in a readable format."""
    segments = whisperx_result.get("segments", [])
    
    if not segments:
        print("📄 post -tighten: no transcript detected.")
        return
    
    # Count total words
    total_words = sum(len(seg.get("words", [])) for seg in segments)
    if total_words == 0:
        # Fallback to segment text if no word-level data
        total_words = sum(len(seg.get("text", "").split()) for seg in segments)
    
    print(f"\n📄 post -tighten: words detected → {total_words} words")
    print("=" * 80)
    
    full_transcript = []
    for segment in segments:
        text = segment.get("text", "").strip()
        if text:
            full_transcript.append(text)
    
    transcript_text = " ".join(full_transcript)
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
    if not segments:
        env.abort("No segments provided for encoding.")

    concat_lines: List[str] = []
    resolved_source = source.resolve()

    def _escape(path: Path) -> str:
        safe = str(path).replace("'", "'\\''")
        return f"'{safe}'"

    for start, end in segments:
        if end <= start:
            continue
        concat_lines.append(f"file {_escape(resolved_source)}\n")
        concat_lines.append(f"inpoint {start:.6f}\n")
        concat_lines.append(f"outpoint {end:.6f}\n")

    if not concat_lines:
        env.abort("No valid segments remained after trimming.")

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt"
    ) as concat_file:
        concat_file.writelines(concat_lines)
        concat_path = Path(concat_file.name)

    print("🚀 post -tighten: stream copying video, re-encoding audio for perfect sync.")

    try:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-fflags",
            "+genpts",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            str(destination),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            env.abort(f"ffmpeg concat failed: {result.stderr.strip()}")
    finally:
        concat_path.unlink(missing_ok=True)

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
        summary="Remove leading, trailing, and mid-take silences from a rough cut using WhisperX (default) or silence detection.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=None,
        help=f"Use silence detection instead of WhisperX. Silence threshold in dB (e.g., {SILENCE_THRESHOLD_DB})",
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
        "--whisper-model",
        type=str,
        default="large-v2",
        help="WhisperX model to use (default: large-v2)",
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
    
    whisperx_temp_file: Optional[Path] = None
    
    try:
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
            # WHISPERX MODE (default path)
            print("🎤 post -tighten: using WhisperX mode (detecting speech boundaries)")
            
            # Run WhisperX
            whisperx_result, whisperx_temp_file = _run_whisperx(
                rough_video, env, model_name=parsed.whisper_model
            )
            
            # Print transcript
            _print_whisperx_transcript(whisperx_result)
            
            # Extract speech segments (these are the parts to KEEP)
            keep_segments = _extract_speech_segments_from_whisperx(
                whisperx_result, duration, leading_padding, trailing_padding
            )
            
            # Print info about segments
            segments_count = len(whisperx_result.get("segments", []))
            print(f"🎤 post -tighten: detected {segments_count} speech segment(s) from WhisperX.")

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
    finally:
        # Clean up temporary WhisperX file
        if whisperx_temp_file is not None and whisperx_temp_file.exists():
            print(f"🧹 post -tighten: cleaning up temporary file '{whisperx_temp_file}'.")
            whisperx_temp_file.unlink()
