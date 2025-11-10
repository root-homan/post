import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from .common import StageEnvironment, build_cli_parser  # type: ignore[attr-defined]
    from .tighten import (  # type: ignore[attr-defined]
        _ensure_tool,
        _probe_dimensions,
        _probe_duration,
        _run_ffmpeg_with_progress,
        AUDIO_BITRATE,
        VIDEOTOOLBOX_CODEC,
        VIDEOTOOLBOX_GLOBAL_QUALITY,
        VIDEOTOOLBOX_PIX_FMT,
    )
except ImportError:  # pragma: no cover - handles execution as a standalone script
    from common import StageEnvironment, build_cli_parser  # type: ignore[attr-defined]
    from tighten import (  # type: ignore[attr-defined]
        _ensure_tool,
        _probe_dimensions,
        _probe_duration,
        _run_ffmpeg_with_progress,
        AUDIO_BITRATE,
        VIDEOTOOLBOX_CODEC,
        VIDEOTOOLBOX_GLOBAL_QUALITY,
        VIDEOTOOLBOX_PIX_FMT,
    )


def _encode_compressed(
    source: Path,
    destination: Path,
    env: StageEnvironment,
) -> None:
    """Encode video with compression and 4:3 crop using VideoToolbox."""
    # Probe video dimensions to calculate 4:3 crop
    width, height = _probe_dimensions(source, env)
    target_width = int(height * 4 / 3)
    
    # Calculate crop filter if width needs to be reduced
    crop_filter = ""
    if width > target_width:
        x_offset = (width - target_width) // 2
        crop_filter = f"crop={target_width}:{height}:{x_offset}:0"
        print(f"📐 post -compress: cropping from {width}x{height} to {target_width}x{height} (4:3 aspect ratio).")
    elif width < target_width:
        print(f"⚠️  post -compress: video is narrower than 4:3 ({width}x{height}), skipping crop.")
    else:
        print(f"✓ post -compress: video is already 4:3 aspect ratio ({width}x{height}).")

    if sys.platform != "darwin":
        env.abort(
            "VideoToolbox hardware encoding requires macOS. "
            "Run on Apple Silicon or adjust the workflow."
        )

    encoder_label = f"{VIDEOTOOLBOX_CODEC} (q:v={VIDEOTOOLBOX_GLOBAL_QUALITY})"
    print(f"🚀 post -compress: encoding via {encoder_label}.")

    # Get source duration for progress tracking
    duration = _probe_duration(source, env)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(source),
    ]

    if crop_filter:
        cmd.extend(["-vf", crop_filter])

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

    _run_ffmpeg_with_progress(cmd, destination, duration, env)


def run(args):
    """
    Compress a video file using VideoToolbox hardware encoding and crop to 4:3 aspect ratio.
    
    Dependencies:
        - Requires a single video file named `<title>-<take_id>-rough-tight.mp4` in the working directory.
    Failure behaviour:
        - Exits without modifying files when the input is absent or when more than one candidate exists.
        - Prompts before overwriting `<title>-<take_id>-compressed.mp4` unless `--yes` is specified.
    Output:
        - Generates `<title>-<take_id>-compressed.mp4`, the compressed and cropped version.
    """
    parser = build_cli_parser(
        stage="compress",
        summary="Compress video using VideoToolbox and crop to 4:3 aspect ratio.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="compress",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    tight_video = env.expect_single_file("*-rough-tight.mp4", "tightened video")
    base_name = tight_video.name[: -len("-rough-tight.mp4")]
    compressed_video = tight_video.with_name(f"{base_name}-compressed.mp4")

    env.ensure_output_path(compressed_video)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to compress '{tight_video.name}' into '{compressed_video.name}'."
    )

    _ensure_tool("ffmpeg", env)
    _ensure_tool("ffprobe", env)

    _encode_compressed(tight_video, compressed_video, env)

    print(
        f"✅ post -compress: wrote compressed video to '{compressed_video.name}' "
        f"({VIDEOTOOLBOX_CODEC}, q:v={VIDEOTOOLBOX_GLOBAL_QUALITY})."
    )

