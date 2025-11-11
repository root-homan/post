# Post - Video Post-Production Tool

A command-line tool for video post-production workflows including denoising, tightening, transcription, and captioning.

## Features

- **AI-Powered Denoising** - Remove background noise with DeepFilterNet or Facebook's DNS64
- **Smart Silence Removal** - Automatically tighten videos by removing silence
- **Word-Level Transcription** - Generate accurate transcripts with timestamps
- **Auto-Captioning** - Add beautiful captions to videos
- **Video Processing** - Convert, compress, stitch, and more

## Quick Start

### 1. Install Dependencies

First, install Rust (required for DeepFilterNet):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 2. Run Installation Script

```bash
cd /Users/karthikuppuluri/bin/post
chmod +x install.sh
./install.sh
```

This will:
- Create a virtual environment at `post-venv/`
- Install all Python dependencies (pinned for DeepFilterNet)
- Set up the `post` command

### 3. Add to PATH (if not already)

Add this to your `~/.zshrc`:

```bash
export PATH="/Users/karthikuppuluri/bin/post:$PATH"
```

Then reload:

```bash
source ~/.zshrc
```

## Usage

The `post` command automatically uses its own isolated environment - no manual activation needed!

### Denoise Audio

Remove background noise from a video:

```bash
# Use DeepFilterNet (default - better clarity)
post -denoise video-rough.mp4

# Use Facebook's DNS64 model
post -denoise video-rough.mp4 --model facebook
```

Output: Creates `video-denoised-rough.mp4`

### Tighten Video

Remove silence and pauses:

```bash
post -tighten --dir /path/to/video/directory
```

### Transcribe

Generate word-level timestamps:

```bash
post -transcribe --dir /path/to/video/directory
```

### Add Captions

Add animated captions to video:

```bash
post -captions --dir /path/to/video/directory
```

### Full Pipeline

Run the complete workflow:

```bash
post -process --dir /path/to/video/directory
```

Runs: tighten → transcribe → essay → captions

### Other Commands

```bash
post -convert      # Convert to all-intra for fast editing
post -compress     # Compress and crop to 4:3
post -cuttakes     # Extract multiple takes
post -stitch       # Stitch videos together
post -endcard      # Add endcard
post -essay        # Generate essay from transcript
```

## Environment Variables

- `OPENAI_API_KEY` - Required for transcription and essay generation

Set in your `~/.zshrc`:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Dependencies

All dependencies are automatically managed in an isolated virtual environment.
The versions are pinned in `requirements.txt` to guarantee DeepFilterNet compatibility.

- **torch 2.2.0** - Deep learning framework
- **torchaudio 2.2.0** - Audio I/O backend required by DeepFilterNet
- **deepfilternet 0.5.6** - AI audio denoising (default)
- **denoiser 0.1.5** - Facebook's DNS64 fallback denoiser
- **stable-ts 2.19.1** - Accurate transcription with Whisper
- **openai 2.7.2** - GPT API access
- **soundfile 0.13.1** - WAV/FLAC I/O

## Denoising Models

### DeepFilterNet3 (Default)

- Better speech clarity and less muffling
- Works at 48kHz for higher quality
- Requires Rust to install

### Facebook DNS64

- Good general noise removal
- May muffle slightly
- Faster to install (no Rust required)

## Deploying to Another Computer

1. Copy the entire `post/` directory
2. Run `./install.sh`
3. Add to PATH
4. Set `OPENAI_API_KEY` environment variable

That's it! The installation script handles everything.

## Troubleshooting

### "No module named 'df'" or similar import errors

Make sure Rust is installed and rerun the installer:

```bash
cd /Users/karthikuppuluri/bin/post
./install.sh
```

### Rust compilation errors

Install the Rust toolchain and rerun:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
./install.sh
```

### Command not found

Add to PATH in `~/.zshrc`:

```bash
export PATH="/Users/karthikuppuluri/bin/post:$PATH"
```

## Development

The project structure:

```
post/
├── post                    # Main CLI script (auto-activates venv)
├── install.sh             # Setup script
├── requirements.txt       # Python dependencies
├── post-venv/            # Virtual environment (created by install.sh)
├── modules/              # Command modules
│   ├── denoise.py
│   ├── tighten.py
│   ├── transcribe.py
│   └── ...
├── remotion/             # Remotion project for captions
└── utils/                # Utility functions
```

### Adding New Dependencies

1. Add to `requirements.txt`
2. Run `./install.sh` to reinstall
3. Dependencies are automatically available to all `post` commands

## License

Private project for personal use.

