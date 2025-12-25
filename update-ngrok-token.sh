#!/bin/bash

# Update ngrok Authtoken

echo "🔐 Update ngrok Authtoken"
echo "========================"
echo ""

NGROK_CMD="/usr/local/bin/ngrok/ngrok"

if [ ! -f "$NGROK_CMD" ]; then
    echo "❌ ngrok not found at $NGROK_CMD"
    exit 1
fi

echo "✅ Found ngrok"
echo ""

# Show current status
echo "Current config status:"
$NGROK_CMD config check 2>&1
echo ""

echo "📝 To fix the invalid token issue:"
echo ""
echo "1. Visit your ngrok dashboard:"
echo "   👉 https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "2. Make sure you're logged into the correct account"
echo ""
echo "3. Copy the authtoken (it should start with something like 2... or 3...)"
echo ""
echo "4. Paste it below when prompted"
echo ""

read -p "Enter your NEW authtoken (or press Ctrl+C to cancel): " NEW_TOKEN

if [ -z "$NEW_TOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

echo ""
echo "🔐 Updating authtoken..."

# Remove old config first
CONFIG_FILE="$HOME/Library/Application Support/ngrok/ngrok.yml"
if [ -f "$CONFIG_FILE" ]; then
    echo "Removing old config..."
    rm "$CONFIG_FILE"
fi

# Add new token
$NGROK_CMD config add-authtoken "$NEW_TOKEN"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Token updated successfully!"
    echo ""
    echo "Testing connection..."
    echo ""
    
    # Quick test (will fail if token still invalid, but shows better error)
    timeout 5 $NGROK_CMD http 8501 2>&1 | head -n 10 || echo ""
    
    echo ""
    echo "If you see 'ERR_NGROK_107' above, the token is still invalid."
    echo "Make sure you:"
    echo "  - Are logged into the correct ngrok account"
    echo "  - Copied the token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "  - The token hasn't been reset or revoked"
    echo ""
    echo "If no errors, you can now run: ./ngrok-setup.sh"
else
    echo ""
    echo "❌ Failed to update token. Please check:"
    echo "  1. Token is correct"
    echo "  2. You're logged into ngrok dashboard"
    echo "  3. Token hasn't been reset"
    exit 1
fi

