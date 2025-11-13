import json
import shutil
import subprocess
import tempfile
from pathlib import Path

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
        - Prompts before overwriting an existing JSON/SRT file unless `--yes` is supplied.
    Output:
        - Produces `<video_basename>.json`, containing word-level timestamps.
        - Produces `<video_basename>.srt`, containing segment-level subtitles with timecodes.
        - JSON format: [{"word": "text", "start": 0.0, "end": 0.5}, ...]
    """
    parser = build_cli_parser(
        stage="transcribe",
        summary="Generate word-level timestamps from a video using stable-ts.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model size to use for transcription.",
    )
    parsed = parser.parse_args(args)

    env = StageEnvironment.create(
        stage="transcribe",
        directory=parsed.dir,
        auto_confirm=parsed.yes,
    )

    def _ensure_tool(tool: str) -> None:
        if shutil.which(tool) is None:
            env.abort(f"Required dependency '{tool}' was not found on PATH. Install FFmpeg and try again.")

    _ensure_tool("ffmpeg")

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
    json_file = video_file.with_suffix(".json")
    srt_file = video_file.with_suffix(".srt")

    env.ensure_output_path(json_file)
    env.ensure_output_path(srt_file)
    env.announce_checks_passed(
        f"All safety checks passed. Ready to transcribe '{video_file.name}' into "
        f"'{json_file.name}' and '{srt_file.name}' using model '{parsed.model}'."
    )

    # Generate word-level timestamps using stable-ts
    print(f"🎙️  post -transcribe: transcribing audio with stable-ts (model: {parsed.model})...")
    try:
        import stable_whisper
    except ImportError:
        env.abort(
            "stable-ts is not installed. Install it with: pip install stable-ts\n"
            "Note: This will also install torch and faster-whisper as dependencies."
        )

    try:
        # Load the model
        print(f"📦 post -transcribe: loading Whisper model '{parsed.model}'...")
        model = stable_whisper.load_model(parsed.model)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_audio = Path(temp_dir) / "transcribe-audio.wav"
            print(f"🎧 post -transcribe: extracting clean audio for transcription...")
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                str(video_file),
                "-vn",
                "-map",
                "0:a:0",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-avoid_negative_ts",
                "make_zero",
                str(temp_audio),
            ]
            ffmpeg_result = subprocess.run(cmd, capture_output=True)
            if ffmpeg_result.returncode != 0:
                stderr = ffmpeg_result.stderr.decode().strip()
                env.abort(
                    "FFmpeg failed to extract audio for transcription"
                    + (f": {stderr}" if stderr else ".")
                )

            # Transcribe with word-level timestamps
            print(f"🔊 post -transcribe: processing audio from '{temp_audio.name}'...")
            result = model.transcribe(str(temp_audio), word_timestamps=True)

        # Extract words with timestamps
        print(f"💾 post -transcribe: extracting word-level timestamps to '{json_file.name}'...")
        words = []
        for segment in result.segments:
            for word in getattr(segment, "words", []):
                text = (word.word or "").strip()
                start = getattr(word, "start", None)
                end = getattr(word, "end", None)
                if not text or start is None or end is None:
                    continue
                words.append({
                    'word': text,
                    'start': float(start),
                    'end': float(end)
                })
        
        # Write to JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(words, f, indent=2, ensure_ascii=False)

        print(f"✅ post -transcribe: successfully generated '{json_file.name}' with {len(words)} words!")

        # Build SRT content from segments
        def _format_timestamp(seconds: float) -> str:
            milliseconds_total = int(round(float(seconds) * 1000))
            hours, remainder = divmod(milliseconds_total, 3600 * 1000)
            minutes, remainder = divmod(remainder, 60 * 1000)
            seconds_part, milliseconds = divmod(remainder, 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}"

        srt_lines = []
        segment_counter = 0
        for segment in result.segments:
            start = getattr(segment, "start", None)
            end = getattr(segment, "end", None)
            text = getattr(segment, "text", "")
            if start is None or end is None:
                continue
            cleaned_text = text.strip()
            if not cleaned_text:
                continue
            segment_counter += 1
            srt_lines.append(str(segment_counter))
            srt_lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
            srt_lines.append(cleaned_text)
            srt_lines.append("")

        srt_content = "\n".join(srt_lines).strip() + "\n" if srt_lines else ""
        srt_file.write_text(srt_content, encoding='utf-8')
        print(f"✅ post -transcribe: wrote subtitles to '{srt_file.name}' with {segment_counter} segments.")

    except Exception as e:
        env.abort(f"Failed to generate timestamps: {e}")

