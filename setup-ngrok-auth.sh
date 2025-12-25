#!/bin/bash

# Quick ngrok Authentication Setup

echo "🔐 ngrok Authentication Setup"
echo "============================"
echo ""

# Find ngrok
NGROK_CMD=""
if command -v ngrok &> /dev/null; then
    NGROK_CMD="ngrok"
elif [ -f "/usr/local/bin/ngrok/ngrok" ]; then
    NGROK_CMD="/usr/local/bin/ngrok/ngrok"
elif [ -f "/usr/local/bin/ngrok" ]; then
    NGROK_CMD="/usr/local/bin/ngrok"
fi

if [ -z "$NGROK_CMD" ]; then
    echo "❌ ngrok not found. Please install it first."
    exit 1
fi

echo "✅ Found ngrok at: $NGROK_CMD"
echo ""

# Check if already authenticated
if [ -f ~/.ngrok2/ngrok.yml ] || [ -f ~/Library/Application\ Support/ngrok/ngrok.yml ]; then
    echo "✅ ngrok is already authenticated!"
    echo ""
    echo "You can now run: ./ngrok-setup.sh"
    exit 0
fi

echo "📝 Follow these steps to authenticate ngrok:"
echo ""
echo "1. Sign up for a free ngrok account:"
echo "   👉 https://dashboard.ngrok.com/signup"
echo ""
echo "2. After signing up, get your authtoken from:"
echo "   👉 https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "3. Copy your authtoken and run this command:"
echo ""
echo "   $NGROK_CMD config add-authtoken YOUR_TOKEN_HERE"
echo ""
echo "   Example:"
echo "   $NGROK_CMD config add-authtoken 2abc123def456ghi789jkl012mno345pqr678"
echo ""
echo "4. After authentication, run: ./ngrok-setup.sh"
echo ""
read -p "Press Enter when you have your authtoken ready, or Ctrl+C to cancel..."

echo ""
echo "Enter your authtoken (or press Ctrl+C to cancel):"
read -s AUTHTOKEN

if [ -z "$AUTHTOKEN" ]; then
    echo "❌ No authtoken provided. Exiting."
    exit 1
fi

echo ""
echo "🔐 Adding authtoken..."
$NGROK_CMD config add-authtoken "$AUTHTOKEN"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Authentication successful!"
    echo ""
    echo "You can now run: ./ngrok-setup.sh"
else
    echo ""
    echo "❌ Authentication failed. Please check your authtoken and try again."
    exit 1
fi

