#!/bin/bash

# QA Assist - Network Access Startup Script
# This script starts the Streamlit app and makes it accessible on your local network

echo "🚀 Starting QA Assist with Network Access..."
echo ""

# Get Mac's IP address
MY_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

if [ -z "$MY_IP" ]; then
    echo "❌ Could not determine IP address. Trying alternative method..."
    MY_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
fi

if [ -z "$MY_IP" ]; then
    echo "❌ Error: Could not find your IP address"
    echo "Please find your IP address manually:"
    echo "  1. System Settings → Network → Wi-Fi"
    echo "  2. Or run: ifconfig | grep 'inet ' | grep -v 127.0.0.1"
    exit 1
fi

echo "✅ Your Mac's IP address: $MY_IP"
echo ""
echo "🌐 Access the app from other devices on the same WiFi:"
echo "   http://$MY_IP:8501"
echo ""
echo "💻 Access from this Mac:"
echo "   http://localhost:8501"
echo ""
echo "📱 Share this URL with your team: http://$MY_IP:8501"
echo ""

# Check if on managed Mac
if [ -d "/Library/Managed Preferences" ] || [ -f "/Library/Preferences/com.apple.alf.plist" ]; then
    echo "⚠️  MANAGED MAC DETECTED"
    echo ""
    echo "If network access doesn't work:"
    echo "  1. Run diagnostic: ./network-diagnostic.sh"
    echo "  2. Contact IT to allow port 8501"
    echo "  3. Or use ngrok (bypasses firewall): ./ngrok-setup.sh"
    echo ""
fi

echo "⚠️  Troubleshooting:"
echo "   - If others can't access, run: ./network-diagnostic.sh"
echo "   - For managed Macs, try: ./ngrok-setup.sh"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "─────────────────────────────────────────────────"
echo ""

# Verify binding will work
echo "🔍 Starting Streamlit on 0.0.0.0:8501..."
echo ""

# Start Streamlit with network access
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8501

