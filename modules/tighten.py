import signal
import re
import sys
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from .common import StageEnvironment, build_cli_parser  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - handles execution as a standalone script
    from common import StageEnvironment, build_cli_parser  # type: ignore[attr-defined]

# dB floor below which audio counts as silence; tune to your mic noise.
SILENCE_THRESHOLD_DB = -24.0
# Minimum silence length (seconds) before we consider trimming it out.
MIN_SILENCE_DURATION_SECONDS = 0.5
# Extra audio to keep around each internal silence boundary (negative tightens).
BOUNDARY_PADDING_SECONDS = -0.1

# Buffer before the first segment so the intro breathes a bit.
LEADING_EDGE_PADDING_SECONDS = 0.5
# Buffer after the last segment so the outro isn’t abruptly chopped.
TRAILING_EDGE_PADDING_SECONDS = 1

# Encoding configuration tuned for Apple Silicon hardware acceleration.
AUDIO_BITRATE = "192k"
VIDEOTOOLBOX_CODEC = "h264_videotoolbox"
VIDEOTOOLBOX_GLOBAL_QUALITY = 55
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


def _detect_silences(path: Path, env: StageEnvironment) -> Sequence[SilenceWindow]:
    detect_filter = (
        f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:d={MIN_SILENCE_DURATION_SECONDS}"
    )
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
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


def _build_keep_segments(
    duration: float, silences: Sequence[SilenceWindow]
) -> List[Tuple[float, float]]:
    segments: List[Tuple[float, float]] = []
    cursor = 0.0

    for silence in silences:
        start = _clamp(silence.start - BOUNDARY_PADDING_SECONDS, cursor, duration)
        if start > cursor:
            segments.append((cursor, start))
        cursor = _clamp(silence.end + BOUNDARY_PADDING_SECONDS, cursor, duration)

    if cursor < duration:
        segments.append((cursor, duration))

    cleaned = [(start, end) for start, end in segments if end - start > 1e-3]
    if not cleaned:
        cleaned.append((0.0, duration))
    else:
        leading_padding = LEADING_EDGE_PADDING_SECONDS
        trailing_padding = TRAILING_EDGE_PADDING_SECONDS

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
    filters: List[str] = []
    concat_inputs: List[str] = []

    for idx, (start, end) in enumerate(segments):
        start_ts = _format_ts(start)
        end_ts = _format_ts(end)
        filters.append(
            f"[0:v]trim=start={start_ts}:end={end_ts},setpts=PTS-STARTPTS[v{idx}]"
        )
        filters.append(
            f"[0:a]atrim=start={start_ts}:end={end_ts},asetpts=PTS-STARTPTS[a{idx}]"
        )
        concat_inputs.append(f"[v{idx}][a{idx}]")

    filters.append(
        f"{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[v][a]"
    )

    filter_complex = ";".join(filters)

    if sys.platform != "darwin":
        env.abort(
            "VideoToolbox hardware encoding requires macOS. "
            "Run on Apple Silicon or adjust the workflow."
        )

    encoder_label = f"{VIDEOTOOLBOX_CODEC} (q:v={VIDEOTOOLBOX_GLOBAL_QUALITY})"
    print(f"🚀 post -tighten: encoding via {encoder_label}.")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
    ]

    cmd.extend(
        [
            "-c:v",
            VIDEOTOOLBOX_CODEC,
            "-q:v",
            str(VIDEOTOOLBOX_GLOBAL_QUALITY),
            "-pix_fmt",
            VIDEOTOOLBOX_PIX_FMT,
            "-allow_sw",
            "1",
        ]
    )

    cmd.extend(
        [
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-progress",
            "pipe:1",
            "-nostats",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )

    _run_ffmpeg_with_progress(cmd, destination, _segments_total(segments), env)


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
        summary="Remove leading, trailing, and mid-take silences from a rough cut.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="tighten",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    rough_video = env.expect_single_file("*-rough.mp4", "rough cut video")
    base_name = rough_video.name[: -len("-rough.mp4")]
    tightened_video = rough_video.with_name(f"{base_name}-rough-tight.mp4")

    env.ensure_output_path(tightened_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to tighten '{rough_video.name}' into '{tightened_video.name}'."
    )

    _ensure_tool("ffmpeg", env)
    _ensure_tool("ffprobe", env)

    duration = _probe_duration(rough_video, env)
    print(
        f"🎧 post -tighten: detecting silences (threshold={SILENCE_THRESHOLD_DB:.1f} dB, "
        f"min_duration={MIN_SILENCE_DURATION_SECONDS:.1f}s, padding={BOUNDARY_PADDING_SECONDS:.2f}s, "
        f"start_edge={LEADING_EDGE_PADDING_SECONDS:.2f}s, end_edge={TRAILING_EDGE_PADDING_SECONDS:.2f}s)."
    )
    silences = _detect_silences(rough_video, env)
    print(f"🔍 post -tighten: raw silences detected: {_format_windows(silences)}.")

    long_silences = [
        window
        for window in silences
        if window.duration >= MIN_SILENCE_DURATION_SECONDS
    ]
    print(f"🪵 post -tighten: silences ≥ {MIN_SILENCE_DURATION_SECONDS:.1f}s: {_format_windows(long_silences)}.")

    keep_segments = _build_keep_segments(duration, long_silences)
    formatted_segments = (
        ", ".join(
            f"[{start:.2f}s → {end:.2f}s | {(end-start):.2f}s]" for start, end in keep_segments
        )
        if keep_segments
        else "none"
    )
    print(f"🎬 post -tighten: segments to keep: {formatted_segments}.")

    print(
        f"🔊 post -tighten: detected {len(long_silences)} silence window(s) ≥ {MIN_SILENCE_DURATION_SECONDS:.1f}s with threshold {SILENCE_THRESHOLD_DB:.1f} dB."
    )
    print(
        f"✂️  post -tighten: keeping {len(keep_segments)} segment(s) totalling {_segments_total(keep_segments):.1f}s out of {duration:.1f}s."
    )

    _encode_tightened(rough_video, tightened_video, keep_segments, env)

    print(
        f"✅ post -tighten: wrote tightened cut to '{tightened_video.name}' "
        f"({VIDEOTOOLBOX_CODEC}, q:v={VIDEOTOOLBOX_GLOBAL_QUALITY})."
    )
