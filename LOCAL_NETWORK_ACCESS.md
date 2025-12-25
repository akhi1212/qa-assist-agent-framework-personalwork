# Local Network Access Guide

## Overview
This guide explains how to run the QA Assist application on your Mac and allow other devices on the same WiFi network to access it through your Mac's IP address.

## Prerequisites
- Mac running the application
- Other devices connected to the same WiFi network
- Python 3.13 and all dependencies installed

---

## Step 1: Find Your Mac's IP Address

### Method 1: Using System Settings (macOS Ventura/Sonoma)
1. Open **System Settings** (or **System Preferences** on older macOS)
2. Click **Network**
3. Select your WiFi connection
4. Your IP address will be shown (e.g., `192.168.1.105`)

### Method 2: Using Terminal
```bash
# Get your local IP address
ifconfig | grep "inet " | grep -v 127.0.0.1

# Or use this simpler command:
ipconfig getifaddr en0
```

The output will look like: `192.168.1.105` or `10.0.0.15`

### Method 3: Using Network Utility
1. Open **Terminal**
2. Run: `networksetup -getinfo "Wi-Fi"`
3. Look for the **IP address** field

---

## Step 2: Configure Streamlit for Network Access

### Option A: Run with Command Line Arguments (Recommended)

Run the app with network access enabled:

```bash
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

**What this does:**
- `--server.address=0.0.0.0` - Allows connections from any network interface
- `--server.port=8501` - Uses port 8501 (default Streamlit port)

### Option B: Create Streamlit Config File (Permanent)

1. Create the config directory:
```bash
mkdir -p .streamlit
```

2. Create config file:
```bash
cat > .streamlit/config.toml << EOF
[server]
address = "0.0.0.0"
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF
```

3. Then run normally:
```bash
uv run --python 3.13.11 streamlit run app.py
```

---

## Step 3: Allow Firewall Access (if needed)

If others can't access the app, you may need to allow it through macOS Firewall:

### Check Firewall Status
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

### Allow Python/Streamlit Through Firewall
1. Open **System Settings** → **Network** → **Firewall**
2. Click **Options** (or **Firewall Options**)
3. If firewall is on, click **+** to add an application
4. Navigate to: `/usr/local/bin/python3` or your Python installation
5. Set to **Allow incoming connections**

### Or use Terminal:
```bash
# Allow Python through firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/local/bin/python3
```

---

## Step 4: Access the Application

### From Your Mac:
- Open browser: `http://localhost:8501` or `http://127.0.0.1:8501`

### From Other Devices on Same WiFi:
1. Make sure they're connected to the **same WiFi network**
2. Open a web browser
3. Navigate to: `http://YOUR_MAC_IP:8501`
   - Example: `http://192.168.1.105:8501`
   - Example: `http://10.0.0.15:8501`

### Find Your IP Again (if needed):
```bash
# Quick command to get your IP
ipconfig getifaddr en0
```

---

## Step 5: Verify It's Working

### Test from Your Mac:
```bash
# Test if the server is accessible
curl http://localhost:8501
```

### Test from Another Device:
1. Open browser on another device
2. Try accessing: `http://YOUR_MAC_IP:8501`
3. You should see the QA Assist application

---

## Troubleshooting

### 🔍 Run Diagnostic Tool First

**Before troubleshooting, run the diagnostic script:**
```bash
./network-diagnostic.sh
```

This will check:
- IP address
- Streamlit binding status
- Firewall status
- Network connectivity
- Corporate network detection

---

### Problem: Others can't access the app

### Problem: Managed Mac / Corporate Computer

**If you're on a managed/corporate Mac where firewall can't be modified:**

**Solution 1: Use ngrok (Recommended - Bypasses Firewall)**
```bash
# Install ngrok first (if not installed)
brew install ngrok/ngrok/ngrok

# Or download from: https://ngrok.com/download

# Authenticate (one-time setup)
# 1. Sign up at: https://dashboard.ngrok.com/signup
# 2. Get authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
# 3. Run: ngrok config add-authtoken YOUR_TOKEN

# Use the ngrok setup script
./ngrok-setup.sh
```

