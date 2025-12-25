# Windows Firewall Configuration Guide

## Quick Solution: Temporarily Disable Windows Firewall

### Method 1: Using Windows Settings (Easiest)

1. **Open Windows Security:**
   - Press `Windows Key + I` to open Settings
   - Go to **Privacy & Security** → **Windows Security**
   - Click **Firewall & network protection**

2. **Disable Firewall:**
   - You'll see three network profiles: **Domain network**, **Private network**, **Public network**
   - For each active network, click on it
   - Toggle **Windows Defender Firewall** to **Off**
   - Click **Yes** when prompted

3. **Test Access:**
   - Try accessing: `http://YOUR_MAC_IP:8501`
   - If it works, the issue was Windows Firewall

4. **Re-enable After Testing:**
   - Go back and toggle Firewall **On** for each network
   - Then use Method 2 below to allow the connection properly

---

### Method 2: Using Command Prompt (Faster)

**⚠️ Run Command Prompt as Administrator:**

1. **Open Command Prompt as Admin:**
   - Press `Windows Key + X`
   - Select **Windows Terminal (Admin)** or **Command Prompt (Admin)**
   - Click **Yes** on UAC prompt

2. **Disable Firewall Temporarily:**
   ```cmd
   netsh advfirewall set allprofiles state off
   ```

3. **Test Access:**
   - Open browser on Windows: `http://YOUR_MAC_IP:8501`

4. **Re-enable Firewall:**
   ```cmd
   netsh advfirewall set allprofiles state on
   ```

---

## Better Solution: Allow Connection Through Firewall (Recommended)

Instead of disabling firewall completely, allow the specific connection:

### Method 1: Using Windows Settings

1. **Open Windows Security:**
   - `Windows Key + I` → **Privacy & Security** → **Windows Security**
   - Click **Firewall & network protection**
   - Click **Allow an app through firewall**

2. **Add Exception:**
   - Click **Change settings** (requires admin)
   - Click **Allow another app...**
   - Click **Browse...**
   - Navigate to your browser executable:
     - Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
     - Edge: `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
     - Firefox: `C:\Program Files\Mozilla Firefox\firefox.exe`
   - Click **Add**
   - Check both **Private** and **Public** boxes
   - Click **OK**

### Method 2: Using Command Prompt (Advanced)

**Run as Administrator:**

```cmd
# Allow outbound connections to port 8501
netsh advfirewall firewall add rule name="QA Assist Streamlit" dir=out action=allow protocol=TCP localport=8501

# Allow inbound connections (if needed)
netsh advfirewall firewall add rule name="QA Assist Streamlit Inbound" dir=in action=allow protocol=TCP localport=8501
```

### Method 3: Allow All Outbound HTTP Connections (Simplest)

**Run as Administrator:**

```cmd
# Allow all outbound HTTP/HTTPS traffic
netsh advfirewall firewall add rule name="Allow HTTP Outbound" dir=out action=allow protocol=TCP localport=80,443,8501
```

---

## Troubleshooting Steps

### Step 1: Verify Mac is Accessible

On Windows, open Command Prompt and test:

```cmd
# Ping your Mac to verify network connectivity
ping YOUR_MAC_IP

# Test if port 8501 is reachable
telnet YOUR_MAC_IP 8501
```

If ping works but telnet doesn't, it's likely a firewall issue.

### Step 2: Check Windows Firewall Status

```cmd
# Check firewall status
netsh advfirewall show allprofiles state
```

### Step 3: Test with Firewall Disabled

1. Disable Windows Firewall (Method 1 or 2 above)
2. Try accessing: `http://YOUR_MAC_IP:8501`
3. If it works → Windows Firewall was blocking
4. If it still doesn't work → Issue is on Mac side (firewall or network policy)

### Step 4: Verify Mac Firewall

On your Mac, check if Streamlit is accessible:

```bash
# On Mac terminal
lsof -i :8501

# Should show: *:8501 (LISTEN)
# If it shows 127.0.0.1:8501, restart with:
./start-network.sh
```

---

## Quick Test Script for Windows

Create a file `test-connection.bat` on Windows:

```batch
@echo off
echo Testing connection to Mac...
echo.

set /p MAC_IP="Enter your Mac's IP address: "

echo.
echo Testing ping...
ping -n 4 %MAC_IP%

echo.
echo Testing HTTP connection...
curl http://%MAC_IP%:8501

echo.
echo If you see HTML content, connection works!
echo If you see "Connection refused" or timeout, check firewalls.
pause
```

---

## Common Issues and Solutions

### Issue 1: "Connection Timed Out"

**Possible Causes:**
- Windows Firewall blocking outbound
- Mac Firewall blocking inbound
- Network policy blocking device-to-device communication

**Solutions:**
1. Disable Windows Firewall temporarily (see Method 1 above)
2. If still doesn't work, use ngrok: `./ngrok-setup.sh` on Mac

### Issue 2: "Connection Refused"

**Possible Causes:**
- Streamlit not running
- Streamlit bound to 127.0.0.1 instead of 0.0.0.0
- Mac Firewall blocking

**Solutions:**
1. On Mac, verify: `lsof -i :8501` shows `*:8501`
2. Restart Streamlit: `./start-network.sh`
3. Check Mac firewall settings

### Issue 3: Works on Mac but not Windows

**This usually means:**
- Windows Firewall is blocking (most common)
- Windows network profile is set to "Public" (more restrictive)

**Solutions:**
1. **Change Network Profile to Private:**
   - `Windows Key + I` → **Network & Internet** → **Wi-Fi** or **Ethernet**
   - Click on your network
   - Set to **Private** (not Public)

2. **Disable Windows Firewall for Private network:**
   - Windows Security → Firewall → Private network
   - Toggle off temporarily

3. **Or use ngrok** (bypasses all firewalls):
   - On Mac: `./ngrok-setup.sh`
   - Share the ngrok URL with Windows users

---

## Security Notes

⚠️ **Important:**

1. **Temporary Only:** Only disable firewall for testing. Re-enable after confirming the issue.

2. **Use Allow Rules:** Instead of disabling, create specific allow rules (safer).

3. **Network Profile:** Private networks are safer than Public. If on Public, consider switching to Private.

4. **Corporate Networks:** If on corporate network, check with IT before modifying firewall.

---

## Recommended Approach

1. **First:** Try allowing the connection (Method 2 under "Better Solution")
2. **If that doesn't work:** Temporarily disable to confirm it's the firewall
3. **If confirmed:** Re-enable and create proper allow rules
4. **Alternative:** Use ngrok on Mac (bypasses all firewalls)

---

## Quick Reference Commands

### Check Firewall Status
```cmd
netsh advfirewall show allprofiles state
```

### Disable Firewall (Temporary)
```cmd
netsh advfirewall set allprofiles state off
```

### Enable Firewall
```cmd
netsh advfirewall set allprofiles state on
```

### Allow Port 8501
```cmd
netsh advfirewall firewall add rule name="QA Assist" dir=out action=allow protocol=TCP localport=8501
```

### Remove Rule
```cmd
netsh advfirewall firewall delete rule name="QA Assist"
```

---

## Still Not Working?

If Windows Firewall isn't the issue:

1. **Use ngrok on Mac:**
   ```bash
   ./ngrok-setup.sh
   ```
   This creates a public URL that works from anywhere, bypassing all firewalls.

2. **Check Mac Firewall:**
   - Run on Mac: `./network-diagnostic.sh`
   - Check if Mac firewall is blocking

3. **Network Policy:**
   - Some corporate networks block device-to-device communication
   - Try from a different network (mobile hotspot) to test

