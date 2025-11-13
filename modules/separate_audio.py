import shutil
import subprocess
from pathlib import Path

try:
    from .common import StageEnvironment, build_cli_parser
except ImportError:  # pragma: no cover - script mode fallback
    from common import StageEnvironment, build_cli_parser


_FORMAT_PRESETS = {
    "wav": ["-c:a", "pcm_s24le"],
    "flac": ["-c:a", "flac"],
    "aac": ["-c:a", "aac", "-b:a", "320k"],
}


def _ensure_tool(tool: str, env: StageEnvironment) -> None:
    if shutil.which(tool) is None:
        env.abort(f"Required dependency '{tool}' was not found on PATH. Install FFmpeg and try again.")


def _resolve_input(path: str, env: StageEnvironment) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (env.directory / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        env.abort(f"Input file '{candidate}' does not exist.")
    if not candidate.is_file():
        env.abort(f"Input path '{candidate}' is not a file.")
    return candidate


def _build_output_path(input_path: Path, audio_format: str) -> Path:
    suffix = ".m4a" if audio_format == "aac" else f".{audio_format}"
    return input_path.with_name(f"{input_path.stem}-audio{suffix}")


def run(args):
    """
    Extract the audio track from a video file and save it alongside the source.
    """
    parser = build_cli_parser(
        stage="separate-audio",
        summary="Extract the audio track from a video file and save it next to the source.",
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the video file to extract audio from.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(_FORMAT_PRESETS.keys()),
        default="wav",
        help="Audio container/codec to export.",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=48000,
        help="Target sample rate in Hz (use 0 to keep the original).",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=0,
        help="Channel count to force (use 0 to keep the original layout).",
    )

    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="separate-audio",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    _ensure_tool("ffmpeg", env)

    input_path = _resolve_input(parsed.file, env)
    output_path = _build_output_path(input_path, parsed.format)
    env.ensure_output_path(output_path)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-vn",
    ]

    if parsed.sample_rate > 0:
        cmd.extend(["-ar", str(parsed.sample_rate)])
    if parsed.channels > 0:
        cmd.extend(["-ac", str(parsed.channels)])

    cmd.extend(_FORMAT_PRESETS[parsed.format])
    cmd.append(str(output_path))

    print(f"🎧 post -separate-audio: extracting audio from '{input_path.name}'...")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"ffmpeg failed to extract audio: {result.stderr.decode().strip()}")

    print(f"✅ post -separate-audio: saved audio to '{output_path.name}'.")

