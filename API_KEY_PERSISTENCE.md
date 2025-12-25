# API Key Persistence Feature

## Overview
API keys and Jira credentials are now automatically saved to `.env` file after successful validation, ensuring they persist across application restarts.

## How It Works

### 1. First Time Usage
When you start the app for the first time:
1. Select your AI provider (OpenAI, Anthropic, or OpenRouter)
2. Enter your API key in the text field
3. Click **"Test & Save API Key"** button
4. The app validates the key by making a test API call
5. If valid ✅, the key is automatically saved to `.env` file
6. Page refreshes and shows "✅ API Key loaded from .env file"

### 2. Subsequent Usage
When you restart the app:
1. The app automatically loads the API key from `.env` file
2. You see "✅ API Key loaded from .env file" 
3. No need to enter the key again
4. You can click "Update API Key" checkbox if you want to change it

### 3. Jira Credentials
Same behavior for Jira credentials:
- Enter Jira Email and API Token once
- Click "Save Jira Credentials"
- Automatically loaded on next restart

## Implementation Details

### New Functions

#### `save_key_to_env(provider: str, api_key: str)`
- Saves API key to `.env` file
- Creates `.env` file if it doesn't exist
- Updates existing key if already present
- Appends new key if not present

### UI Changes

#### Sidebar - API Key Section
**When key exists in .env:**
```
✅ OpenAI API Key loaded from .env file
☐ Update API Key
```

**When key doesn't exist:**
```
[API Key input field]
📺 How to generate API Key?
[Test & Save API Key button]
```

#### Sidebar - Jira Section
**When credentials exist in .env:**
```
✅ Jira credentials loaded from .env file
☐ Update Jira Credentials
```

**When credentials don't exist:**
```
[Jira Email input]
[Jira API Token input]
📺 How to generate Jira API Token?
[Save Jira Credentials button]
```

## Security

### Protected Files
- `.env` file is in `.gitignore` - never committed to git
- Only stored locally on user's machine
- API keys never displayed in plain text in UI

### Password Fields
- API Key input uses `type="password"` (shows dots)
- Jira API Token uses `type="password"` (shows dots)

## User Experience Flow

### Happy Path
1. User enters API key → Clicks "Test & Save" → ✅ Valid → Saved to .env → Page refreshes
2. User restarts app → ✅ Key loaded automatically → Ready to use
3. User can start generating test cases immediately

### Update Key Flow
1. User sees "✅ API Key loaded from .env file"
2. Checks "Update API Key" checkbox
3. Enters new key → Clicks "Test & Save" → ✅ Valid → Updated in .env → Page refreshes

## Files Modified

### app.py
- Added `save_key_to_env()` function
- Updated sidebar UI to check for existing keys
- Added logic to show/hide input fields based on key existence
- Added "Test & Save API Key" button with validation + save
- Added "Save Jira Credentials" button

### env.example
- Created template file showing required environment variables
- Users can copy this to `.env` if they prefer manual setup

### README.md
- Updated with feature documentation
- Added setup instructions
- Added security notes

## Benefits

1. ✅ **Convenience**: Enter key once, use forever
2. ✅ **Security**: Keys stored locally, never in code
3. ✅ **User-friendly**: Auto-detection of existing keys
4. ✅ **Flexible**: Can update keys anytime via checkbox
5. ✅ **Simple**: No manual file editing required

