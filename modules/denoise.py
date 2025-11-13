import sys
import argparse
from pathlib import Path
import subprocess
import tempfile
import shutil
from abc import ABC, abstractmethod
from typing import Tuple

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

try:
    from .common import StageEnvironment  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - handles execution as a standalone script
    from common import StageEnvironment  # type: ignore[attr-defined]


##############################################################################
# Denoiser Backend Abstraction
##############################################################################


class DenoiserBackend(ABC):
    """Abstract base class for different denoising models."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the denoiser."""
        pass
    
    @property
    def required_sample_rate(self) -> int:
        """Sample rate required by the model."""
        pass
    
    @abstractmethod
    def check_dependencies(self, env: StageEnvironment) -> None:
        """Check that required dependencies are installed."""
        pass
    
    @abstractmethod
    def denoise(self, input_audio: Path, output_audio: Path, env: StageEnvironment) -> None:
        """Apply denoising to the audio file."""
        pass


class FacebookDenoiser(DenoiserBackend):
    """Facebook's Denoiser (DNS64) - Good noise removal, may muffle slightly."""
    
    @property
    def name(self) -> str:
        return "Facebook DNS64"
    
    @property
    def required_sample_rate(self) -> int:
        return 16000
    
    def check_dependencies(self, env: StageEnvironment) -> None:
        try:
            import torch  # noqa: F401
            import denoiser  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError as e:
            env.abort(
                f"Required library is not installed: {e}. "
                "Install with: pip3 install denoiser torch soundfile"
            )
    
    def denoise(self, input_audio: Path, output_audio: Path, env: StageEnvironment) -> None:
        print(f"🧹 post -denoise: removing noise with {self.name}...")
        
        try:
            import time
            import torch
            import numpy as np
            import soundfile as sf
            from denoiser import pretrained
            from denoiser.dsp import convert_audio
            
            start_time = time.time()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            print("📥 post -denoise: loading model...")
            model = pretrained.dns64().to(device)
            model.eval()
            model_load_time = time.time()
            
            print("📂 post -denoise: reading audio...")
            wav_np, sr = sf.read(str(input_audio), dtype="float32", always_2d=True)
            wav_tensor = torch.from_numpy(np.transpose(wav_np)).to(device)
            wav_tensor = convert_audio(wav_tensor, sr, model.sample_rate, model.chin)
            
            processing_start = time.time()
            print(f"🔄 post -denoise: processing ({wav_tensor.shape[-1] / model.sample_rate:.1f}s)...")
            
            with torch.no_grad():
                denoised = model(wav_tensor.unsqueeze(0))[0]
            
            inference_end = time.time()
            
            denoised_np = denoised.cpu().transpose(0, 1).numpy()
            print("💾 post -denoise: writing output...")
            sf.write(str(output_audio), denoised_np, model.sample_rate)
            
            print(
                f"✨ post -denoise: complete "
                f"(load: {model_load_time - start_time:.1f}s, "
                f"process: {inference_end - processing_start:.1f}s)"
            )
        except Exception as e:
            import traceback
            env.abort(f"Denoising failed: {e}\n{traceback.format_exc()}")


class DeepFilterNet(DenoiserBackend):
    """DeepFilterNet3 - Better speech clarity preservation, less muffling."""
    
    @property
    def name(self) -> str:
        return "DeepFilterNet3"
    
    @property
    def required_sample_rate(self) -> int:
        return 48000
    
    def check_dependencies(self, env: StageEnvironment) -> None:
        try:
            import torch  # noqa: F401
            import df  # noqa: F401
            import soundfile  # noqa: F401
        except ImportError as e:
            env.abort(
                f"Required library is not installed: {e}. "
                "Install with: pip3 install deepfilternet torch soundfile"
            )
    
    def denoise(self, input_audio: Path, output_audio: Path, env: StageEnvironment) -> None:
        print(f"🧹 post -denoise: removing noise with {self.name}...")
        
        try:
            import time
            import torch
            from df.enhance import enhance, init_df, load_audio, save_audio
            
            start_time = time.time()
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            print("📥 post -denoise: loading model...")
            model, df_state, _ = init_df(config_allow_defaults=True)
            model = model.to(device)
            model_load_time = time.time()
            
            print("📂 post -denoise: reading audio...")
            audio, metadata = load_audio(str(input_audio), sr=df_state.sr())
            sample_rate = df_state.sr()
            
            processing_start = time.time()
            duration_seconds = audio.shape[-1] / sample_rate
            print(f"🔄 post -denoise: processing ({duration_seconds:.1f}s)...")
            
            enhanced = enhance(model, df_state, audio)
            
            inference_end = time.time()
            
            print("💾 post -denoise: writing output...")
            save_audio(str(output_audio), enhanced, sample_rate)
            
            print(
                f"✨ post -denoise: complete "
                f"(load: {model_load_time - start_time:.1f}s, "
                f"process: {inference_end - processing_start:.1f}s)"
            )
        except Exception as e:
            import traceback
            env.abort(f"Denoising failed: {e}\n{traceback.format_exc()}")


# Registry of available denoisers
DENOISERS = {
    "facebook": FacebookDenoiser(),
    "deepfilter": DeepFilterNet(),
}


##############################################################################
# Helper Functions
##############################################################################


def _ensure_tool(tool: str, env: StageEnvironment) -> None:
    """Check that a required command-line tool is available."""
    result = shutil.which(tool)
    if result is None:
        env.abort(f"Required tool '{tool}' is not installed or not in PATH.")


