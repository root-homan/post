#!/bin/bash
set -e

echo "🚀 Setting up 'post' video processing tool..."
echo ""

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/post-venv"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    echo "   Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Found Python: $(python3 --version)"

# DeepFilterNet depends on Rust for compiling DeepFilterLib
if ! command -v rustc &> /dev/null; then
    echo ""
    echo "❌ Rust toolchain not found."
    echo "   DeepFilterNet requires Rust to build DeepFilterLib."
    echo ""
    echo "   Install Rust with:"
    echo "   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    echo "   source \"$HOME/.cargo/env\""
    echo ""
    exit 1
fi

echo "✓ Found Rust: $(rustc --version)"

echo ""
echo "📦 Creating virtual environment at: $VENV_DIR"
if [ -d "$VENV_DIR" ]; then
    echo "   (Removing existing venv)"
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

echo ""
echo "📥 Installing Python dependencies..."
echo "   (This may take a few minutes, especially for PyTorch and DeepFilterNet)"
echo ""

if pip install -r "$SCRIPT_DIR/requirements.txt"; then
    echo ""
    echo "✅ All dependencies installed successfully!"
else
    echo ""
    echo "⚠️  Some dependencies failed to install."
    echo "   Please resolve the errors above and re-run ./install.sh."
    deactivate
    exit 1
fi

# Make the post script executable
chmod +x "$SCRIPT_DIR/post"

# Check if post is in PATH
if command -v post &> /dev/null; then
    POST_PATH=$(command -v post)
    echo ""
    echo "✅ Setup complete! The 'post' command is available at:"
    echo "   $POST_PATH"
else
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "📝 To use the 'post' command from anywhere, add to your PATH:"
    echo "   export PATH=\"$SCRIPT_DIR:\$PATH\""
    echo ""
    echo "   Add this line to your ~/.zshrc to make it permanent."
fi

echo ""
echo "🎬 Try it out:"
echo "   post -denoise your-video.mp4              # Uses DeepFilterNet (default)"
echo "   post -denoise your-video.mp4 -m facebook  # Optional fallback denoiser"
echo ""

