"""
Utility Functions
-----------------
Helper functions for API key validation and other utilities.
"""

import os
import openai

def validate_openai_key(api_key: str) -> bool:
    """
    Validate OpenAI API key by making a test call.
    
    Args:
        api_key (str): The API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True
    except Exception:
        return False

def validate_anthropic_key(api_key: str) -> bool:
    """
    Validate Anthropic API key by making a test call.
    
    Args:
        api_key (str): The API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=5,
            messages=[{"role": "user", "content": "Hello"}]
        )
        return True
    except Exception:
        return False

def validate_openrouter_key(api_key: str) -> bool:
    """
    Validate OpenRouter API key by making a test call.
    
    Args:
        api_key (str): The API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        import requests
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
        )
        return response.status_code == 200
    except Exception:
        return False

def validate_jira_credentials(jira_email: str, jira_token: str, jira_url: str = "https://welocalizedev.atlassian.net/") -> bool:
    """
    Validate Jira email and API token by making a test call.
    
    Args:
        jira_email (str): The Jira email
        jira_token (str): The Jira API token
        jira_url (str): Your Jira instance URL
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Test Jira credentials by getting current user
        response = requests.get(
            f"{jira_url}/rest/api/3/myself",
            auth=HTTPBasicAuth(jira_email, jira_token),
            timeout=10
        )
        
        return response.status_code == 200
    except Exception:
        return False

