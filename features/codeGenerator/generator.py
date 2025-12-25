"""
Code Generation Logic
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

# Cache directory for generated code
CODE_CACHE_DIR = "codeGenerated"


def ensure_code_cache_dir():
    """Ensure the code cache directory exists"""
    if not os.path.exists(CODE_CACHE_DIR):
        os.makedirs(CODE_CACHE_DIR, exist_ok=True)


def get_code_cache_file_path(test_case_id: str, ticket_id: str = None) -> str:
    """
    Get the cache file path for generated code.
    
    Args:
        test_case_id: Test case ID (e.g., "TC-01")
        ticket_id: Optional ticket ID (e.g., "PAN-12345")
        
    Returns:
        Path to the cache file
    """
    ensure_code_cache_dir()
    # Sanitize IDs for filename
    safe_test_case_id = test_case_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
    if ticket_id:
        safe_ticket_id = ticket_id.replace("/", "_").replace("\\", "_")
        filename = f"{safe_ticket_id}_{safe_test_case_id}_code.json"
    else:
        filename = f"{safe_test_case_id}_code.json"
    return os.path.join(CODE_CACHE_DIR, filename)


def load_cached_code(test_case_id: str, ticket_id: str = None) -> Optional[Dict]:
    """
    Load cached code for a test case.
    
    Args:
        test_case_id: Test case ID
        ticket_id: Optional ticket ID
        
    Returns:
        Cached code dict or None if not found
    """
    cache_file = get_code_cache_file_path(test_case_id, ticket_id)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            # If file is corrupted, return None to regenerate
            return None
    return None


def save_code_to_cache(
    test_case_id: str,
    test_case_title: str,
    ticket_id: str,
    code_data: Dict,
    formatted_code: Dict
):
    """
    Save generated code to cache file.
    
    Args:
        test_case_id: Test case ID
        test_case_title: Test case title
        ticket_id: Ticket ID
        code_data: Raw code data dict
        formatted_code: Formatted code dict for display
    """
    try:
        ensure_code_cache_dir()
        cache_file = get_code_cache_file_path(test_case_id, ticket_id)
        
        # Prepare data to save
        save_data = {
            "test_case_id": test_case_id,
            "test_case_title": test_case_title,
            "ticket_id": ticket_id,
            "generated_date": datetime.now().isoformat(),
            "code": code_data,
            "formatted": formatted_code
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Log error but don't fail the generation
        print(f"Warning: Could not save code to cache: {e}")


def get_all_cached_codes() -> List[Dict]:
    """
    Get all cached code files.
    
    Returns:
        List of code data dictionaries
    """
    ensure_code_cache_dir()
    codes = []
    
    try:
        for filename in os.listdir(CODE_CACHE_DIR):
            if filename.endswith("_code.json"):
                filepath = os.path.join(CODE_CACHE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code_data = json.load(f)
                        codes.append(code_data)
                except Exception as e:
                    # Skip corrupted files
                    continue
    except Exception as e:
        pass
    
    # Sort by generated date (newest first)
    codes.sort(key=lambda x: x.get("generated_date", ""), reverse=True)
    return codes


def get_code_history_table_data(codes: List[Dict]) -> List[Dict]:
    """
    Format code history for table display.
    
    Args:
        codes: List of code data dictionaries
        
    Returns:
        List of dictionaries formatted for table display
    """
    table_data = []
    for code_data in codes:
        generated_date = code_data.get("generated_date", "")
        if generated_date:
            try:
                dt = datetime.fromisoformat(generated_date)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = generated_date
        else:
            formatted_date = "N/A"
        
        table_data.append({
            "Test Case ID": code_data.get("test_case_id", "N/A"),
            "Title": code_data.get("test_case_title", "N/A"),
            "Ticket ID": code_data.get("ticket_id", "N/A"),
            "Generated Date": formatted_date
        })
    
    return table_data

def generate_playwright_code(
    test_case_id: str,
    test_case_title: str,
    test_steps: List[str],
    expected_results: List[str],
    model: str,
    provider: str = None,
    first_name: str = "",
    last_name: str = "",
    recorded_flow_json: str = None
) -> Dict:
    """
    Generate Playwright code for a test case using CrewAI
    
    Args:
        test_case_id: Test case ID (e.g., "TC-01")
        test_case_title: Test case title
        test_steps: List of test steps
        expected_results: List of expected results
        model: LLM model name
        provider: LLM provider name
        first_name: User first name
        last_name: User last name
    
    Returns:
        Dictionary with success status, generated code, and error message if any
    """
    try:
        from crewai import Crew, Process
        from .agent import create_code_generator_agent
        from .task import create_generate_playwright_code_task
        
        # Create agent
        agent = create_code_generator_agent(model, provider)
        
        # Create task
        task = create_generate_playwright_code_task(
            agent=agent,
            test_case_id=test_case_id,
            test_case_title=test_case_title,
            test_steps=test_steps,
            expected_results=expected_results,
            recorded_flow_json=recorded_flow_json
        )
        
        # Create crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        # Execute
        result = crew.kickoff()
        raw_output = str(result)
        
        # Parse JSON from output
        generated_code = parse_code_json(raw_output)
        
        if not generated_code:
            return {
                "success": False,
                "error": "Failed to parse generated code. Please try again.",
                "raw": raw_output
            }
        
        return {
            "success": True,
            "code": generated_code,
            "raw": raw_output
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error generating code: {str(e)}",
            "raw": ""
        }


def parse_code_json(raw_output: str) -> Optional[Dict]:
    """
    Parse JSON from raw LLM output
    
    Args:
        raw_output: Raw output from LLM
    
    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    try:
        # Try to extract JSON from markdown code blocks
        if "```json" in raw_output:
            start = raw_output.find("```json") + 7
            end = raw_output.find("```", start)
            json_str = raw_output[start:end].strip()
        elif "```" in raw_output:
            start = raw_output.find("```") + 3
            end = raw_output.find("```", start)
            json_str = raw_output[start:end].strip()
            # Remove language identifier if present
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
        else:
            # Try to find JSON object directly
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_output[start:end]
            else:
                json_str = raw_output
        
        # Parse JSON
        parsed = json.loads(json_str)
        
        # Validate structure
        required_keys = ["locators", "reusable_functions", "test_functions", "cursor_prompt"]
        if all(key in parsed for key in required_keys):
            return parsed
        
        return None
        
    except json.JSONDecodeError:
        # Try to fix common JSON issues
        try:
            # Remove trailing commas
            json_str = json_str.replace(",\n}", "\n}").replace(",\n]", "\n]")
            parsed = json.loads(json_str)
            required_keys = ["locators", "reusable_functions", "test_functions", "cursor_prompt"]
            if all(key in parsed for key in required_keys):
                return parsed
        except:
            pass
        
        return None
    except Exception as e:
        return None


