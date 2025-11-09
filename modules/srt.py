try:
    from .common import StageEnvironment, build_cli_parser
except ImportError:
    from common import StageEnvironment, build_cli_parser


def run(args):
    """
    Dependencies:
        - Requires one video file (*.mp4, *.mov, *.avi, etc.) in the working directory.
        - Requires stable-ts to be installed: `pip install stable-ts`
        - Requires ffmpeg for audio extraction.
    Failure behaviour:
        - Aborts when no video is found or when multiple video candidates are present.
        - Prompts before overwriting an existing SRT file unless `--yes` is supplied.
    Output:
        - Produces `<video_basename>.srt`, sharing the exact basename with the video but
          switching the extension to `.srt`.
        - SRT contains word-level timestamps suitable for karaoke-style captions.
    """
    parser = build_cli_parser(
        stage="srt",
        summary="Generate word-level SRT subtitle file from a video using stable-ts.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="small",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model size to use for transcription.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="srt",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    # Find any video file in the directory
    video_extensions = ["*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm", "*.m4v"]
    video_files = []
    for ext in video_extensions:
        video_files.extend(env.directory.glob(ext))
    video_files = [path for path in video_files if path.is_file()]

    if not video_files:
        env.abort(
            f"Expected a video file in '{env.directory}', but nothing was found. "
            f"Supported formats: {', '.join(video_extensions)}"
        )

    # If multiple videos exist, look for a single "-tight" video
    if len(video_files) > 1:
        tight_videos = [v for v in video_files if "-tight" in v.stem]
        
        if not tight_videos:
            names = ", ".join(path.name for path in sorted(video_files))
            env.abort(
                f"Found multiple video files ({names}) but none contain '-tight' in the filename. "
                "Please ensure only one video exists, or have a single '-tight' video."
            )
        
        if len(tight_videos) > 1:
            names = ", ".join(path.name for path in sorted(tight_videos))
            env.abort(
                f"Found multiple '-tight' video files: {names}. "
                "Please ensure only one '-tight' video exists."
            )
        
        video_file = tight_videos[0]
    else:
        video_file = video_files[0]
    srt_file = video_file.with_suffix(".srt")

    env.ensure_output_path(srt_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to generate word-level subtitles '{srt_file.name}' "
        f"from '{video_file.name}' using model '{parsed.model}'."
    )

    # Generate word-level SRT using stable-ts
    print(f"🎙️  post -srt: transcribing audio with stable-ts (model: {parsed.model})...")
    try:
        import stable_whisper
    except ImportError:
        env.abort(
            "stable-ts is not installed. Install it with: pip install stable-ts\n"
            "Note: This will also install torch and faster-whisper as dependencies."
        )

    try:
        # Load the model
        print(f"📦 post -srt: loading Whisper model '{parsed.model}'...")
        model = stable_whisper.load_model(parsed.model)

        # Transcribe with word-level timestamps
        print(f"🔊 post -srt: processing audio from '{video_file.name}'...")
        result = model.transcribe(str(video_file), word_timestamps=True)

        # Export to SRT with word-level timing
        print(f"💾 post -srt: writing word-level SRT to '{srt_file.name}'...")
        result.to_srt_vtt(str(srt_file), word_level=True)

        print(f"✅ post -srt: successfully generated '{srt_file.name}' with word-level timestamps!")

    except Exception as e:
        env.abort(f"Failed to generate SRT: {e}")
