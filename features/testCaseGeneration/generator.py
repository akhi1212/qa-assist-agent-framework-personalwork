"""
Test Case Generation Logic
---------------------------
Generates test cases from Jira tickets using validated credentials.
Credentials are loaded from encrypted storage (user_creds.json) and decrypted automatically.
"""
import os
import json
import re
import pandas as pd
from typing import Tuple, Optional

from auth_store import load_user_credentials

# Cache directory for test cases
CACHE_DIR = "testcaseGenerated"


def ensure_cache_dir():
    """Ensure the cache directory exists"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_file_path(ticket_id: str) -> str:
    """
    Get the cache file path for a Jira ticket ID.
    
    Args:
        ticket_id: Jira ticket ID (e.g., "PROJ-123")
        
    Returns:
        Path to the cache file
    """
    ensure_cache_dir()
    # Sanitize ticket ID for filename
    safe_ticket_id = ticket_id.replace("/", "_").replace("\\", "_")
    return os.path.join(CACHE_DIR, f"{safe_ticket_id}_test_case.json")


def load_cached_test_cases(ticket_id: str) -> Optional[dict]:
    """
    Load cached test cases for a Jira ticket ID.
    
    Args:
        ticket_id: Jira ticket ID
        
    Returns:
        Cached test cases dict or None if not found
    """
    cache_file = get_cache_file_path(ticket_id)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            # If file is corrupted, return None to regenerate
            return None
    return None


def save_test_cases_to_cache(ticket_id: str, test_cases_data: dict):
    """
    Save test cases to cache file.
    
    Args:
        ticket_id: Jira ticket ID
        test_cases_data: Test cases data dict (with status, notes, test_cases)
    """
    try:
        cache_file = get_cache_file_path(ticket_id)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Log error but don't fail the generation
        print(f"Warning: Could not save test cases to cache: {e}")


def get_user_credentials(first_name: str, last_name: str) -> Tuple[bool, str, dict]:
    """
    Get user credentials from encrypted storage (already decrypted).
    
    Args:
        first_name: User's first name
        last_name: User's last name
        
    Returns:
        Tuple of (is_valid, error_message, credentials_dict)
    """
    if not first_name or not last_name:
        return False, "First name and last name are required", {}
    
    # Load credentials from encrypted storage
    credentials = load_user_credentials(first_name, last_name)
    
    if not credentials:
        return False, "No credentials found. Please add API key and Jira credentials in settings.", {}
    
    # Check for API key (at least one provider)
    has_openai = bool(credentials.get("openai_key", ""))
    has_anthropic = bool(credentials.get("anthropic_key", ""))
    has_openrouter = bool(credentials.get("openrouter_key", ""))
    
    if not (has_openai or has_anthropic or has_openrouter):
        return False, "No API key found. Please add an API key in settings.", {}
    
    # Check for Jira credentials
    jira_email = credentials.get("jira_email", "")
    jira_token = credentials.get("jira_token", "")
    
    if not jira_email or not jira_token:
        return False, "Jira credentials not found. Please add Jira email and token in settings.", {}
    
    return True, "", credentials


def get_jira_ticket(ticket_id: str, jira_email: str, jira_token: str, jira_url: str) -> Tuple[bool, str, dict]:
    """
    Get Jira ticket data (credentials already validated separately).
    
    Args:
        ticket_id: Jira ticket ID (e.g., "PROJ-123")
        jira_email: Jira email (decrypted)
        jira_token: Jira API token (decrypted)
        jira_url: Jira instance URL (decrypted)
        
    Returns:
        Tuple of (is_valid, error_message, ticket_data)
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get ticket details (credentials already validated in settings)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{jira_url}/rest/api/3/issue/{ticket_id}",
            headers=headers,
            auth=HTTPBasicAuth(jira_email, jira_token),
            timeout=10
        )
        
        if response.status_code != 200:
            return False, f"Ticket {ticket_id} not found or inaccessible", {}
        
        ticket_data = response.json()
        return True, "", ticket_data
        
    except requests.exceptions.RequestException as e:
        return False, f"Error accessing Jira: {str(e)}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def extract_ticket_id(feature_text: str) -> Optional[str]:
    """
    Extract Jira ticket ID from feature text.
    
    Args:
        feature_text: Feature description text
        
    Returns:
        Ticket ID if found, None otherwise
    """
    # Pattern: PROJECT-123 or PROJ-456
    pattern = r'\b([A-Z]+-\d+)\b'
    matches = re.findall(pattern, feature_text)
    
    if matches:
        return matches[0]  # Return first match
    
    return None


