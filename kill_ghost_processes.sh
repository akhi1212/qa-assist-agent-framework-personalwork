#!/bin/bash
# Script to kill ghost Playwright/Chromium processes on Mac

echo "🔍 Finding Playwright/Chromium processes..."

# Find and kill Chromium processes spawned by Playwright
pkill -f "chromium.*--remote-debugging" 2>/dev/null
pkill -f "chromium.*--user-data-dir" 2>/dev/null
pkill -f "Google Chrome.*--remote-debugging" 2>/dev/null

# Find and kill any orphaned browser processes
ps aux | grep -i "chromium\|chrome.*remote-debugging" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

# Kill Python processes that might be holding browser connections
ps aux | grep -i "python.*playwright\|python.*recording" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

echo "✅ Ghost processes killed (if any were found)"
echo "💡 If processes persist, try: sudo pkill -9 -f chromium"