def format_code_for_display(code_dict: Dict) -> Dict[str, str]:
    """
    Format generated code for display in UI
    
    Args:
        code_dict: Dictionary with generated code
    
    Returns:
        Dictionary with formatted code strings for each section
    """
    return {
        "locators_python": code_dict.get("locators", {}).get("python", ""),
        "locators_javascript": code_dict.get("locators", {}).get("javascript", ""),
        "reusable_functions_python": code_dict.get("reusable_functions", {}).get("python", ""),
        "reusable_functions_javascript": code_dict.get("reusable_functions", {}).get("javascript", ""),
        "test_functions_python": code_dict.get("test_functions", {}).get("python", ""),
        "test_functions_javascript": code_dict.get("test_functions", {}).get("javascript", ""),
        "cursor_prompt": code_dict.get("cursor_prompt", "")
    }


def handle_generate_code(
    test_case_id: str,
    test_case_title: str,
    test_steps: List[str],
    expected_results: List[str],
    provider: str,
    model: str,
    first_name: str = "",
    last_name: str = "",
    ticket_id: str = None,
    recorded_flow_json: str = None
) -> Dict:
    """
    Handle code generation request
    
    Args:
        test_case_id: Test case ID
        test_case_title: Test case title
        test_steps: List of test steps
        expected_results: List of expected results
        provider: LLM provider
        model: LLM model
        first_name: User first name
        last_name: User last name
        ticket_id: Optional ticket ID for caching
    
    Returns:
        Dictionary with success status and generated code or error
    """
    # Validate inputs
    if not test_case_id or not test_case_title:
        return {
            "success": False,
            "error": "Test case ID and title are required."
        }
    
    if not test_steps or len(test_steps) == 0:
        return {
            "success": False,
            "error": "Test steps are required to generate code."
        }
    
    # Check cache first
    cached_code = load_cached_code(test_case_id, ticket_id)
    if cached_code:
        return {
            "success": True,
            "code": cached_code.get("code", {}),
            "formatted": cached_code.get("formatted", {}),
            "cached": True
        }
    
    # Generate code
    result = generate_playwright_code(
        test_case_id=test_case_id,
        test_case_title=test_case_title,
        test_steps=test_steps,
        expected_results=expected_results,
        model=model,
        provider=provider,
        first_name=first_name,
        last_name=last_name,
        recorded_flow_json=recorded_flow_json
    )
    
    if result["success"]:
        # Format code for display
        formatted = format_code_for_display(result["code"])
        result["formatted"] = formatted
        
        # Save to cache
        if ticket_id:
            save_code_to_cache(
                test_case_id=test_case_id,
                test_case_title=test_case_title,
                ticket_id=ticket_id,
                code_data=result["code"],
                formatted_code=formatted
            )
    
    return result