def _get_audio_sample_rate(video_path: Path, env: StageEnvironment) -> int:
    """Get the sample rate of the audio stream in the video."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        env.abort(f"Failed to get audio sample rate: {result.stderr}")
    
    try:
        return int(result.stdout.strip())
    except ValueError:
        # Default to 48kHz if we can't detect it
        print("⚠️  post -denoise: couldn't detect sample rate, defaulting to 48000Hz")
        return 48000


def _extract_audio(
    video_path: Path,
    audio_path: Path,
    sample_rate: int,
    env: StageEnvironment
) -> None:
    """Extract audio from video file to WAV format at specified sample rate."""
    print(f"🎵 post -denoise: extracting audio from '{video_path.name}' at {sample_rate}Hz...")
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
        str(sample_rate),
        "-ac",
        "1",  # Mono
        str(audio_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"Failed to extract audio: {result.stderr.decode()}")


def _resample_audio(
    input_audio: Path,
    output_audio: Path,
    target_sample_rate: int,
    env: StageEnvironment,
) -> None:
    """Resample audio to a target sample rate."""
    print(f"🔄 post -denoise: resampling audio to {target_sample_rate}Hz...")
    
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_audio),
        "-ar",
        str(target_sample_rate),
        "-acodec",
        "pcm_s16le",
        str(output_audio),
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"Failed to resample audio: {result.stderr.decode()}")


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
        "320k",  # High-bitrate AAC - near-transparent quality
        "-shortest",  # Match the shorter stream duration
        str(output_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        env.abort(f"Failed to replace audio: {result.stderr.decode()}")


def _generate_output_filename(input_path: Path) -> Path:
    """Generate output filename with '-denoised' before the last tag."""
    stem = input_path.stem  # filename without extension
    suffix = input_path.suffix  # .mp4, .mov, etc.
    
    # Split by hyphens to find the last tag
    parts = stem.split('-')
    
    if len(parts) > 1:
        # Insert '-denoised' before the last tag
        # e.g., "video-rough" -> "video-denoised-rough"
        parts.insert(-1, 'denoised')
        new_stem = '-'.join(parts)
    else:
        # No hyphens, just append '-denoised'
        new_stem = f"{stem}-denoised"
    
    return input_path.parent / f"{new_stem}{suffix}"


def run(args):
    """
    Remove background noise from audio in a video file using AI denoising models.
    
    This command processes a specific file and creates a new denoised version.
    The video stream is preserved without re-encoding.
    
    Available Models:
        - deepfilter (default): DeepFilterNet3 - Better speech clarity, less muffling
        - facebook: Facebook DNS64 - Good noise removal, may muffle slightly
    
    Dependencies:
        - For deepfilter: pip3 install deepfilternet torch soundfile
        - For facebook: pip3 install denoiser torch soundfile
    
    Usage:
        post -denoise <video_file>
        post -denoise <video_file> --model facebook
    
    Output:
        - Creates a new file with '-denoised' inserted before the last tag.
        - Example: 'video-rough.mp4' -> 'video-denoised-rough.mp4'
    """
    parser = argparse.ArgumentParser(
        prog="post -denoise",
        description="Remove background noise from audio using AI denoising models.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the video file to denoise.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="deepfilter",
        choices=list(DENOISERS.keys()),
        help="Denoising model to use.",
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
    
    # Generate output filename
    output_file = _generate_output_filename(input_file)
    
    # Check if output file already exists
    if output_file.exists():
        print(f"❌ post -denoise: output file '{output_file.name}' already exists.")
        raise SystemExit(1)
    
    # Create environment for safety checks
    env = StageEnvironment.create(
        stage="denoise",
        directory=str(input_file.parent),
        auto_confirm=True,
    )
    
    # Check for required tools
    _ensure_tool("ffmpeg", env)
    _ensure_tool("ffprobe", env)
    
    # Get the selected denoiser backend and check dependencies
    denoiser = DENOISERS[parsed.model]
    
    # Check if dependencies are available, fallback if needed
    try:
        denoiser.check_dependencies(env)
    except (SystemExit, Exception) as e:
        if parsed.model == "deepfilter":
            print("⚠️  DeepFilterNet not available, falling back to Facebook denoiser...")
            print("   (Install Rust and deepfilternet, or run ./install.sh)")
            denoiser = DENOISERS["facebook"]
            denoiser.check_dependencies(env)
        else:
            raise
    
    print(f"🔍 post -denoise: processing '{input_file.name}'...")
    print(f"🎯 post -denoise: using {denoiser.name}")
    print(f"📝 post -denoise: will create '{output_file.name}'")
    
    # Get the original audio sample rate to preserve sync
    original_sample_rate = _get_audio_sample_rate(input_file, env)
    print(f"📊 post -denoise: original audio sample rate: {original_sample_rate}Hz")
    
    # Use a temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Step 1: Extract audio at model's required sample rate
        extracted_audio = temp_path / "extracted.wav"
        _extract_audio(input_file, extracted_audio, denoiser.required_sample_rate, env)
        
        # Step 2: Denoise using selected backend
        denoised_audio = temp_path / "denoised.wav"
        denoiser.denoise(extracted_audio, denoised_audio, env)
        
        # Step 3: Resample back to original sample rate (prevents sync drift)
        resampled_audio = temp_path / "resampled.wav"
        _resample_audio(denoised_audio, resampled_audio, original_sample_rate, env)
        
        # Step 4: Replace audio in video
        output_video = temp_path / "output.mp4"
        _replace_audio_in_video(input_file, resampled_audio, output_video, env)
        
        # Step 5: Save to new file
        print(f"💾 post -denoise: saving denoised video...")
        shutil.move(str(output_video), str(output_file))
    
    print(f"✅ post -denoise: successfully created '{output_file.name}'.")

