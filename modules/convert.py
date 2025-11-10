import subprocess
from pathlib import Path

try:
    from .common import (
        StageEnvironment,
        build_cli_parser,
        find_original_rough_video,
    )  # type: ignore[attr-defined]
    from .tighten import (  # type: ignore[attr-defined]
        VIDEOTOOLBOX_CODEC,
        VIDEOTOOLBOX_GLOBAL_QUALITY,
        VIDEOTOOLBOX_PIX_FMT,
        _ensure_tool,
        _probe_duration,
        _run_ffmpeg_with_progress,
    )
except ImportError:  # pragma: no cover - script mode fallback
    from common import (
        StageEnvironment,
        build_cli_parser,
        find_original_rough_video,
    )
    from tighten import (
        VIDEOTOOLBOX_CODEC,
        VIDEOTOOLBOX_GLOBAL_QUALITY,
        VIDEOTOOLBOX_PIX_FMT,
        _ensure_tool,
        _probe_duration,
        _run_ffmpeg_with_progress,
    )


def _build_output_path(source: Path) -> Path:
    base_name = source.name[: -len("-rough.mp4")]
    return source.with_name(f"{base_name}-intra-rough.mp4")


def run(args):
    """
    Convert a rough cut to an all-intra H.264 proxy using VideoToolbox.

    The resulting file is named `<title>-<take>-intra-rough.mp4`, making it the preferred
    input for subsequent stages (tighten, process, etc.) while keeping the original rough
    cut untouched.
    """
    parser = build_cli_parser(
        stage="convert",
        summary=(
            "Convert the rough cut to an all-intra H.264 proxy for fast stream-copy "
            "operations in later stages."
        ),
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=VIDEOTOOLBOX_GLOBAL_QUALITY,
        help=(
            "VideoToolbox quality (lower values improve visual fidelity at the cost of "
            "larger files)."
        ),
    )

    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="convert",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    source = find_original_rough_video(env)
    destination = _build_output_path(source)

    env.ensure_output_path(destination)
    env.announce_checks_passed(
        f"Ready to convert '{source.name}' into all-intra proxy '{destination.name}'."
    )

    _ensure_tool("ffmpeg", env)

    duration = _probe_duration(source, env)
    quality = parsed.quality

    print(
        f"🎞️ post -convert: transcoding to all-intra H.264 (g=1, quality={quality})."
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-c:v",
        VIDEOTOOLBOX_CODEC,
        "-g",
        "1",
        "-keyint_min",
        "1",
        "-bf",
        "0",
        "-q:v",
        str(quality),
        "-pix_fmt",
        VIDEOTOOLBOX_PIX_FMT,
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(destination),
    ]

    _run_ffmpeg_with_progress(cmd, destination, duration, env)

    print(
        f"✅ post -convert: wrote all-intra proxy to '{destination.name}'. "
        "Subsequent stages will automatically prefer this file."
    )

