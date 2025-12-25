#!/bin/bash

# Fix ngrok Authentication Issues

echo "🔧 ngrok Authentication Troubleshooter"
echo "======================================"
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
    echo "❌ ngrok not found"
    exit 1
fi

echo "✅ Found ngrok at: $NGROK_CMD"
echo ""

# Check existing config
echo "📋 Checking current configuration..."
echo ""

CONFIG_FILE1="$HOME/Library/Application Support/ngrok/ngrok.yml"
CONFIG_FILE2="$HOME/.ngrok2/ngrok.yml"

if [ -f "$CONFIG_FILE1" ]; then
    echo "Found config at: $CONFIG_FILE1"
    echo "Contents:"
    cat "$CONFIG_FILE1" | grep -v "^#" | grep -v "^$" || echo "  (empty or commented)"
    echo ""
fi

if [ -f "$CONFIG_FILE2" ]; then
    echo "Found config at: $CONFIG_FILE2"
    echo "Contents:"
    cat "$CONFIG_FILE2" | grep -v "^#" | grep -v "^$" || echo "  (empty or commented)"
    echo ""
fi

echo "🔍 Testing current authentication..."
$NGROK_CMD config check 2>&1
echo ""

# Option to remove old token
echo "⚠️  If your token is invalid, you need to:"
echo ""
echo "1. Get a NEW authtoken from:"
echo "   👉 https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "2. Remove old config (optional, if you want to start fresh):"
read -p "   Do you want to remove the old config file? (y/n): " REMOVE_CONFIG

if [ "$REMOVE_CONFIG" = "y" ] || [ "$REMOVE_CONFIG" = "Y" ]; then
    if [ -f "$CONFIG_FILE1" ]; then
        rm "$CONFIG_FILE1"
        echo "✅ Removed: $CONFIG_FILE1"
    fi
    if [ -f "$CONFIG_FILE2" ]; then
        rm "$CONFIG_FILE2"
        echo "✅ Removed: $CONFIG_FILE2"
    fi
    echo ""
    echo "Now add your new token:"
    echo "  $NGROK_CMD config add-authtoken YOUR_NEW_TOKEN"
else
    echo ""
    echo "To update your token, run:"
    echo "  $NGROK_CMD config add-authtoken YOUR_NEW_TOKEN"
fi

echo ""
echo "📝 Steps to fix:"
echo "1. Visit: https://dashboard.ngrok.com/get-started/your-authtoken"
echo "2. Copy the NEW authtoken (make sure it's the latest one)"
echo "3. Run: $NGROK_CMD config add-authtoken YOUR_NEW_TOKEN"
echo "4. Test: $NGROK_CMD http 8501"
echo ""

