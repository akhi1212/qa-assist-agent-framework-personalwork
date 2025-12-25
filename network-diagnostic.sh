#!/bin/bash

# Network Diagnostic Script for QA Assist
# This script helps diagnose network access issues

echo "🔍 QA Assist Network Diagnostic Tool"
echo "======================================"
echo ""

# 1. Check IP address
echo "1️⃣ Checking IP Address..."
MY_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
if [ -z "$MY_IP" ]; then
    MY_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
fi

if [ -z "$MY_IP" ]; then
    echo "   ❌ Could not determine IP address"
else
    echo "   ✅ Your IP address: $MY_IP"
fi
echo ""

# 2. Check if Streamlit is running
echo "2️⃣ Checking if Streamlit is running..."
if lsof -i :8501 > /dev/null 2>&1; then
    echo "   ✅ Streamlit is running on port 8501"
    echo "   Process details:"
    lsof -i :8501 | head -n 2
else
    echo "   ❌ Streamlit is NOT running on port 8501"
    echo "   💡 Start the app first: ./start-network.sh"
fi
echo ""

# 3. Check how Streamlit is bound
echo "3️⃣ Checking Streamlit binding..."
if lsof -i :8501 | grep -q "0.0.0.0:8501"; then
    echo "   ✅ Streamlit is bound to 0.0.0.0 (accessible from network)"
elif lsof -i :8501 | grep -q "127.0.0.1:8501"; then
    echo "   ❌ Streamlit is bound to 127.0.0.1 (localhost only)"
    echo "   💡 Restart with: ./start-network.sh"
else
    echo "   ⚠️  Could not determine binding"
fi
echo ""

# 4. Check firewall status
echo "4️⃣ Checking Firewall Status..."
FIREWALL_STATUS=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | grep -i "enabled")
if [ -n "$FIREWALL_STATUS" ]; then
    echo "   ⚠️  Firewall is enabled"
    echo "   💡 On managed Macs, contact IT to allow port 8501"
else
    echo "   ✅ Firewall appears to be disabled or accessible"
fi
echo ""

# 5. Test local connection
echo "5️⃣ Testing Local Connection..."
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "   ✅ Local connection works (http://localhost:8501)"
else
    echo "   ❌ Local connection failed"
fi
echo ""

# 6. Test network connection
if [ -n "$MY_IP" ]; then
    echo "6️⃣ Testing Network Connection..."
    if curl -s --connect-timeout 2 http://$MY_IP:8501 > /dev/null 2>&1; then
        echo "   ✅ Network connection works (http://$MY_IP:8501)"
    else
        echo "   ❌ Network connection failed (http://$MY_IP:8501)"
        echo "   💡 This might be a firewall or network policy issue"
    fi
fi
echo ""

# 7. Network interface info
echo "7️⃣ Network Interface Information..."
echo "   Active interfaces:"
ifconfig | grep -E "^[a-z]|inet " | grep -B1 "inet " | grep -v "127.0.0.1" | head -n 10
echo ""

# 8. Check for corporate network restrictions
echo "8️⃣ Network Configuration Check..."
GATEWAY=$(route -n get default | grep gateway | awk '{print $2}' 2>/dev/null)
if [ -n "$GATEWAY" ]; then
    echo "   Gateway: $GATEWAY"
    # Check if it's a corporate network (common patterns)
    if [[ "$GATEWAY" == 10.* ]] || [[ "$GATEWAY" == 172.* ]] || [[ "$GATEWAY" == 192.168.* ]]; then
        echo "   ⚠️  Corporate/Private network detected"
        echo "   💡 Some corporate networks block device-to-device communication"
    fi
fi
echo ""

# 9. Recommendations
echo "📋 Recommendations:"
echo "==================="
echo ""
echo "If network access is not working:"
echo ""
echo "1. ✅ Make sure Streamlit is running with:"
echo "   ./start-network.sh"
echo ""
echo "2. ✅ Verify binding:"
echo "   lsof -i :8501"
echo "   Should show: *:8501 (LISTEN)"
echo ""
echo "3. ✅ Test from another device:"
echo "   Open browser: http://$MY_IP:8501"
echo ""
echo "4. ⚠️  If on corporate/managed Mac:"
echo "   - Contact IT to allow port 8501"
echo "   - Or use alternative: ngrok (see below)"
echo ""
echo "5. 🔄 Alternative: Use ngrok for tunneling"
echo "   See: ngrok-setup.sh"
echo ""

