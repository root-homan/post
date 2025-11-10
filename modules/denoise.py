import sys
import argparse
from pathlib import Path
import subprocess
import tempfile
import shutil

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from .common import StageEnvironment  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - handles execution as a standalone script
    from common import StageEnvironment  # type: ignore[attr-defined]


def _ensure_tool(tool: str, env: StageEnvironment) -> None:
    """Check that a required command-line tool is available."""
    result = shutil.which(tool)
    if result is None:
        env.abort(f"Required tool '{tool}' is not installed or not in PATH.")


def _ensure_denoiser(env: StageEnvironment) -> None:
    """Check that the denoiser dependencies are installed."""
    try:
        import torch  # noqa: F401
        import denoiser  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError as e:
        env.abort(
            f"Required library is not installed: {e}. "
            "Install with: pip3 install denoiser torch soundfile --break-system-packages"
        )


def _extract_audio(video_path: Path, audio_path: Path, env: StageEnvironment) -> None:
    """Extract audio from video file to WAV format."""
    print(f"🎵 post -denoise: extracting audio from '{video_path.name}'...")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(video_path),
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # 16-bit PCM
        "-ar",
        "16000",  # 16kHz sample rate (required by denoiser)
        "-ac",
        "1",  # Mono (required by denoiser)
        str(audio_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"Failed to extract audio: {result.stderr.decode()}")


def _denoise_audio(input_audio: Path, output_audio: Path, env: StageEnvironment) -> None:
    """Apply Facebook's denoiser to the audio file."""
    print("🧹 post -denoise: removing noise from audio (this may take a minute)...")

    try:
        import time
        import torch
        import numpy as np
        import soundfile as sf
        from denoiser import pretrained
        from denoiser.dsp import convert_audio

        start_time = time.time()

        # Prefer GPU when available, but fall back to CPU
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print("📥 post -denoise: loading DNS64 model...")
        model = pretrained.dns64().to(device)
        model.eval()
        model_load_time = time.time()

        print("📂 post -denoise: reading extracted audio...")
        wav_np, sr = sf.read(str(input_audio), dtype="float32", always_2d=True)
        # soundfile returns shape (num_samples, num_channels); convert to (channels, samples)
        wav_tensor = torch.from_numpy(np.transpose(wav_np)).to(device)

        # Ensure mono channel expected by the model
        wav_tensor = convert_audio(wav_tensor, sr, model.sample_rate, model.chin)

        processing_start = time.time()
        print(
            "🔄 post -denoise: running denoiser "
            f"({wav_tensor.shape[-1] / model.sample_rate:.1f}s of audio)..."
        )

        with torch.no_grad():
            denoised = model(wav_tensor.unsqueeze(0))[0]  # (channels, samples)

        inference_end = time.time()

        denoised_np = denoised.cpu().transpose(0, 1).numpy()  # (samples, channels)
        print("💾 post -denoise: writing denoised audio...")
        sf.write(str(output_audio), denoised_np, model.sample_rate)

        print(
            "✨ post -denoise: denoising complete "
            f"(model load: {model_load_time - start_time:.1f}s, "
            f"inference: {inference_end - processing_start:.1f}s)."
        )

    except Exception as e:
        import traceback

        env.abort(f"Denoising failed: {e}\n{traceback.format_exc()}")


def _replace_audio_in_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    env: StageEnvironment,
) -> None:
    """Replace the audio track in the video with the denoised audio."""
    print(f"🎬 post -denoise: replacing audio in video...")
    
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",  # Copy video stream without re-encoding
        "-map",
        "0:v:0",  # Video from first input
        "-map",
        "1:a:0",  # Audio from second input
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",  # Match the shorter stream duration
        str(output_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"Failed to replace audio: {result.stderr.decode()}")


def run(args):
    """
    Remove background noise from audio in a video file using Facebook's denoiser.
    
    This command processes a specific file and rewrites it with denoised audio.
    The video stream is preserved without re-encoding.
    
    Dependencies:
        - Requires ffmpeg, torch, and the 'denoiser' Python library.
        - Install with: pip3 install denoiser torch --break-system-packages
    
    Usage:
        post -denoise <video_file>
        post -denoise <video_file> --yes  # Skip confirmation
    
    Output:
        - Overwrites the input file with the denoised version after confirmation.
    """
    parser = argparse.ArgumentParser(
        prog="post -denoise",
        description="Remove background noise from audio using Facebook's denoiser.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the video file to denoise.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically overwrite the input file without confirmation.",
    )
    
    parsed = parser.parse_args(args)
    
    # Resolve the input file path
    input_file = Path(parsed.file).expanduser().resolve()
    
    if not input_file.exists():
        print(f"❌ post -denoise: file '{input_file}' does not exist.")
        raise SystemExit(1)
    
    if not input_file.is_file():
        print(f"❌ post -denoise: '{input_file}' is not a file.")
        raise SystemExit(1)
    
    # Create environment for safety checks
    env = StageEnvironment.create(
        stage="denoise",
        directory=str(input_file.parent),
        auto_confirm=parsed.yes,
    )
    
    # Check for required tools
    _ensure_tool("ffmpeg", env)
    _ensure_tool("ffprobe", env)
    _ensure_denoiser(env)
    
    # Confirm overwrite
    if not env.auto_confirm:
        answer = input(
            f"post -denoise: This will overwrite '{input_file.name}' with a denoised version. Continue? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("❌ post -denoise: operation cancelled by user.")
            raise SystemExit(0)
    else:
        print(f"⚠️  post -denoise: will overwrite '{input_file.name}' via --yes.")
    
    print(f"🔍 post -denoise: processing '{input_file.name}'...")
    
    # Use a temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Step 1: Extract audio from video
        extracted_audio = temp_path / "extracted.wav"
        _extract_audio(input_file, extracted_audio, env)
        
        # Step 2: Denoise the audio
        denoised_audio = temp_path / "denoised.wav"
        _denoise_audio(extracted_audio, denoised_audio, env)
        
        # Step 3: Replace audio in video
        output_video = temp_path / "output.mp4"
        _replace_audio_in_video(input_file, denoised_audio, output_video, env)
        
        # Step 4: Replace the original file
        print(f"💾 post -denoise: saving denoised video...")
        shutil.move(str(output_video), str(input_file))
    
    print(f"✅ post -denoise: successfully denoised '{input_file.name}'.")