This creates a public URL that works from anywhere, bypassing firewall restrictions.

**Solution 2: Contact IT Department**
- Ask IT to allow port 8501 for Python/Streamlit
- Provide them with: `./network-diagnostic.sh` output
- Request firewall exception for port 8501

**Solution 3: Check Network Policies**
Some corporate networks block device-to-device communication. Check if:
- Devices can ping each other
- Network allows peer-to-peer connections
- VPN is interfering (try disconnecting VPN)

**Solution 4: Verify Streamlit Binding**
```bash
# Check if Streamlit is bound correctly
lsof -i :8501

# Should show: *:8501 (LISTEN) not 127.0.0.1:8501
# If it shows 127.0.0.1, restart with:
./start-network.sh
```

---

### Problem: Firewall Blocking Access

**Solution 1: Check Firewall Status (if accessible)**
```bash
# Check firewall state
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# On managed Macs, this may not be modifiable
```

**Solution 2: Use ngrok (Bypasses Firewall)**
See "Managed Mac" section above - ngrok works even with strict firewalls.

**Solution 3: Try Different Port**
```bash
# Use a different port (some networks allow certain ports)
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8080
# Then access: http://YOUR_IP:8080
```

**Solution 2: Check if Streamlit is binding correctly**
```bash
# Check if port 8501 is listening
lsof -i :8501

# Should show something like:
# COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# Python  12345 user   5u  IPv4  TCP *:8501 (LISTEN)

# IMPORTANT: Look for "*:8501" not "127.0.0.1:8501"
# If it shows 127.0.0.1, it's only accessible locally
```

**Solution 3: Verify IP Address**
- Make sure you're using the correct IP address
- IP address can change if you reconnect to WiFi
- Run `ipconfig getifaddr en0` again to get current IP

**Solution 4: Check Network Connection**
- Ensure all devices are on the same WiFi network
- Some corporate networks may block device-to-device communication
- Try pinging your Mac from another device:
  ```bash
  # On another device (if it has terminal access)
  ping YOUR_MAC_IP
  ```

**Solution 5: Test from Windows Device**
If Windows devices can't access but Mac can:

**Quick Fix - Temporarily Disable Windows Firewall:**
```cmd
# Run Command Prompt as Administrator, then:
netsh advfirewall set allprofiles state off
```

**Or use Windows Settings:**
1. `Windows Key + I` → **Privacy & Security** → **Windows Security**
2. **Firewall & network protection**
3. Toggle **Windows Defender Firewall** to **Off** for your network
4. Test access: `http://YOUR_MAC_IP:8501`
5. **Re-enable after testing** and use proper allow rules

**Better Solution - Allow Connection:**
```cmd
# Run as Administrator
netsh advfirewall firewall add rule name="QA Assist Streamlit" dir=out action=allow protocol=TCP localport=8501
```

**Full Windows Firewall Guide:** See [WINDOWS_FIREWALL_GUIDE.md](WINDOWS_FIREWALL_GUIDE.md)

**Solution 6: Use ngrok (Works Everywhere)**
If nothing else works, ngrok is the most reliable solution:
```bash
./ngrok-setup.sh
# This creates a public URL that works from any device, anywhere
```

### Problem: "Connection refused" error

**Solution:**
- Make sure Streamlit is running with `--server.address=0.0.0.0`
- Check that no firewall is blocking port 8501
- Verify the IP address is correct

### Problem: Port already in use

**Solution:**
```bash
# Find what's using port 8501
lsof -i :8501

# Kill the process (replace PID with actual process ID)
kill -9 PID

# Or use a different port
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8502
```

---

## Security Considerations

⚠️ **Important Security Notes:**

1. **Local Network Only**: This setup allows access only from devices on the same WiFi network. It's relatively safe for office/home networks.

2. **No Authentication**: The app doesn't have built-in authentication. Anyone on your network can access it.

3. **API Keys**: Make sure your `.env` file is secure and not shared. API keys are stored locally.