def generate_test_cases(
    feature_text: str,
    first_name: str,
    last_name: str,
    provider: str,
    model: str
) -> Tuple[pd.DataFrame, str, Optional[str], Optional[list], Optional[dict]]:
    """
    Generate test cases with full validation.
    
    Args:
        feature_text: Feature/story description
        first_name: User's first name
        last_name: User's last name
        provider: LLM provider (OpenAI, Anthropic, OpenRouter)
        model: Model name
        
    Returns:
        Tuple of (DataFrame, raw_output, error_message, formatted_test_cases_list, context_data)
        context_data is only provided when status is "needs_more_info"
    """
    # Step 1: Get user credentials (already decrypted from user_creds.json)
    is_valid, error_msg, credentials = get_user_credentials(first_name, last_name)
    if not is_valid:
        return pd.DataFrame(), "", error_msg, None, None
    
    # Step 2: Get API key (credentials already validated in settings)
    provider_key_map = {
        "OpenAI": "openai_key",
        "Anthropic": "anthropic_key",
        "OpenRouter": "openrouter_key"
    }
    
    api_key_name = provider_key_map.get(provider)
    if not api_key_name:
        return pd.DataFrame(), "", f"Invalid provider: {provider}", None, None
    
    api_key = credentials.get(api_key_name, "")
    if not api_key:
        return pd.DataFrame(), "", f"No {provider} API key found. Please add it in settings.", None, None
    
    # Step 3: Extract Jira ticket ID and check cache first
    ticket_id = extract_ticket_id(feature_text)
    if not ticket_id:
        return pd.DataFrame(), "", "No Jira ticket ID found in feature text. Please include ticket ID (e.g., PAN-16083, AI/ML-16084, AIMLENG-3911, etc.).", None, None
    
    # Check if test cases are already cached for this ticket
    cached_data = load_cached_test_cases(ticket_id)
    if cached_data:
        # Convert cached test cases to the expected format
        cached_test_cases = cached_data.get("test_cases", [])
        if cached_test_cases:
            # Format cached test cases
            formatted_test_cases = []
            rows = []
            
            for tc in cached_test_cases:
                tc_id = tc.get("id", "")
                tc_title = tc.get("title", "Untitled")
                steps = tc.get("steps", [])
                expected_results = tc.get("expected_results", [])
                
                # Format steps with expected results
                formatted_steps = []
                for i, step in enumerate(steps):
                    formatted_steps.append({
                        "Step": step,
                        "Expected Result": expected_results[i] if i < len(expected_results) else ""
                    })
                    rows.append({
                        "Step": step,
                        "Expected Result": expected_results[i] if i < len(expected_results) else ""
                    })
                
                formatted_test_cases.append({
                    "id": tc_id,
                    "title": tc_title,
                    "steps": formatted_steps
                })
            
            df = pd.DataFrame(rows)
            raw_output = f"Cached test cases for {ticket_id}"
            return df, raw_output, None, formatted_test_cases, None
    
    jira_email = credentials.get("jira_email", "")
    jira_token = credentials.get("jira_token", "")
    jira_url = credentials.get("jira_url", "https://welocalizedev.atlassian.net/")
    
    # Get ticket data (credentials already validated in settings)
    is_valid_ticket, ticket_error, ticket_data = get_jira_ticket(
        ticket_id, jira_email, jira_token, jira_url
    )
    
    if not is_valid_ticket:
        return pd.DataFrame(), "", ticket_error, None, None
    
    # Step 4: Set API key in environment for CrewAI
    env_var_map = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY"
    }
    os.environ[env_var_map[provider]] = api_key
    
    # Step 5: Extract Jira ticket information from ticket data
    try:
        fields = ticket_data.get("fields", {})
        jira_key = ticket_data.get("key", ticket_id)
        jira_project = fields.get("project", {}).get("name", "Unknown Project")
        jira_summary = fields.get("summary", "")
        jira_description = fields.get("description", "")
        
        # If description is None or empty, use summary as fallback
        if not jira_description:
            jira_description = jira_summary or feature_text
    except Exception as e:
        return pd.DataFrame(), "", f"Error extracting Jira ticket information: {str(e)}", None, None
    
    # Step 6: Generate test cases using CrewAI (validator agent will analyze ticket)
    try:
        from crewai import Crew, Process
        from features.testCaseGeneration import (
            create_test_case_validator_agent,
            create_test_case_generator_agent,
            create_validate_jira_story_task,
            create_generate_test_cases_task
        )
        
        # Create validator agent and task
        validator_agent = create_test_case_validator_agent(model, provider)
        validation_task = create_validate_jira_story_task(
            agent=validator_agent,
            jira_key=jira_key,
            jira_project=jira_project,
            jira_summary=jira_summary,
            jira_description=jira_description
        )
        
        # Create generator agent and task
        generator_agent = create_test_case_generator_agent(model, provider)
        generation_task = create_generate_test_cases_task(
            agent=generator_agent,
            validation_task=validation_task
        )
        
        # Run crew with both tasks
        crew = Crew(
            agents=[validator_agent, generator_agent],
            tasks=[validation_task, generation_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        raw = str(result)
        
        # Parse JSON response from generation task
        try:
            # Try to extract JSON from the result
            # CrewAI result structure: result.tasks_output contains list of task outputs
            generation_output = raw
            
            if hasattr(result, 'tasks_output') and result.tasks_output:
                # Get the last task output (generation task)
                generation_output = result.tasks_output[-1]
            elif hasattr(result, 'raw') and result.raw:
                generation_output = result.raw
            elif hasattr(result, 'output'):
                generation_output = result.output
            
            # Convert to string if not already
            if not isinstance(generation_output, str):
                generation_output = str(generation_output)
            
            # Extract JSON from string (handle nested JSON)
            # Find the first complete JSON object by counting braces
            start = generation_output.find('{')
            if start != -1:
                brace_count = 0
                end = start
                in_string = False
                escape_next = False
                
                for i, char in enumerate(generation_output[start:], start):
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                
                if brace_count == 0:
                    json_str = generation_output[start:end]
                    data = json.loads(json_str)
                else:
                    # Fallback: try parsing whole string
                    data = json.loads(generation_output)
            else:
                # No JSON object found, try parsing whole string
                data = json.loads(generation_output)
            
            # Check status
            status = data.get("status", "")
            
            if status == "invalid":
                return pd.DataFrame(), "", f"Jira ticket is not suitable for test case generation: {data.get('notes', 'Invalid ticket')}", None, None
            
            if status == "needs_more_info":
                questions = data.get("questions", [])
                questions_text = "\n".join([f"- {q}" for q in questions]) if questions else "No specific questions provided."
                # Save context for later use with additional information
                context_data = {
                    "ticket_id": ticket_id,
                    "jira_key": jira_key,
                    "jira_project": jira_project,
                    "jira_summary": jira_summary,
                    "jira_description": jira_description,
                    "validation_result": data,
                    "questions": questions
                }
                # Return special error code to indicate needs_more_info with context
                return pd.DataFrame(), "", f"NEEDS_MORE_INFO:{data.get('notes', '')}\n\nPlease provide:\n{questions_text}", None, context_data
            
            if status == "ready":
                test_cases = data.get("test_cases", [])
                if not test_cases:
                    return pd.DataFrame(), "", "No test cases generated despite ready status.", None, None
                
                # Return test cases as list of dicts (not DataFrame)
                # This allows proper display of multiple test cases
                formatted_test_cases = []
                for tc in test_cases:
                    tc_id = tc.get("id", "")
                    tc_title = tc.get("title", "Untitled")
                    steps = tc.get("steps", [])
                    expected_results = tc.get("expected_results", [])
                    
                    # Format steps with expected results
                    formatted_steps = []
                    for i, step in enumerate(steps):
                        formatted_steps.append({
                            "Step": step,
                            "Expected Result": expected_results[i] if i < len(expected_results) else ""
                        })
                    
                    formatted_test_cases.append({
                        "id": tc_id,
                        "title": tc_title,
                        "steps": formatted_steps
                    })
                
                # Create a single DataFrame for backward compatibility (all steps combined)
                rows = []
                for tc in formatted_test_cases:
                    for step_row in tc["steps"]:
                        rows.append(step_row)
                df = pd.DataFrame(rows)
                
                # Save test cases to cache before returning
                cache_data = {
                    "status": "ready",
                    "notes": data.get("notes", ""),
                    "test_cases": test_cases  # Original test cases from LLM
                }
                save_test_cases_to_cache(ticket_id, cache_data)
                
                # Return both DataFrame and formatted test cases list
                return df, raw, None, formatted_test_cases, None
            else:
                return pd.DataFrame(), "", f"Unknown status: {status}. Raw output: {raw}", None, None
                
        except json.JSONDecodeError as e:
            # Fallback: try to extract JSON array (old format compatibility)
            m = re.search(r"(\[\s*\{.*?\}\s*\])", raw, re.DOTALL)
            if m:
                data = json.loads(m.group(1))
                df = pd.DataFrame([{
                    "Step": item.get("step", ""),
                    "Expected Result": item.get("expected_result", "")
                } for item in data])
                # Convert to formatted test cases format
                formatted_test_cases = [{
                    "id": "TC-01",
                    "title": "Test Case 1",
                    "steps": df.to_dict('records')
                }]
                
                # Save to cache (fallback format)
                cache_data = {
                    "status": "ready",
                    "notes": "Test cases generated (fallback format)",
                    "test_cases": [{
                        "id": "TC-01",
                        "title": "Test Case 1",
                        "steps": [item.get("step", "") for item in data],
                        "expected_results": [item.get("expected_result", "") for item in data]
                    }]
                }
                save_test_cases_to_cache(ticket_id, cache_data)
                
                return df, raw, None, formatted_test_cases, None
            else:
                return pd.DataFrame(), "", f"Model did not return valid JSON. Error: {str(e)}\nRaw output:\n{raw}", None, None
        
    except Exception as e:
        return pd.DataFrame(), "", f"Error generating test cases: {str(e)}", None, None


# ============================================================================
# UI LOGIC FUNCTIONS
# ============================================================================

def prepare_regeneration_prompt(
    original_feature_text: str,
    current_test_cases: list,
    feedback_text: str
) -> str:
    """
    Prepare enhanced prompt for regeneration with feedback.
    
    Args:
        original_feature_text: Original feature/story description
        current_test_cases: List of current test cases with title and steps
        feedback_text: User feedback for regeneration
        
    Returns:
        Enhanced prompt string
    """
    # Format current test cases
    current_test_cases_str = "\n\n".join([
        f"Test Case: {tc.get('title', 'Untitled')}\n" + 
        "\n".join([
            f"Step: {step.get('Step', '')}, Expected: {step.get('Expected Result', '')}" 
            for step in tc.get('steps', [])
        ])
        for tc in current_test_cases
    ])
    
    # Create enhanced prompt
    enhanced_prompt = f"""Original Feature:
{original_feature_text}

Current Test Cases:
{current_test_cases_str}

User Feedback:
{feedback_text}

Please regenerate the test cases incorporating the user's feedback."""
    
    return enhanced_prompt


def handle_generate_test_cases(
    feature_text: str,
    first_name: str,
    last_name: str,
    provider: str,
    model: str
) -> dict:
    """
    Handle test case generation workflow.
    
    Args:
        feature_text: Feature/story description
        first_name: User's first name
        last_name: User's last name
        provider: LLM provider
        model: Model name
        
    Returns:
        Dict with keys: success, error, df, raw, test_cases
    """
    # Validate input
    if not feature_text or not feature_text.strip():
        return {
            "success": False,
            "error": "Paste a jira feature/story first.",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": []
        }
    
    # Validate user identification
    if not first_name or not last_name:
        return {
            "success": False,
            "error": "User not identified. Please refresh the page.",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": []
        }
    
    # Generate test cases
    try:
        df, raw, error, formatted_test_cases, context_data = generate_test_cases(
            feature_text=feature_text,
            first_name=first_name,
            last_name=last_name,
            provider=provider,
            model=model
        )
        
        # Check if needs_more_info
        if error and error.startswith("NEEDS_MORE_INFO:"):
            return {
                "success": False,
                "error": error.replace("NEEDS_MORE_INFO:", ""),
                "df": df,
                "raw": raw,
                "test_cases": [],
                "needs_more_info": True,
                "context_data": context_data
            }
        
        if error:
            return {
                "success": False,
                "error": error,
                "df": df,
                "raw": raw,
                "test_cases": [],
                "needs_more_info": False,
                "context_data": None
            }
        
        if df.empty:
            return {
                "success": False,
                "error": "No test cases generated.",
                "df": df,
                "raw": raw,
                "test_cases": []
            }
        
        # Use formatted test cases if available, otherwise fallback to single test case
        if formatted_test_cases:
            test_cases = formatted_test_cases
        else:
            # Fallback: create single test case from DataFrame
            test_cases = [
                {
                    "id": "TC-01",
                    "title": "Test Case 1",
                    "steps": df.to_dict('records')
                }
            ]
        
        return {
            "success": True,
            "error": None,
            "df": df,
            "raw": raw,
            "test_cases": test_cases,
            "needs_more_info": False,
            "context_data": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": [],
            "needs_more_info": False,
            "context_data": None
        }


def generate_test_cases_with_additional_info(
    context_data: dict,
    additional_info: str,
    first_name: str,
    last_name: str,
    provider: str,
    model: str
) -> Tuple[pd.DataFrame, str, Optional[str], Optional[list], Optional[dict]]:
    """
    Generate test cases with additional information provided by user.
    
    Args:
        context_data: Saved context from previous validation (ticket info, questions, etc.)
        additional_info: Additional information provided by user (backstory, epic, etc.)
        first_name: User's first name
        last_name: User's last name
        provider: LLM provider
        model: Model name
        
    Returns:
        Tuple of (DataFrame, raw_output, error_message, formatted_test_cases_list, context_data)
    """
    # Combine original ticket info with additional information
    jira_key = context_data.get("jira_key", "")
    jira_project = context_data.get("jira_project", "")
    jira_summary = context_data.get("jira_summary", "")
    jira_description = context_data.get("jira_description", "")
    
    # Enhanced description with additional info
    enhanced_description = f"""{jira_description}

ADDITIONAL INFORMATION PROVIDED BY USER:
{additional_info}
"""
    
    # Get user credentials
    is_valid, error_msg, credentials = get_user_credentials(first_name, last_name)
    if not is_valid:
        return pd.DataFrame(), "", error_msg, None, None
    
    # Get API key
    provider_key_map = {
        "OpenAI": "openai_key",
        "Anthropic": "anthropic_key",
        "OpenRouter": "openrouter_key"
    }
    
    api_key_name = provider_key_map.get(provider)
    if not api_key_name:
        return pd.DataFrame(), "", f"Invalid provider: {provider}", None, None
    
    api_key = credentials.get(api_key_name, "")
    if not api_key:
        return pd.DataFrame(), "", f"No {provider} API key found. Please add it in settings.", None, None
    
    # Set API key in environment for CrewAI
    env_var_map = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY"
    }
    os.environ[env_var_map[provider]] = api_key
    
    # Generate test cases using CrewAI with enhanced description
    try:
        from crewai import Crew, Process
        from features.testCaseGeneration import (
            create_test_case_validator_agent,
            create_test_case_generator_agent,
            create_validate_jira_story_task,
            create_generate_test_cases_task
        )
        
        # Create validator agent and task with enhanced description
        validator_agent = create_test_case_validator_agent(model, provider)
        validation_task = create_validate_jira_story_task(
            agent=validator_agent,
            jira_key=jira_key,
            jira_project=jira_project,
            jira_summary=jira_summary,
            jira_description=enhanced_description
        )
        
        # Create generator agent and task
        generator_agent = create_test_case_generator_agent(model, provider)
        generation_task = create_generate_test_cases_task(
            agent=generator_agent,
            validation_task=validation_task
        )
        
        # Run crew with both tasks
        crew = Crew(
            agents=[validator_agent, generator_agent],
            tasks=[validation_task, generation_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        raw = str(result)
        
        # Parse JSON response (same logic as generate_test_cases)
        try:
            generation_output = raw
            
            if hasattr(result, 'tasks_output') and result.tasks_output:
                generation_output = result.tasks_output[-1]
            elif hasattr(result, 'raw') and result.raw:
                generation_output = result.raw
            elif hasattr(result, 'output'):
                generation_output = result.output
            
            if not isinstance(generation_output, str):
                generation_output = str(generation_output)
            
            # Extract JSON
            start = generation_output.find('{')
            if start != -1:
                brace_count = 0
                end = start
                in_string = False
                escape_next = False
                
                for i, char in enumerate(generation_output[start:], start):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                
                if brace_count == 0:
                    json_str = generation_output[start:end]
                    data = json.loads(json_str)
                else:
                    data = json.loads(generation_output)
            else:
                data = json.loads(generation_output)
            
            status = data.get("status", "")
            
            if status == "invalid":
                return pd.DataFrame(), "", f"Jira ticket is not suitable for test case generation: {data.get('notes', 'Invalid ticket')}", None, None
            
            if status == "needs_more_info":
                questions = data.get("questions", [])
                questions_text = "\n".join([f"- {q}" for q in questions]) if questions else "No specific questions provided."
                # Update context with new validation result
                context_data["validation_result"] = data
                context_data["questions"] = questions
                return pd.DataFrame(), "", f"NEEDS_MORE_INFO:{data.get('notes', '')}\n\nPlease provide:\n{questions_text}", None, context_data
            
            if status == "ready":
                test_cases = data.get("test_cases", [])
                if not test_cases:
                    return pd.DataFrame(), "", "No test cases generated despite ready status.", None, None
                
                # Format test cases
                formatted_test_cases = []
                rows = []
                for tc in test_cases:
                    tc_id = tc.get("id", "")
                    tc_title = tc.get("title", "Untitled")
                    steps = tc.get("steps", [])
                    expected_results = tc.get("expected_results", [])
                    
                    formatted_steps = []
                    for i, step in enumerate(steps):
                        formatted_steps.append({
                            "Step": step,
                            "Expected Result": expected_results[i] if i < len(expected_results) else ""
                        })
                        rows.append({
                            "Step": step,
                            "Expected Result": expected_results[i] if i < len(expected_results) else ""
                        })
                    
                    formatted_test_cases.append({
                        "id": tc_id,
                        "title": tc_title,
                        "steps": formatted_steps
                    })
                
                df = pd.DataFrame(rows)
                
                # Save to cache
                ticket_id = context_data.get("ticket_id", "")
                if ticket_id:
                    cache_data = {
                        "status": "ready",
                        "notes": data.get("notes", ""),
                        "test_cases": test_cases
                    }
                    save_test_cases_to_cache(ticket_id, cache_data)
                
                return df, raw, None, formatted_test_cases, None
            else:
                return pd.DataFrame(), "", f"Unknown status: {status}. Raw output: {raw}", None, None
                
        except json.JSONDecodeError as e:
            return pd.DataFrame(), "", f"Model did not return valid JSON. Error: {str(e)}\nRaw output:\n{raw}", None, None
        
    except Exception as e:
        return pd.DataFrame(), "", f"Error generating test cases: {str(e)}", None, None


def regenerate_test_cases_with_feedback(
    original_feature_text: str,
    current_test_cases: list,
    feedback_text: str,
    first_name: str,
    last_name: str,
    provider: str,
    model: str,
    ticket_id: Optional[str] = None
) -> Tuple[pd.DataFrame, str, Optional[str], Optional[list], Optional[dict]]:
    """
    Regenerate test cases based on user feedback about existing test cases.
    This function uses the test case generator agent directly with the current test cases and feedback.
    
    Args:
        original_feature_text: Original feature/story description
        current_test_cases: List of current test cases with title and steps
        feedback_text: User feedback on what to change
        first_name: User's first name
        last_name: User's last name
        provider: LLM provider
        model: Model name
        
    Returns:
        Tuple of (DataFrame, raw_output, error_message, formatted_test_cases_list, context_data)
    """
    # Get user credentials
    is_valid, error_msg, credentials = get_user_credentials(first_name, last_name)
    if not is_valid:
        return pd.DataFrame(), "", error_msg, None, None
    
    # Get API key
    provider_key_map = {
        "OpenAI": "openai_key",
        "Anthropic": "anthropic_key",
        "OpenRouter": "openrouter_key"
    }
    
    api_key_name = provider_key_map.get(provider)
    if not api_key_name:
        return pd.DataFrame(), "", f"Invalid provider: {provider}", None, None
    
    api_key = credentials.get(api_key_name, "")
    if not api_key:
        return pd.DataFrame(), "", f"No {provider} API key found. Please add it in settings.", None, None
    
    # Set API key in environment for CrewAI
    env_var_map = {
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY"
    }
    os.environ[env_var_map[provider]] = api_key
    
    # Format current test cases for the prompt
    current_test_cases_str = "\n\n".join([
        f"Test Case {idx + 1} ({tc.get('id', f'TC-{idx+1:02d}')}): {tc.get('title', 'Untitled')}\n" + 
        "\n".join([
            f"  Step {step_idx + 1}: {step.get('Step', '')}\n  Expected: {step.get('Expected Result', '')}" 
            for step_idx, step in enumerate(tc.get('steps', []))
        ])
        for idx, tc in enumerate(current_test_cases)
    ])
    
    # Create regeneration prompt with better structure
    regeneration_prompt = f"""You are regenerating test cases based on user feedback about existing test cases.

ORIGINAL FEATURE/STORY:
{original_feature_text}

CURRENT GENERATED TEST CASES (that need to be updated):
{current_test_cases_str}

USER FEEDBACK/REQUEST:
{feedback_text}

INSTRUCTIONS:
1. Analyze the user's feedback carefully to understand what changes they want
2. Review the current test cases to see what needs to be modified
3. Generate updated test cases that:
   - Address the user's specific feedback
   - Maintain coverage of the original feature/story
   - Keep test cases that don't need changes (unless feedback says otherwise)
   - Add new test cases if requested
   - Remove or modify test cases as per feedback
   - Ensure all test cases have clear steps and expected results

4. The number of test cases can increase, decrease, or stay the same based on the feedback
5. Test case IDs should be sequential (TC-01, TC-02, etc.)

Return ONLY a valid JSON object with this exact structure (no markdown, no code fences):
{{
  "status": "ready",
  "notes": "Brief explanation of what was changed based on the user's feedback",
  "test_cases": [
    {{
      "id": "TC-01",
      "title": "Clear, descriptive test case title",
      "steps": [
        "1. First step description",
        "2. Second step description",
        ...
      ],
      "expected_results": [
        "Expected outcome for step 1",
        "Expected outcome for step 2",
        ...
      ]
    }},
    {{
      "id": "TC-02",
      "title": "Another test case title",
      "steps": [...],
      "expected_results": [...]
    }}
  ]
}}

IMPORTANT: 
- Output JSON ONLY, no markdown formatting
- Each step should be a numbered string (e.g., "1. ...", "2. ...")
- Steps and expected_results arrays must have the same length
- Generate 6-15 test cases depending on the feedback and original feature complexity
"""
    
    # Generate test cases using CrewAI with regeneration prompt
    try:
        from crewai import Crew, Process
        from features.testCaseGeneration import (
            create_test_case_generator_agent,
            create_generate_test_cases_task
        )
        
        # Use only the generator agent for regeneration (no validation needed)
        generator_agent = create_test_case_generator_agent(model, provider)
        
        # Create a custom task for regeneration
        from crewai import Task
        regeneration_task = Task(
            description=regeneration_prompt,
            expected_output="A strictly valid JSON object with status='ready', notes, and test_cases array. Each test case must have id, title, steps, and expected_results.",
            agent=generator_agent
        )
        
        # Run crew with regeneration task
        crew = Crew(
            agents=[generator_agent],
            tasks=[regeneration_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        raw = str(result)
        
        # Parse JSON response
        try:
            generation_output = raw
            
            if hasattr(result, 'tasks_output') and result.tasks_output:
                generation_output = result.tasks_output[-1]
            elif hasattr(result, 'raw') and result.raw:
                generation_output = result.raw
            elif hasattr(result, 'output'):
                generation_output = result.output
            
            if not isinstance(generation_output, str):
                generation_output = str(generation_output)
            
            # Extract JSON
            start = generation_output.find('{')
            if start != -1:
                brace_count = 0
                end = start
                in_string = False
                escape_next = False
                
                for i, char in enumerate(generation_output[start:], start):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                
                if brace_count == 0:
                    json_str = generation_output[start:end]
                    data = json.loads(json_str)
                else:
                    data = json.loads(generation_output)
            else:
                data = json.loads(generation_output)
            
            status = data.get("status", "")
            
            if status == "ready":
                test_cases = data.get("test_cases", [])
                if not test_cases:
                    return pd.DataFrame(), "", "No test cases generated.", None, None
                
                # Format test cases
                formatted_test_cases = []
                rows = []
                for tc in test_cases:
                    tc_id = tc.get("id", "")
                    tc_title = tc.get("title", "Untitled")
                    steps = tc.get("steps", [])
                    expected_results = tc.get("expected_results", [])
                    
                    formatted_steps = []
                    for i, step in enumerate(steps):
                        formatted_steps.append({
                            "Step": step,
                            "Expected Result": expected_results[i] if i < len(expected_results) else ""
                        })
                        rows.append({
                            "Step": step,
                            "Expected Result": expected_results[i] if i < len(expected_results) else ""
                        })
                    
                    formatted_test_cases.append({
                        "id": tc_id,
                        "title": tc_title,
                        "steps": formatted_steps
                    })
                
                df = pd.DataFrame(rows)
                
                # Save regenerated test cases to cache
                # Use provided ticket_id or extract from original_feature_text
                cache_ticket_id = ticket_id if ticket_id else extract_ticket_id(original_feature_text)
                if cache_ticket_id:
                    # Convert formatted test cases back to original format for cache
                    cache_test_cases = []
                    for tc in formatted_test_cases:
                        steps = [step.get("Step", "") for step in tc.get("steps", [])]
                        expected_results = [step.get("Expected Result", "") for step in tc.get("steps", [])]
                        cache_test_cases.append({
                            "id": tc.get("id", ""),
                            "title": tc.get("title", ""),
                            "steps": steps,
                            "expected_results": expected_results
                        })
                    
                    cache_data = {
                        "status": "ready",
                        "notes": data.get("notes", "Test cases regenerated based on user feedback"),
                        "test_cases": cache_test_cases
                    }
                    save_test_cases_to_cache(cache_ticket_id, cache_data)
                
                return df, raw, None, formatted_test_cases, None
            else:
                return pd.DataFrame(), "", f"Unexpected status: {status}. Expected 'ready'. Raw output: {raw}", None, None
                
        except json.JSONDecodeError as e:
            return pd.DataFrame(), "", f"Model did not return valid JSON. Error: {str(e)}\nRaw output:\n{raw}", None, None
        
    except Exception as e:
        return pd.DataFrame(), "", f"Error regenerating test cases: {str(e)}", None, None


def handle_regenerate_test_cases(
    original_feature_text: str,
    current_test_cases: list,
    feedback_text: str,
    first_name: str,
    last_name: str,
    provider: str,
    model: str,
    ticket_id: Optional[str] = None
) -> dict:
    """
    Handle test case regeneration workflow with feedback.
    
    Args:
        original_feature_text: Original feature/story description
        current_test_cases: List of current test cases
        feedback_text: User feedback
        first_name: User's first name
        last_name: User's last name
        provider: LLM provider
        model: Model name
        
    Returns:
        Dict with keys: success, error, df, raw, test_cases, needs_more_info, context_data
    """
    # Validate feedback
    if not feedback_text or not feedback_text.strip():
        return {
            "success": False,
            "error": "Please provide feedback on what to change",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": [],
            "needs_more_info": False,
            "context_data": None
        }
    
    # Validate user identification
    if not first_name or not last_name:
        return {
            "success": False,
            "error": "User not identified. Please refresh the page.",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": [],
            "needs_more_info": False,
            "context_data": None
        }
    
    # Validate current test cases exist
    if not current_test_cases or len(current_test_cases) == 0:
        return {
            "success": False,
            "error": "No existing test cases to regenerate. Please generate test cases first.",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": [],
            "needs_more_info": False,
            "context_data": None
        }
    
    # Regenerate test cases with feedback
    try:
        df, raw, error, formatted_test_cases, context_data = regenerate_test_cases_with_feedback(
            original_feature_text=original_feature_text,
            current_test_cases=current_test_cases,
            feedback_text=feedback_text,
            first_name=first_name,
            last_name=last_name,
            provider=provider,
            model=model,
            ticket_id=ticket_id
        )
        
        if error:
            return {
                "success": False,
                "error": error,
                "df": df,
                "raw": raw,
                "test_cases": [],
                "needs_more_info": False,
                "context_data": None
            }
        
        if df.empty:
            return {
                "success": False,
                "error": "No test cases generated.",
                "df": df,
                "raw": raw,
                "test_cases": [],
                "needs_more_info": False,
                "context_data": None
            }
        
        # Use formatted test cases if available, otherwise fallback to single test case
        if formatted_test_cases:
            test_cases = formatted_test_cases
        else:
            # Fallback: create single test case from DataFrame
            test_cases = [
                {
                    "id": "TC-01",
                    "title": "Test Case 1",
                    "steps": df.to_dict('records')
                }
            ]
        
        return {
            "success": True,
            "error": None,
            "df": df,
            "raw": raw,
            "test_cases": test_cases,
            "needs_more_info": False,
            "context_data": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "df": pd.DataFrame(),
            "raw": "",
            "test_cases": [],
            "needs_more_info": False,
            "context_data": None
        }


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_test_cases_to_csv(test_cases: list) -> str:
    """
    Export test cases to CSV format.
    
    Args:
        test_cases: List of test cases with title and steps
        
    Returns:
        CSV string content
    """
    import io
    
    # Create a list of all rows
    rows = []
    for test_case in test_cases:
        title = test_case.get("title", "Untitled")
        steps = test_case.get("steps", [])
        
        for step in steps:
            rows.append({
                "Test Case Title": title,
                "Step": step.get("Step", ""),
                "Expected Result": step.get("Expected Result", "")
            })
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Convert to CSV string
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()


def export_test_cases_to_excel(test_cases: list) -> bytes:
    """
    Export test cases to Excel format.
    
    Args:
        test_cases: List of test cases with title and steps
        
    Returns:
        Excel file as bytes
    """
    import io
    
    # Create Excel writer
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Create a list of all rows
        rows = []
        for test_case in test_cases:
            title = test_case.get("title", "Untitled")
            steps = test_case.get("steps", [])
            
            for step in steps:
                rows.append({
                    "Test Case Title": title,
                    "Step": step.get("Step", ""),
                    "Expected Result": step.get("Expected Result", "")
                })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Write to Excel
        df.to_excel(writer, sheet_name="Test Cases", index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets["Test Cases"]
        from openpyxl.utils import get_column_letter
        
        for idx, col in enumerate(df.columns, start=1):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            column_letter = get_column_letter(idx)
            worksheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    output.seek(0)
    return output.getvalue()


# ============================================================================
# TICKET HISTORY MANAGEMENT
# ============================================================================

def save_ticket_to_history(
    ticket_id: str,
    ticket_summary: str,
    test_cases: list,
    generated_date: Optional[str] = None
) -> dict:
    """
    Save a ticket and its test cases to history.
    
    Args:
        ticket_id: Jira ticket ID (e.g., "PAN-12776")
        ticket_summary: Ticket summary/title
        test_cases: List of test cases
        generated_date: Optional date string (defaults to current timestamp)
        
    Returns:
        Dictionary with ticket history entry
    """
    from datetime import datetime
    
    if not generated_date:
        generated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    history_entry = {
        "ticket_id": ticket_id,
        "ticket_summary": ticket_summary,
        "test_cases": test_cases,
        "generated_date": generated_date,
        "test_case_count": len(test_cases)
    }
    
    return history_entry


def get_ticket_history_entry(ticket_history: list, ticket_id: str) -> Optional[dict]:
    """
    Get a specific ticket entry from history by ticket ID.
    
    Args:
        ticket_history: List of ticket history entries
        ticket_id: Ticket ID to find
        
    Returns:
        History entry dict or None if not found
    """
    for entry in ticket_history:
        if entry.get("ticket_id") == ticket_id:
            return entry
    return None


def update_ticket_in_history(
    ticket_history: list,
    ticket_id: str,
    ticket_summary: str,
    test_cases: list
) -> list:
    """
    Update or add a ticket in history.
    
    Args:
        ticket_history: Current list of ticket history entries
        ticket_id: Ticket ID
        ticket_summary: Ticket summary/title
        test_cases: Updated test cases
        
    Returns:
        Updated ticket history list
    """
    from datetime import datetime
    
    # Check if ticket already exists
    existing_index = None
    for idx, entry in enumerate(ticket_history):
        if entry.get("ticket_id") == ticket_id:
            existing_index = idx
            break
    
    # Create or update entry
    history_entry = {
        "ticket_id": ticket_id,
        "ticket_summary": ticket_summary,
        "test_cases": test_cases,
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "test_case_count": len(test_cases)
    }
    
    if existing_index is not None:
        # Update existing entry
        ticket_history[existing_index] = history_entry
    else:
        # Add new entry
        ticket_history.append(history_entry)
    
    return ticket_history


def clear_ticket_history() -> list:
    """
    Clear all ticket history.
    
    Returns:
        Empty list
    """
    return []


def get_ticket_history_table_data(ticket_history: list) -> pd.DataFrame:
    """
    Convert ticket history to DataFrame for table display.
    
    Args:
        ticket_history: List of ticket history entries
        
    Returns:
        DataFrame with columns: Ticket ID, Summary, Test Cases, Generated Date
    """
    if not ticket_history:
        return pd.DataFrame(columns=["Ticket ID", "Summary", "Test Cases", "Generated Date"])
    
    rows = []
    for entry in ticket_history:
        rows.append({
            "Ticket ID": entry.get("ticket_id", ""),
            "Summary": entry.get("ticket_summary", "")[:50] + "..." if len(entry.get("ticket_summary", "")) > 50 else entry.get("ticket_summary", ""),
            "Test Cases": entry.get("test_case_count", 0),
            "Generated Date": entry.get("generated_date", "")
        })
    
    return pd.DataFrame(rows)
