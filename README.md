# QA Assist - Test Case Generator and Code Generator

## Features
- Generate test cases from Jira feature stories using AI
- Multiple AI provider support (OpenAI, Anthropic, OpenRouter)
- Automatic API key persistence in `.env` file
- Edit and manage multiple test cases
- Regenerate test cases with AI feedback
- Publish test cases to Jira (coming soon)

## Quick Start

### Run the application (Local only):
```bash
uv run streamlit run app.py
```

### Run with Network Access (Share with team on same WiFi):
```bash
# Option 1: Use the startup script (recommended)
./start-network.sh

# Option 2: Run manually
uv run streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

### For Managed/Corporate Macs (Firewall Issues):
```bash
# Use ngrok to bypass firewall restrictions
./ngrok-setup.sh
# This creates a public URL that works from anywhere
```

### Troubleshooting Network Access:
```bash
# Run diagnostic tool
./network-diagnostic.sh
```

**📖 For detailed network access instructions, see [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md)**

**🪟 Windows Firewall Issues?** See [WINDOWS_FIREWALL_GUIDE.md](WINDOWS_FIREWALL_GUIDE.md)

### First Time Setup:
1. Select your AI provider (OpenAI, Anthropic, or OpenRouter)
2. Enter your API key
3. Click "Test & Save API Key"
4. Your key will be validated and saved to `.env` file automatically

### Next Time:
- Your API key will be loaded automatically from `.env` file
- No need to enter it again unless you want to update it

## API Keys

### Automatic Persistence
When you validate an API key successfully, it's automatically saved to `.env` file and will be loaded on next restart.

### Manual Setup (Optional)
If you prefer to set up keys manually:
1. Copy `env.example` to `.env`
2. Add your API keys
3. Restart the application

## Jira Configuration
Similarly, Jira email and API token are saved to `.env` file after you enter them once.

## Security
- `.env` file is in `.gitignore` (never committed to git)
- API keys are never displayed in plain text in the UI
- Keys are stored locally on your machine only