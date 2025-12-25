"""
Authentication Store
-------------------
Handles per-user credential storage with encryption.
Stores encrypted credentials in user_creds.json file.
"""
import os
import json
from cryptography.fernet import Fernet

# Path to credentials file
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "user_creds.json")

# Generate or load encryption key
def _get_encryption_key():
    """Get or generate encryption key"""
    key_file = os.path.join(os.path.dirname(__file__), ".encryption_key")
    
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Generate new key
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

# Initialize encryption
_key = _get_encryption_key()
_cipher = Fernet(_key)

def _get_user_id(first_name: str, last_name: str) -> str:
    """Generate unique user ID from name"""
    return f"{first_name.lower()}_{last_name.lower()}"

def save_user_credentials(first_name: str, last_name: str, credentials: dict, nickname: str = None):
    """
    Save encrypted user credentials to JSON file.
    
    Args:
        first_name: User's first name
        last_name: User's last name
        credentials: Dict with keys like 'openai_key', 'jira_email', 'jira_token', 'jira_url'
        nickname: Optional 3-character nickname for quick login
    """
    user_id = _get_user_id(first_name, last_name)
    
    # Load existing credentials
    all_creds = {}
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                all_creds = json.load(f)
        except:
            all_creds = {}
    
    # Encrypt credentials (exclude nickname from encryption)
    encrypted_creds = {}
    for key, value in credentials.items():
        if value:  # Only encrypt non-empty values
            encrypted_creds[key] = _cipher.encrypt(value.encode()).decode()
    
    # Store with user metadata
    all_creds[user_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name.lower()}.{last_name.lower()}@welocalize.com",
        "credentials": encrypted_creds,
        "updated_at": os.path.getmtime(CREDENTIALS_FILE) if os.path.exists(CREDENTIALS_FILE) else None
    }
    
    # Save credentials file
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(all_creds, f, indent=2)
    
    # Store nickname mapping if provided
    if nickname:
        nickname = nickname.upper()[:3]  # Store as uppercase, max 3 chars
        nickname_file = os.path.join(os.path.dirname(__file__), "nickname_index.json")
        nickname_index = {}
        if os.path.exists(nickname_file):
            try:
                with open(nickname_file, 'r') as f:
                    nickname_index = json.load(f)
            except:
                nickname_index = {}
        
        nickname_index[nickname] = user_id
        with open(nickname_file, 'w') as f:
            json.dump(nickname_index, f, indent=2)
    
    # Save to file
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(all_creds, f, indent=2)

def load_user_credentials(first_name: str, last_name: str) -> dict:
    """
    Load and decrypt user credentials from JSON file.
    
    Args:
        first_name: User's first name
        last_name: User's last name
        
    Returns:
        Dict with decrypted credentials or empty dict if not found
    """
    user_id = _get_user_id(first_name, last_name)
    
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            all_creds = json.load(f)
        
        if user_id not in all_creds:
            return {}
        
        user_data = all_creds[user_id]
        encrypted_creds = user_data.get("credentials", {})
        
        # Decrypt credentials
        decrypted_creds = {}
        for key, encrypted_value in encrypted_creds.items():
            try:
                decrypted_creds[key] = _cipher.decrypt(encrypted_value.encode()).decode()
            except:
                pass
        
        return decrypted_creds
    except:
        return {}

def user_exists(first_name: str, last_name: str) -> bool:
    """Check if user credentials exist"""
    user_id = _get_user_id(first_name, last_name)
    
    if not os.path.exists(CREDENTIALS_FILE):
        return False
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            all_creds = json.load(f)
        return user_id in all_creds
    except:
        return False

def get_user_by_nickname(nickname: str) -> tuple:
    """
    Get user first_name and last_name by nickname.
    
    Args:
        nickname: 3-character nickname (case insensitive)
        
    Returns:
        Tuple of (first_name, last_name) or (None, None) if not found
    """
    nickname = nickname.upper()[:3]  # Normalize to uppercase, max 3 chars
    
    nickname_file = os.path.join(os.path.dirname(__file__), "nickname_index.json")
    if not os.path.exists(nickname_file):
        return None, None
    
    try:
        with open(nickname_file, 'r') as f:
            nickname_index = json.load(f)
        
        user_id = nickname_index.get(nickname)
        if not user_id:
            return None, None
        
        # Load user data
        if not os.path.exists(CREDENTIALS_FILE):
            return None, None
        
        with open(CREDENTIALS_FILE, 'r') as f:
            all_creds = json.load(f)
        
        if user_id not in all_creds:
            return None, None
        
        user_data = all_creds[user_id]
        return user_data.get("first_name"), user_data.get("last_name")
    except:
        return None, None

def nickname_exists(nickname: str) -> bool:
    """Check if nickname is already taken"""
    nickname = nickname.upper()[:3]
    nickname_file = os.path.join(os.path.dirname(__file__), "nickname_index.json")
    
    if not os.path.exists(nickname_file):
        return False
    
    try:
        with open(nickname_file, 'r') as f:
            nickname_index = json.load(f)
        return nickname in nickname_index
    except:
        return False

