# ChromaDB Setup Instructions

## Installation Commands

### Option 1: Using uv (if Python 3.13 or lower)
```bash
cd /Users/akhilesh.gairola/Desktop/jiraTCGeneratorAndPlaywrightCodeGenerator
uv add chromadb
```

### Option 2: Using pip (if Python 3.13 or lower)
```bash
pip install chromadb
```

### Option 3: For Python 3.14 (Current Issue)
**Note**: ChromaDB's dependency `onnxruntime` doesn't have Python 3.14 wheels yet.

**Workaround Options:**

#### A. Use Python 3.13 instead:
```bash
# Create new environment with Python 3.13
uv python install 3.13
uv venv --python 3.13
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install chromadb
```

#### B. Install without onnxruntime (limited functionality):
```bash
uv pip install chromadb --no-deps
uv pip install pysqlite3-binary
```

#### C. Wait for Python 3.14 support or use alternative:
- Use SQLite instead (simpler, no compatibility issues)
- Or wait for ChromaDB/onnxruntime to support Python 3.14

## After Installation

The code in `chromadb_utils.py` will automatically:
1. Create a `./chroma_db` directory for data storage
2. Create a collection named "jira_tickets"
3. Store ticket information with metadata

## Usage in app.py

```python
from chromadb_utils import save_jira_ticket

# Save valid ticket
save_jira_ticket(
    ticket_id="PROJ-123",
    ticket_key="PROJ",
    description="Test case generation feature",
    is_valid=True,
    jira_url="https://welocalizedev.atlassian.net"
)

# Save invalid ticket
save_jira_ticket(
    ticket_id="PROJ-999",
    ticket_key="PROJ",
    description="Invalid ticket",
    is_valid=False,
    jira_url="https://welocalizedev.atlassian.net",
    error_message="Ticket not found"
)
```

