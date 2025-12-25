#!/bin/bash

# Get ngrok public URL

echo "🔗 Getting ngrok public URL..."
echo ""

# Try to get from ngrok API
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -n 1 | cut -d'"' -f4)

if [ -n "$NGROK_URL" ]; then
    echo "✅ Your ngrok public URL:"
    echo ""
    echo "   $NGROK_URL"
    echo ""
    echo "📱 Share this URL with your team (works from anywhere!)"
    echo ""
    echo "🌐 Access from Windows:"
    echo "   1. Open any web browser (Chrome, Edge, Firefox)"
    echo "   2. Paste this URL: $NGROK_URL"
    echo "   3. Press Enter"
    echo ""
else
    echo "⚠️  Could not get URL from ngrok API"
    echo ""
    echo "Make sure ngrok is running. Check the ngrok terminal window"
    echo "for the 'Forwarding' line - it shows your public URL"
    echo ""
    echo "Or visit: http://127.0.0.1:4040 to see the ngrok web interface"
fi

