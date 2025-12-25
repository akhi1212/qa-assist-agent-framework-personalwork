#!/bin/bash

# Alternative Solution: Use ngrok for Network Access
# This bypasses firewall restrictions by creating a secure tunnel

echo "🌐 ngrok Setup for QA Assist"
echo "=============================="
echo ""
echo "ngrok creates a secure tunnel that bypasses firewall restrictions."
echo "This is useful for managed/corporate Macs where firewall can't be modified."
echo ""

# Check if ngrok is installed (check multiple locations)
NGROK_CMD=""

# Check in PATH first
if command -v ngrok &> /dev/null; then
    NGROK_CMD="ngrok"
# Check common installation locations
elif [ -f "/usr/local/bin/ngrok/ngrok" ]; then
    NGROK_CMD="/usr/local/bin/ngrok/ngrok"
elif [ -f "/usr/local/bin/ngrok" ]; then
    NGROK_CMD="/usr/local/bin/ngrok"
elif [ -f "$HOME/.local/bin/ngrok" ]; then
    NGROK_CMD="$HOME/.local/bin/ngrok"
elif [ -f "/opt/homebrew/bin/ngrok" ]; then
    NGROK_CMD="/opt/homebrew/bin/ngrok"
fi

if [ -z "$NGROK_CMD" ]; then
    echo "❌ ngrok is not installed or not found"
    echo ""
    echo "📥 Installation Options:"
    echo ""
    echo "Option 1: Homebrew (Recommended)"
    echo "  brew install ngrok/ngrok/ngrok"
    echo ""
    echo "Option 2: Direct Download"
    echo "  1. Visit: https://ngrok.com/download"
    echo "  2. Download for macOS"
    echo "  3. Extract and move to /usr/local/bin/"
    echo ""
    echo "Option 3: Using curl"
    echo "  curl -O https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
    echo "  unzip ngrok-v3-stable-darwin-amd64.zip"
    echo "  sudo mv ngrok /usr/local/bin/"
    echo ""
    echo "After installation, run this script again."
    exit 1
fi

echo "✅ ngrok found at: $NGROK_CMD"
echo ""

# Check if ngrok is authenticated
if [ ! -f ~/.ngrok2/ngrok.yml ] && [ ! -f ~/Library/Application\ Support/ngrok/ngrok.yml ]; then
    echo "⚠️  ngrok authentication required"
    echo ""
    echo "Quick setup: Run ./setup-ngrok-auth.sh"
    echo ""
    echo "Or manually:"
    echo "1. Sign up for free at: https://dashboard.ngrok.com/signup"
    echo "2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "3. Run: $NGROK_CMD config add-authtoken YOUR_TOKEN"
    echo ""
    read -p "Press Enter after you've set up ngrok authentication, or Ctrl+C to cancel..."
fi

echo ""
echo "🚀 Starting Streamlit in background..."
echo ""

# Start Streamlit in background
uv run --python 3.13.11 streamlit run app.py --server.address=127.0.0.1 --server.port=8501 > /dev/null 2>&1 &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 3

echo "✅ Streamlit started (PID: $STREAMLIT_PID)"
echo ""
echo "🌐 Starting ngrok tunnel..."
echo ""
echo "📱 Your public URL will be shown below:"
echo "   Share this URL with your team (works from anywhere!)"
echo ""
echo "⚠️  Press Ctrl+C to stop both Streamlit and ngrok"
echo ""
echo "─────────────────────────────────────────────────"
echo ""

# Start ngrok using the found command
$NGROK_CMD http 8501

# Cleanup on exit
echo ""
echo "🛑 Stopping services..."
kill $STREAMLIT_PID 2>/dev/null
pkill -f "streamlit run app.py" 2>/dev/null
echo "✅ Stopped"