4. **Corporate Networks**: Some corporate networks may have policies against this. Check with IT.

5. **Temporary Access**: Consider stopping the server when not in use:
   ```bash
   # Press Ctrl+C in the terminal running Streamlit
   ```

---

## Quick Start Commands

### Start the app with network access:
```bash
# Get your IP address
MY_IP=$(ipconfig getifaddr en0)
echo "Your IP address is: $MY_IP"
echo "Others can access at: http://$MY_IP:8501"

# Start the app
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

### Create a startup script:
```bash
# Create a file called start-network.sh
cat > start-network.sh << 'EOF'
#!/bin/bash
MY_IP=$(ipconfig getifaddr en0)
echo "🚀 Starting QA Assist..."
echo "📱 Your IP address: $MY_IP"
echo "🌐 Access from other devices: http://$MY_IP:8501"
echo ""
uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8501
EOF

# Make it executable
chmod +x start-network.sh

# Run it
./start-network.sh
```

---

## Example Workflow

1. **On your Mac:**
   ```bash
   # Get your IP
   ipconfig getifaddr en0
   # Output: 192.168.1.105
   
   # Start the app
   uv run --python 3.13.11 streamlit run app.py --server.address=0.0.0.0 --server.port=8501
   ```

2. **Share the URL with your team:**
   - `http://192.168.1.105:8501`

3. **Team members open the URL in their browsers:**
   - Works on laptops, phones, tablets - any device on same WiFi

4. **When done, stop the server:**
   - Press `Ctrl+C` in the terminal

---

## Advanced: Keep IP Address Static

If your IP address keeps changing, you can set a static IP:

1. **System Settings** → **Network** → **Wi-Fi** → **Details**
2. Click **TCP/IP** tab
3. Change **Configure IPv4** from "Using DHCP" to "Manually"
4. Enter your current IP, subnet mask, and router address
5. Click **Apply**

**Note:** This may require router configuration. Check with your network administrator.

---

## Alternative: ngrok (Bypasses All Firewalls)

If you're on a managed Mac or having firewall issues, **ngrok is the best solution**:

### Quick Setup:
```bash
# 1. Install ngrok
brew install ngrok/ngrok/ngrok

# 2. Sign up and get authtoken
# Visit: https://dashboard.ngrok.com/signup
# Get token from: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN

# 3. Run the setup script
./ngrok-setup.sh
```

### Benefits:
- ✅ Works on managed/corporate Macs
- ✅ Bypasses all firewalls
- ✅ Works from anywhere (not just same WiFi)
- ✅ Secure HTTPS tunnel
- ✅ Free tier available

### How it works:
1. ngrok creates a secure tunnel to your local Streamlit
2. You get a public URL (e.g., `https://abc123.ngrok.io`)
3. Share this URL with your team
4. Works from any device, anywhere in the world

---

## Summary

✅ **To allow network access:**
1. Find your Mac's IP: `ipconfig getifaddr en0`
2. Run: `./start-network.sh` (or manually with `--server.address=0.0.0.0`)
3. Share URL: `http://YOUR_IP:8501`
4. If blocked, use: `./ngrok-setup.sh`

✅ **Quick test:**
- From another device: `http://YOUR_MAC_IP:8501`
- Or use ngrok URL if firewall blocks

✅ **For Managed Macs:**
- Run diagnostic: `./network-diagnostic.sh`
- Use ngrok: `./ngrok-setup.sh` (recommended)
- Or contact IT to allow port 8501

✅ **Security:**
- Local network: Only accessible on same WiFi
- ngrok: Public URL (use only for trusted team)
- No authentication (anyone with URL can access)
- Stop server when not in use

---

**Need Help?**
1. **Run diagnostic first:** `./network-diagnostic.sh`
2. **Check that all devices are on the same WiFi**
3. **Verify Streamlit binding:** `lsof -i :8501` (should show `*:8501`)
4. **For managed Macs:** Use `./ngrok-setup.sh`
5. **Test from your Mac first:** `http://localhost:8501`

