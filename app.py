# ============================================================================
# IMPORTS
# ============================================================================
# Standard library imports
import os
import json
import time
from datetime import datetime

# Third-party imports
import pandas as pd
import streamlit as st

# Local imports
from utils import (
    validate_openai_key, 
    validate_anthropic_key, 
    validate_openrouter_key,
    validate_jira_credentials
)
from auth_store import (
    save_user_credentials,
    load_user_credentials,
    user_exists
)

# NOTE: CrewAI imports are done inside functions (lazy loading) to avoid
# Python 3.14 compatibility issues with Pydantic v1. Do not move these to top.

# ============================================================================
# CONFIGURATION
# ============================================================================
# Page configuration
st.set_page_config(page_title="QA Assist", layout="wide")

# ============================================================================
# CONSTANTS
# ============================================================================
PROVIDERS = {
    "OpenAI": {"env_var": "OPENAI_API_KEY", "models": ["gpt-4o", "gpt-4o-mini"]},
    "Anthropic": {"env_var": "ANTHROPIC_API_KEY", "models": ["anthropic/claude-3-5-sonnet-latest"]},
    "OpenRouter": {"env_var": "OPENROUTER_API_KEY", "models": ["openrouter/openai/gpt-4o", "openrouter/openai/gpt-4o-mini"]},
}

# ============================================================================
# HELPER FUNCTIONS - USER AUTHENTICATION
# ============================================================================

def initialize_user_session():
    """Initialize user session - ask for nickname (returning user) or register (new user)"""
    from auth_store import get_user_by_nickname, nickname_exists, user_exists, save_user_credentials
    
    if "user_identified" not in st.session_state:
        st.session_state.user_identified = False
        st.session_state.first_name = ""
        st.session_state.last_name = ""
        st.session_state.user_email = ""
        st.session_state.registration_mode = None  # None, "login", or "register"
    
    if not st.session_state.user_identified:
        # Check if we're in registration mode
        if st.session_state.get("registration_mode") == "register":
            # Registration form for new users
            st.info("👤 Register as a new user")
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name", key="reg_first_name", placeholder="John")
            with col2:
                last_name = st.text_input("Last Name", key="reg_last_name", placeholder="Doe")
            
            nickname = st.text_input(
                "Nickname (3 characters)", 
                key="reg_nickname", 
                placeholder="ABC",
                max_chars=3,
                help="Choose a unique 3-character nickname for quick login"
            )
            
            if nickname:
                nickname = nickname.upper()[:3]  # Normalize to uppercase
                if len(nickname) < 3:
                    st.warning("⚠️ Nickname must be exactly 3 characters")
                elif nickname_exists(nickname):
                    st.error(f"❌ Nickname '{nickname}' is already taken. Please choose another.")
                else:
                    if first_name and last_name and len(nickname) == 3:
                        if st.button("Register & Continue", type="primary"):
                            # Save user with nickname
                            save_user_credentials(
                                first_name.strip(),
                                last_name.strip(),
                                {},  # Empty credentials for new user
                                nickname=nickname
                            )
                            
                            st.session_state.first_name = first_name.strip()
                            st.session_state.last_name = last_name.strip()
                            st.session_state.user_email = f"{first_name.lower()}.{last_name.lower()}@welocalize.com"
                            st.session_state.user_identified = True
                            st.session_state.registration_mode = None
                            
                            # Initialize empty credentials
                            st.session_state.openai_key = ""
                            st.session_state.anthropic_key = ""
                            st.session_state.openrouter_key = ""
                            st.session_state.jira_email = st.session_state.user_email
                            st.session_state.jira_token = ""
                            st.session_state.jira_url = "https://welocalizedev.atlassian.net/"
                            
                            st.success(f"✅ Registered successfully! Your nickname is: {nickname}")
                            st.rerun()
            
            if st.button("← Back to Login"):
                st.session_state.registration_mode = None
                st.rerun()
            
            return False
        else:
            # Redesigned Login UI
            # Top row: Logo and Title
            st.markdown("""
                <div style="text-align: center; margin-bottom: 30px;">
                    <h3>🔧 QA Assist Test Case Generator and Playwright Code Generator</h3>
                </div>
            """, unsafe_allow_html=True)
            
            # Initialize saved nickname from session state (set by JavaScript on page load)
            saved_nickname = st.session_state.get("saved_nickname_from_browser", "")
            
            # Second row: Nickname field, Remember me checkbox, Login button (smaller)
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                nickname = st.text_input(
                    "Nickname", 
                    key="login_nickname", 
                    placeholder="ABC",
                    value=saved_nickname,
                    max_chars=3,
                    help="Enter your 3-character nickname",
                    label_visibility="visible"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # Align checkbox with input
                remember_me = st.checkbox("Remember me", key="remember_me", value=bool(saved_nickname))
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)  # Align button with input
                # Smaller login button
                login_clicked = st.button("Login", type="primary", use_container_width=False)
            
            # Third row: Register link on the right (small)
            col_left, col_right = st.columns([4, 1])
            with col_right:
                st.markdown("<p style='margin-top: 5px; margin-bottom: 0;'>", unsafe_allow_html=True)
                if st.button("New User? Register", type="secondary", use_container_width=False, key="register_small"):
                    st.session_state.registration_mode = "register"
                    st.rerun()
                st.markdown("</p>", unsafe_allow_html=True)
            
            # Handle login logic
            if login_clicked and nickname:
                nickname = nickname.upper()[:3]  # Normalize to uppercase
                if len(nickname) == 3:
                    first_name, last_name = get_user_by_nickname(nickname)
                    
                    if first_name and last_name:
                        # Save nickname to browser localStorage if "Remember me" is checked
                        if remember_me:
                            st.session_state.saved_nickname_from_browser = nickname
                            # Use JavaScript to save to localStorage
                            st.markdown(
                                f"""
                                <script>
                                    if (typeof(Storage) !== "undefined") {{
                                        localStorage.setItem('qa_assist_nickname', '{nickname}');
                                    }}
                                </script>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            # Clear saved nickname
                            if "saved_nickname_from_browser" in st.session_state:
                                del st.session_state.saved_nickname_from_browser
                            st.markdown(
                                """
                                <script>
                                    if (typeof(Storage) !== "undefined") {
                                        localStorage.removeItem('qa_assist_nickname');
                                    }
                                </script>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        st.session_state.first_name = first_name
                        st.session_state.last_name = last_name
                        st.session_state.user_email = f"{first_name.lower()}.{last_name.lower()}@welocalize.com"
                        st.session_state.user_identified = True
                        
                        # Load existing credentials
                        existing_creds = load_user_credentials(first_name, last_name)
                        if existing_creds:
                            st.session_state.openai_key = existing_creds.get("openai_key", "")
                            st.session_state.anthropic_key = existing_creds.get("anthropic_key", "")
                            st.session_state.openrouter_key = existing_creds.get("openrouter_key", "")
                            st.session_state.jira_email = existing_creds.get("jira_email", st.session_state.user_email)
                            st.session_state.jira_token = existing_creds.get("jira_token", "")
                            st.session_state.jira_url = existing_creds.get("jira_url", "https://welocalizedev.atlassian.net/")
                        else:
                            # Initialize empty credentials
                            st.session_state.openai_key = ""
                            st.session_state.anthropic_key = ""
                            st.session_state.openrouter_key = ""
                            st.session_state.jira_email = st.session_state.user_email
                            st.session_state.jira_token = ""
                            st.session_state.jira_url = "https://welocalizedev.atlassian.net/"
                        
                        st.rerun()
                    else:
                        st.warning(f"⚠️ Nickname '{nickname}' not found")
                else:
                    st.warning("⚠️ Nickname must be exactly 3 characters")
            
            # Load saved nickname from localStorage on page load using JavaScript
            # This script runs once to populate the input field
            st.markdown(
                """
                <script>
                    (function() {
                        if (typeof(Storage) !== "undefined") {
                            const savedNickname = localStorage.getItem('qa_assist_nickname');
                            if (savedNickname) {
                                // Wait for Streamlit to render, then set the input value
                                setTimeout(function() {
                                    const frame = window.parent.document.querySelector('iframe[title*="streamlit"]');
                                    if (frame && frame.contentWindow) {
                                        const inputs = frame.contentWindow.document.querySelectorAll('input[placeholder="ABC"]');
                                        if (inputs.length > 0) {
                                            inputs[0].value = savedNickname;
                                            inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                            inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                        }
                                    }
                                    // Also try direct parent document
                                    const directInputs = window.parent.document.querySelectorAll('input[placeholder="ABC"]');
                                    if (directInputs.length > 0) {
                                        directInputs[0].value = savedNickname;
                                        directInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                        directInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    }
                                }, 500);
                            }
                        }
                    })();
                </script>
                """,
                unsafe_allow_html=True
            )
            
            return False
    
    return True

# ============================================================================
# USER IDENTIFICATION
# ============================================================================
# Initialize user session - must be done before any other UI
if not initialize_user_session():
    st.stop()  # Stop execution if user not identified

# ============================================================================
# IMPORTS - TEST CASE GENERATION
# ============================================================================
# Import test case generator functions (all logic separated)
from features.testCaseGeneration import (
    handle_generate_test_cases,
    handle_regenerate_test_cases,
    export_test_cases_to_csv,
    export_test_cases_to_excel,
    save_ticket_to_history,
    get_ticket_history_entry,
    update_ticket_in_history,
    clear_ticket_history,
    get_ticket_history_table_data
)

# ============================================================================
# IMPORTS - CODE GENERATION
# ============================================================================
# Import code generator functions
from features.codeGenerator import (
    handle_generate_code,
    get_all_cached_codes,
    get_code_history_table_data,
    load_cached_code
)

# ============================================================================
# IMPORTS - RECORDING
# ============================================================================
# Import recording functions
from features.recording import (
    start_recording_session,
    stop_recording_session,
    get_recorded_actions,
    get_generated_playwright_code,
    convert_actions_to_test_steps,
    save_recorded_flow,
    load_recorded_flow,
    get_all_recorded_flows,
    get_recorded_flow_for_test_case,
    has_recorded_flow,
    kill_ghost_processes
)

# ============================================================================
# USER INTERFACE
# ============================================================================

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Show user info
    if st.session_state.get("user_identified", False):
        st.caption(f"👤 {st.session_state.first_name} {st.session_state.last_name}")
        st.caption(f"📧 {st.session_state.user_email}")
        st.divider()
    
    # Provider selection
    provider = st.selectbox("Provider", list(PROVIDERS.keys()))
    
    # Get API key from session state
    if provider == "OpenAI":
        existing_key = st.session_state.get("openai_key", "")
    elif provider == "Anthropic":
        existing_key = st.session_state.get("anthropic_key", "")
    elif provider == "OpenRouter":
        existing_key = st.session_state.get("openrouter_key", "")
    else:
        existing_key = ""
    
    if existing_key:
        st.success(f"✅ {provider} API Key saved")
        show_key_input = st.checkbox("Update API Key", value=False)
    else:
        show_key_input = True
    
    # API Key input
    if show_key_input:
        typed_key = st.text_input("API Key", type="password", value="")
        st.markdown("📺 [How to generate API Key?](#)", unsafe_allow_html=True)
    else:
        typed_key = existing_key
    
    # Model selection
    model = st.selectbox("Model", PROVIDERS[provider]["models"])
    
    # Test and Save button
    if show_key_input and typed_key:
        if st.button("Test & Save API Key", key="test_api", type="primary"):
            # Validate using utility function
            with st.spinner(f"Validating {provider} API key..."):
                if provider == "OpenAI":
                    is_valid = validate_openai_key(typed_key)
                    key_name = "openai_key"
                elif provider == "Anthropic":
                    is_valid = validate_anthropic_key(typed_key)
                    key_name = "anthropic_key"
                elif provider == "OpenRouter":
                    is_valid = validate_openrouter_key(typed_key)
                    key_name = "openrouter_key"
                else:
                    is_valid = False
                    key_name = None
                
            if is_valid and key_name:
                # Save to session state
                st.session_state[key_name] = typed_key
                os.environ[PROVIDERS[provider]["env_var"]] = typed_key
                
                # Save to encrypted storage
                credentials = {
                    "openai_key": st.session_state.get("openai_key", ""),
                    "anthropic_key": st.session_state.get("anthropic_key", ""),
                    "openrouter_key": st.session_state.get("openrouter_key", ""),
                    "jira_email": st.session_state.get("jira_email", ""),
                    "jira_token": st.session_state.get("jira_token", ""),
                    "jira_url": st.session_state.get("jira_url", "")
                }
                save_user_credentials(
                    st.session_state.first_name,
                    st.session_state.last_name,
                    credentials
                )
                
                st.success("✅ API Key is valid and saved!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ API Key validation failed. Please check your key.")
                st.info(f"Make sure you have a valid {provider} API key with sufficient credits.")
    
    st.divider()
    
    # Jira configuration
    st.subheader("Jira Configuration")
    
    # Get Jira credentials from session state
    existing_jira_email = st.session_state.get("jira_email", "")
    existing_jira_token = st.session_state.get("jira_token", "")
    existing_jira_url = st.session_state.get("jira_url", "https://welocalizedev.atlassian.net/")
    
    if existing_jira_email and existing_jira_token:
        st.success("✅ Jira credentials saved")
        show_jira_input = st.checkbox("Update Jira Credentials", value=False)
    else:
        show_jira_input = True
    
    # Jira inputs
    if show_jira_input:
        # Jira email - auto-use user email or allow override
        email_display_value = ""
        if existing_jira_email:
            if "@welocalize.com" in existing_jira_email:
                email_display_value = existing_jira_email.replace("@welocalize.com", "")
            else:
                email_display_value = existing_jira_email
        elif st.session_state.get("user_email"):
            email_display_value = st.session_state.user_email.replace("@welocalize.com", "")
        
        jira_email_input = st.text_input(
            "Jira Email", 
            value=email_display_value,
            help="Enter firstname.lastname (e.g., john.doe). @welocalize.com will be added automatically.",
            placeholder="firstname.lastname"
        )
        
        # Auto-append @welocalize.com if not present
        if jira_email_input:
            if "@welocalize.com" not in jira_email_input:
                jira_email = f"{jira_email_input}@welocalize.com"
            else:
                jira_email = jira_email_input
        else:
            jira_email = existing_jira_email or st.session_state.get("user_email", "")
        
        # Show the full email if auto-appended
        if jira_email_input and "@welocalize.com" not in jira_email_input:
            st.caption(f"📧 Email will be: {jira_email}")
        
        jira_api_token = st.text_input("Jira API Token", type="password", value="")
        jira_url = st.text_input("Jira URL", value=existing_jira_url, 
                                 help="Your Jira instance URL")
        st.markdown("📺 [How to generate Jira API Token?](#)", unsafe_allow_html=True)
        
        if jira_email and jira_api_token:
            if st.button("Test & Save Jira Credentials", key="save_jira", type="primary"):
                # Validate Jira credentials
                with st.spinner("Validating Jira credentials..."):
                    is_valid = validate_jira_credentials(jira_email, jira_api_token, jira_url)
                
                if is_valid:
                    # Save to session state
                    st.session_state.jira_email = jira_email
                    st.session_state.jira_token = jira_api_token
                    st.session_state.jira_url = jira_url
                    
                    # Save to encrypted storage
                    credentials = {
                        "openai_key": st.session_state.get("openai_key", ""),
                        "anthropic_key": st.session_state.get("anthropic_key", ""),
                        "openrouter_key": st.session_state.get("openrouter_key", ""),
                        "jira_email": jira_email,
                        "jira_token": jira_api_token,
                        "jira_url": jira_url
                    }
                    save_user_credentials(
                        st.session_state.first_name,
                        st.session_state.last_name,
                        credentials
                    )
                    
                    st.success("✅ Jira credentials are valid and saved!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Jira credentials validation failed.")
                    st.info("Please check your Jira email, API token, and URL.")
    else:
        # Use existing credentials
        jira_email = existing_jira_email
        jira_api_token = existing_jira_token
        jira_url = existing_jira_url
    
    st.divider()
    
    # Help section at bottom of sidebar
    st.markdown("### 📚 Help & Resources")
    st.markdown("🎬 [Watch: How to use this tool](#)")
    st.markdown("💡 [Setup Guide](#)")

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================

# Top left corner - App title
st.markdown("<p style='font-size: 14px; color: #666; margin-bottom: 20px;'><b>QA Assist</b><br><small>your tc generator and code generator</small></p>", unsafe_allow_html=True)

st.title("Test Case Generator and Playwright Code Generator")

# ============================================================================
# TEST CASE GENERATION SECTION (EXISTING)
# ============================================================================
st.subheader("📋 Generate Test Cases from Jira")

# Feature story input
feature_text = st.text_area(
    "Jira Feature story for which you want test cases and playwright code to be generated:",
    height=100
)

generate = st.button("Generate Test Cases", type="primary")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Detect page refresh and clear session state
if "page_loaded" not in st.session_state:
    # First time page loads - clear everything
    st.session_state.page_loaded = True
    st.session_state.test_cases = []
    st.session_state.ticket_history = []
    st.session_state.current_ticket_id = ""
    st.session_state.valid_jira_ticket = False
    st.session_state.pending_context = None
    st.session_state.pending_ticket_id = ""
    # Initialize recording session state
    st.session_state.recording_session = None
    st.session_state.recording_url = ""
    st.session_state.is_recording = False
    st.session_state.recorded_actions = []
    st.session_state.recorded_test_steps = []
    st.session_state.recording_id = ""
    st.session_state.show_recorded_code = False
    st.session_state.use_recorded_steps = False
    # Initialize code generation state
    st.session_state.generated_code = None
    st.session_state.selected_test_case_for_code = None
    st.session_state.show_code_generator = False
else:
    # Page already loaded - check if we need to initialize
    if "ticket_history" not in st.session_state:
        st.session_state.ticket_history = []
    if "test_cases" not in st.session_state:
        st.session_state.test_cases = []
    if "current_ticket_id" not in st.session_state:
        st.session_state.current_ticket_id = ""
    if "valid_jira_ticket" not in st.session_state:
        st.session_state.valid_jira_ticket = False
    # Initialize recording session state
    if "recording_session" not in st.session_state:
        st.session_state.recording_session = None
    if "recording_url" not in st.session_state:
        st.session_state.recording_url = ""
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    if "recorded_actions" not in st.session_state:
        st.session_state.recorded_actions = []
    if "recorded_test_steps" not in st.session_state:
        st.session_state.recorded_test_steps = []
    if "recording_id" not in st.session_state:
        st.session_state.recording_id = ""
    if "show_recorded_code" not in st.session_state:
        st.session_state.show_recorded_code = False
    if "use_recorded_steps" not in st.session_state:
        st.session_state.use_recorded_steps = False
    # Initialize code generation state
    if "generated_code" not in st.session_state:
        st.session_state.generated_code = None
    if "selected_test_case_for_code" not in st.session_state:
        st.session_state.selected_test_case_for_code = None
    if "show_code_generator" not in st.session_state:
        st.session_state.show_code_generator = False

# ============================================================================
# TEST CASE GENERATION
# ============================================================================

# Generate test cases when button is clicked
if generate:
    # Get user info from session state
    first_name = st.session_state.get("first_name", "")
    last_name = st.session_state.get("last_name", "")
    
    with st.spinner("Validating credentials and generating test cases..."):
        # Call generator logic function
        result = handle_generate_test_cases(
            feature_text=feature_text,
            first_name=first_name,
            last_name=last_name,
            provider=provider,
            model=model
        )
    
    # Handle result
    if not result["success"]:
        # Check if needs more information
        if result.get("needs_more_info", False):
            context_data = result.get("context_data")
            if context_data:
                # Save context to session state
                st.session_state.pending_context = context_data
                st.session_state.pending_ticket_id = context_data.get("ticket_id", "")
                
                # Show error with questions
                st.warning(f"ℹ️ {result['error']}")
                
                # Show form for additional information
                st.divider()
                st.subheader("📝 Provide Additional Information")
                st.write("Please provide additional details about the ticket (backstory, epic description, feature details, etc.):")
                
                additional_info = st.text_area(
                    "Additional Information",
                    height=150,
                    placeholder="Paste backstory, epic description, feature details, acceptance criteria, or any other relevant information here...",
                    key="additional_info_input"
                )
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🔄 Generate with Additional Info", type="primary"):
                        if additional_info and additional_info.strip():
                            # Generate with additional info
                            from features.testCaseGeneration import generate_test_cases_with_additional_info
                            
                            with st.spinner("Generating test cases with additional information..."):
                                df, raw, error, formatted_test_cases, new_context = generate_test_cases_with_additional_info(
                                    context_data=context_data,
                                    additional_info=additional_info.strip(),
                                    first_name=first_name,
                                    last_name=last_name,
                                    provider=provider,
                                    model=model
                                )
                                
                                if error:
                                    if error.startswith("NEEDS_MORE_INFO:"):
                                        st.warning(f"ℹ️ {error.replace('NEEDS_MORE_INFO:', '')}")
                                        st.info("💡 Please provide even more detailed information above and try again.")
                                        st.session_state.pending_context = new_context if new_context else context_data
                                    else:
                                        st.error(f"❌ {error}")
                                else:
                                    # Success - clear pending context
                                    if "pending_context" in st.session_state:
                                        del st.session_state.pending_context
                                    if "pending_ticket_id" in st.session_state:
                                        del st.session_state.pending_ticket_id
                                    
                                    # Use formatted test cases
                                    if formatted_test_cases:
                                        test_cases = formatted_test_cases
                                    else:
                                        test_cases = [{
                                            "id": "TC-01",
                                            "title": "Test Case 1",
                                            "steps": df.to_dict('records')
                                        }]
                                    
                                    st.session_state.test_cases = test_cases
                                    st.session_state.valid_jira_ticket = True
                                    # Store ticket ID for cache saving
                                    from features.testCaseGeneration.generator import extract_ticket_id
                                    ticket_id = extract_ticket_id(feature_text)
                                    if ticket_id:
                                        st.session_state.current_ticket_id = ticket_id
                                        
                                        # Get ticket summary
                                        ticket_summary = feature_text.split('\n')[0][:100] if feature_text else ticket_id
                                        
                                        # Save to ticket history
                                        st.session_state.ticket_history = update_ticket_in_history(
                                            st.session_state.get("ticket_history", []),
                                            ticket_id,
                                            ticket_summary,
                                            test_cases
                                        )
                                    
                                    st.success("✅ Test cases generated successfully with additional information!")
                                    st.rerun()
                        else:
                            st.warning("⚠️ Please provide additional information before generating.")
        elif result["error"]:
            st.error(f"❌ {result['error']}")
        else:
            st.warning("No test cases generated.")
    else:
        # Store in session state
        st.session_state.test_cases = result["test_cases"]
        
        # Mark valid ticket as found
        st.session_state.valid_jira_ticket = True
        
        # Store ticket ID for cache saving
        from features.testCaseGeneration.generator import extract_ticket_id
        ticket_id = extract_ticket_id(feature_text)
        if ticket_id:
            st.session_state.current_ticket_id = ticket_id
            
            # Get ticket summary from feature text or use ticket ID
            ticket_summary = feature_text.split('\n')[0][:100] if feature_text else ticket_id
            
            # Save to ticket history
            st.session_state.ticket_history = update_ticket_in_history(
                st.session_state.get("ticket_history", []),
                ticket_id,
                ticket_summary,
                result["test_cases"]
            )
        
        # Check if test cases were loaded from cache
        if "Cached test cases" in result.get("raw", ""):
            st.success("✅ Test cases loaded from cache!")
            st.info("💾 Using previously generated test cases. To regenerate, delete the cache file or modify the Jira ticket.")
        else:
            st.success("✅ Test cases generated successfully!")
        
        with st.expander("Raw model output (debug)"):
            st.code(result["raw"])

# ============================================================================
# HANDLE PENDING CONTEXT (Additional Information Needed)
# ============================================================================

# Show additional info form if there's pending context
if st.session_state.get("pending_context") and not st.session_state.get("valid_jira_ticket", False):
    context_data = st.session_state.pending_context
    ticket_id = st.session_state.get("pending_ticket_id", "")
    
    st.divider()
    st.subheader("📝 Additional Information Required")
    st.warning(f"ℹ️ The Jira ticket {ticket_id} needs more information to generate test cases.")
    
    # Show questions if available
    questions = context_data.get("questions", [])
    if questions:
        st.write("**Please provide information about:**")
        for q in questions:
            st.write(f"- {q}")
    
    st.write("**Please provide additional details** (backstory, epic description, feature details, acceptance criteria, etc.):")
    
    additional_info = st.text_area(
        "Additional Information",
        height=150,
        placeholder="Paste backstory, epic description, feature details, acceptance criteria, or any other relevant information here...",
        key="additional_info_pending"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Generate with Additional Info", type="primary", key="generate_with_info"):
            if additional_info and additional_info.strip():
                # Get user info
                first_name = st.session_state.get("first_name", "")
                last_name = st.session_state.get("last_name", "")
                
                # Generate with additional info
                from features.testCaseGeneration import generate_test_cases_with_additional_info
                
                with st.spinner("Generating test cases with additional information..."):
                    df, raw, error, formatted_test_cases, new_context = generate_test_cases_with_additional_info(
                        context_data=context_data,
                        additional_info=additional_info.strip(),
                        first_name=first_name,
                        last_name=last_name,
                        provider=provider,
                        model=model
                    )
                    
                    if error:
                        if error.startswith("NEEDS_MORE_INFO:"):
                            st.warning(f"ℹ️ {error.replace('NEEDS_MORE_INFO:', '')}")
                            st.info("💡 Please provide even more detailed information above and try again.")
                            st.session_state.pending_context = new_context if new_context else context_data
                        else:
                            st.error(f"❌ {error}")
                    else:
                        # Success - clear pending context
                        if "pending_context" in st.session_state:
                            del st.session_state.pending_context
                        if "pending_ticket_id" in st.session_state:
                            del st.session_state.pending_ticket_id
                        
                        # Use formatted test cases
                        if formatted_test_cases:
                            test_cases = formatted_test_cases
                        else:
                            test_cases = [{
                                "id": "TC-01",
                                "title": "Test Case 1",
                                "steps": df.to_dict('records')
                            }]
                        
                        st.session_state.test_cases = test_cases
                        st.session_state.valid_jira_ticket = True
                        
                        # Update ticket history
                        ticket_id = st.session_state.get("pending_ticket_id", "")
                        if ticket_id:
                            ticket_summary = feature_text.split('\n')[0][:100] if feature_text else ticket_id
                            st.session_state.ticket_history = update_ticket_in_history(
                                st.session_state.get("ticket_history", []),
                                ticket_id,
                                ticket_summary,
                                test_cases
                            )
                        
                        st.success("✅ Test cases generated successfully with additional information!")
                        st.rerun()
            else:
                st.warning("⚠️ Please provide additional information before generating.")

# ============================================================================
# TEST CASES DISPLAY & EDITING
# ============================================================================

# Check if valid Jira ticket is available (will be updated later with actual validation)
# For now, hide sections until valid ticket is found
valid_jira_ticket = st.session_state.get("valid_jira_ticket", False)

# Only show test cases section if valid Jira ticket is available
if valid_jira_ticket:
    # Display test cases section header
    st.subheader("Generated Test Cases")

    # Add new test case button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("➕ Add Test Case"):
            new_num = len(st.session_state.test_cases) + 1
            st.session_state.test_cases.append({
                "id": f"TC-{new_num:02d}",
                "title": f"Test Case {new_num}",
                "steps": [{"Step": "1. ", "Expected Result": ""}]
            })
            st.rerun()

    # Display test cases in a grid/table format
    st.markdown("### Test Cases Grid")
    
    # Create a table view of test cases
    if st.session_state.test_cases:
        # Prepare data for grid display
        grid_data = []
        for idx, test_case in enumerate(st.session_state.test_cases):
            test_case_id = test_case.get('id', f'TC-{idx+1:02d}')
            test_case_title = test_case.get('title', f'Test Case {idx+1}')
            steps = test_case.get('steps', [])
            num_steps = len(steps) if steps else 0
            grid_data.append({
                "ID": test_case_id,
                "Title": test_case_title,
                "Steps": num_steps
            })
        
        # Display as dataframe
        grid_df = pd.DataFrame(grid_data)
        st.dataframe(
            grid_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("Test Case ID", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Steps": st.column_config.NumberColumn("Steps", width="small")
            }
        )
    
    st.markdown("---")
    st.markdown("### Test Cases Details")
    
    # Display each test case as an expandable row
    for idx, test_case in enumerate(st.session_state.test_cases):
        test_case_num = idx + 1
        test_case_id = test_case.get('id', f'TC-{test_case_num:02d}')
        test_case_title = test_case.get('title', f'Test Case {test_case_num}')
        
        # Expandable row for each test case
        with st.expander(f"Test Case {test_case_num}: {test_case_title}", expanded=False):
            # Test Case Title - editable
            new_title = st.text_input(
                "Test Case Title",
                value=test_case_title,
                key=f"title_{idx}"
            )
            st.session_state.test_cases[idx]['title'] = new_title
            
            # Display steps and expected results in editable table format
            if test_case.get('steps'):
                # Create DataFrame for editable table
                df = pd.DataFrame(test_case['steps'])
                
                # Use data_editor for editable grid (pure Streamlit, no HTML)
                updated_df = st.data_editor(
                    df,
                    num_rows="dynamic",
                    width="stretch",
                    key=f"steps_{idx}",
                    hide_index=True,
                    column_config={
                        "Step": st.column_config.TextColumn(
                            "Step",
                            width="large",
                            help="Test step description"
                        ),
                        "Expected Result": st.column_config.TextColumn(
                            "Expected Result",
                            width="large",
                            help="Expected outcome for this step"
                        )
                    }
                )
                st.session_state.test_cases[idx]['steps'] = updated_df.to_dict('records')
            else:
                st.info("No steps available for this test case. Add steps using the table above.")
            
            # Delete test case button
            if len(st.session_state.test_cases) > 1:
                if st.button(f"🗑️ Delete Test Case {test_case_num}", key=f"delete_{idx}"):
                    st.session_state.test_cases.pop(idx)
                    st.rerun()

    # ============================================================================
    # FEEDBACK & REGENERATION
    # ============================================================================

    # Feedback section for regenerating test cases
    st.divider()
    st.subheader("💬 Not Happy with Test Cases?")
    st.write("Review the generated test cases above and provide feedback on what you'd like to change.")
    
    # Show current test cases summary
    st.info(f"📊 Currently have {len(st.session_state.test_cases)} test case(s). Provide feedback to modify them.")

    feedback_text = st.text_area(
        "Tell us what you'd like to change:",
        placeholder="Examples:\n- Add more negative test scenarios\n- Make steps more detailed\n- Add edge cases for boundary testing\n- Remove test case TC-03\n- Modify test case TC-01 to include validation steps\n- Add test cases for error handling\n- Combine similar test cases",
        height=100,
        help="Be specific about what you want to change, add, or remove in the test cases"
    )

    col1, col2, col3 = st.columns([3, 1, 3])
    with col2:
        regenerate_button = st.button("🔄 Regenerate", type="secondary", use_container_width=True)

    if regenerate_button:
        # Get user info from session state
        first_name = st.session_state.get("first_name", "")
        last_name = st.session_state.get("last_name", "")
        
        with st.spinner("Regenerating test cases based on your feedback..."):
            # Get ticket ID from session state or extract from feature text
            ticket_id = st.session_state.get("current_ticket_id", "")
            if not ticket_id:
                from features.testCaseGeneration.generator import extract_ticket_id
                ticket_id = extract_ticket_id(feature_text)
            
            # Call generator logic function
            result = handle_regenerate_test_cases(
                original_feature_text=feature_text,
                current_test_cases=st.session_state.test_cases,
                feedback_text=feedback_text,
                first_name=first_name,
                last_name=last_name,
                provider=provider,
                model=model,
                ticket_id=ticket_id
            )
        
        # Handle result
        if not result["success"]:
            if result["error"]:
                st.error(f"❌ {result['error']}")
            else:
                st.warning("No test cases generated.")
        else:
            # Update test cases
            st.session_state.test_cases = result["test_cases"]
            
            # Ensure ticket ID is stored for future regenerations
            if "current_ticket_id" not in st.session_state:
                from features.testCaseGeneration.generator import extract_ticket_id
                ticket_id = extract_ticket_id(feature_text)
                if ticket_id:
                    st.session_state.current_ticket_id = ticket_id
            
            # Update ticket history with regenerated test cases
            current_ticket_id = st.session_state.get("current_ticket_id", "")
            if current_ticket_id:
                ticket_summary = feature_text.split('\n')[0][:100] if feature_text else current_ticket_id
                st.session_state.ticket_history = update_ticket_in_history(
                    st.session_state.get("ticket_history", []),
                    current_ticket_id,
                    ticket_summary,
                    result["test_cases"]
                )
            
            st.success("✅ Test cases regenerated based on your feedback!")
            st.rerun()

    # ============================================================================
    # EXPORT & PUBLISH TO JIRA
    # ============================================================================

    # Export and Publish buttons at the bottom
    st.divider()
    st.subheader("Export & Publish")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Export to CSV button
        csv_data = export_test_cases_to_csv(st.session_state.test_cases)
        st.download_button(
            label="📥 Export CSV",
            data=csv_data,
            file_name="test_cases.csv",
            mime="text/csv",
            use_container_width=True,
            type="secondary"
        )
    
    with col2:
        # Export to Excel button
        excel_data = export_test_cases_to_excel(st.session_state.test_cases)
        st.download_button(
            label="📥 Export Excel",
            data=excel_data,
            file_name="test_cases.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
    
    with col3:
        # Publish to Jira button
        if st.button("📤 Publish to Jira", type="primary", use_container_width=True):
            # Dummy button - will push to Jira as subtask under Pantheon - QA Automation
            with st.spinner("Publishing to Jira..."):
                time.sleep(1)  # Simulate API call
            st.success("✅ Test cases published to Jira under Pantheon - QA Automation project!")
            st.info("Subtask created successfully")

    # ============================================================================
    # CODE GENERATION SECTION
    # ============================================================================
    
    st.divider()
    st.subheader("🔧 Generate Playwright Code")
    
    # Initialize code history state
    if "code_history" not in st.session_state:
        st.session_state.code_history = get_all_cached_codes()
    
    # Code History Section
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 📚 Previously Generated Code")
    with col2:
        if st.button("🔄 Refresh History", key="refresh_code_history"):
            st.session_state.code_history = get_all_cached_codes()
            st.rerun()
    
    code_history = st.session_state.code_history
    if code_history:
        # Display code history table
        history_table_data = get_code_history_table_data(code_history)
        history_df = pd.DataFrame(history_table_data)
        
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Test Case ID": st.column_config.TextColumn("Test Case ID", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Ticket ID": st.column_config.TextColumn("Ticket ID", width="small"),
                "Generated Date": st.column_config.TextColumn("Generated Date", width="medium")
            }
        )
        
        # Code selection
        st.write("**Select a previously generated code to load:**")
        code_options = {}
        for idx, code_data in enumerate(code_history):
            test_case_id = code_data.get("test_case_id", "N/A")
            test_case_title = code_data.get("test_case_title", "N/A")
            ticket_id = code_data.get("ticket_id", "N/A")
            option_label = f"{test_case_id} - {test_case_title} ({ticket_id})"
            code_options[option_label] = idx
        
        selected_code_option = st.selectbox(
            "Choose Generated Code",
            options=list(code_options.keys()),
            key="code_history_selector",
            help="Select previously generated code to load"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📂 Load Selected Code", type="primary", key="load_code_btn"):
                selected_idx = code_options[selected_code_option]
                selected_code_data = code_history[selected_idx]
                
                # Load the code
                st.session_state.generated_code = selected_code_data.get("formatted", {})
                st.session_state.selected_test_case_for_code = {
                    "id": selected_code_data.get("test_case_id", "N/A"),
                    "title": selected_code_data.get("test_case_title", "N/A")
                }
                st.success(f"✅ Loaded code for {selected_code_data.get('test_case_id', 'N/A')}")
                st.rerun()
        
        st.markdown("---")
    else:
        st.info("📝 No previously generated code found. Generate code to see it here.")
        st.markdown("---")
    
    # Initialize code generation state
    if "show_code_generator" not in st.session_state:
        st.session_state.show_code_generator = False
    if "generated_code" not in st.session_state:
        st.session_state.generated_code = None
    if "selected_test_case_for_code" not in st.session_state:
        st.session_state.selected_test_case_for_code = None
    
    # Generate Code button
    if st.button("🚀 Generate Code", type="primary", use_container_width=False):
        st.session_state.show_code_generator = True
        st.rerun()
    
    # Show code generator UI if button was clicked
    if st.session_state.show_code_generator:
        st.markdown("---")
        st.write("**Select a test case to generate Playwright code:**")
        
        # Create test case selection options
        test_case_options = {}
        for idx, test_case in enumerate(st.session_state.test_cases):
            test_case_id = test_case.get('id', f'TC-{idx+1:02d}')
            test_case_title = test_case.get('title', f'Test Case {idx+1}')
            option_label = f"{test_case_id}: {test_case_title}"
            test_case_options[option_label] = idx
        
        if test_case_options:
            selected_option = st.selectbox(
                "Choose Test Case",
                options=list(test_case_options.keys()),
                key="test_case_selector",
                help="Select a test case to generate Playwright code for"
            )
            
            selected_idx = test_case_options[selected_option]
            selected_test_case = st.session_state.test_cases[selected_idx]
            
            # Display selected test case details
            with st.expander("📋 Selected Test Case Details", expanded=False):
                st.write(f"**ID:** {selected_test_case.get('id', 'N/A')}")
                st.write(f"**Title:** {selected_test_case.get('title', 'N/A')}")
                st.write("**Steps:**")
                steps = selected_test_case.get('steps', [])
                if isinstance(steps, list) and len(steps) > 0:
                    if isinstance(steps[0], dict):
                        # Steps are in DataFrame format
                        for step_dict in steps:
                            step_text = step_dict.get('Step', '')
                            if step_text:
                                st.write(f"- {step_text}")
                    else:
                        # Steps are in list format
                        for step in steps:
                            st.write(f"- {step}")
                else:
                    st.write("No steps available")
                
                st.write("**Expected Results:**")
                expected_results = selected_test_case.get('expected_results', [])
                if expected_results:
                    for result in expected_results:
                        st.write(f"- {result}")
                else:
                    st.write("No expected results available")
            
            # Recording option (only shown when test case is selected)
            st.markdown("---")
            st.markdown("### 🎥 Record Browser Flow")
            
            # Check if recording already exists for this test case
            test_case_id = selected_test_case.get('id', 'TC-01')
            ticket_id = st.session_state.get("current_ticket_id", "")
            existing_recording = get_recorded_flow_for_test_case(test_case_id, ticket_id)
            has_recording = existing_recording is not None
            
            if has_recording:
                st.success(f"✅ Recording found for {test_case_id}")
                with st.expander("📹 View Existing Recording", expanded=False):
                    st.write(f"**URL:** {existing_recording.get('url', 'N/A')}")
                    st.write(f"**Recorded:** {existing_recording.get('recorded_date', 'N/A')}")
                    st.write(f"**Actions:** {len(existing_recording.get('actions', []))} actions recorded")
                    if st.button("🗑️ Delete Recording", key="delete_recording_btn"):
                        # Delete the recording file
                        import os
                        recording_file = existing_recording.get('_file_path')
                        if recording_file and os.path.exists(recording_file):
                            os.remove(recording_file)
                            st.success("✅ Recording deleted")
                            st.rerun()
            
            # Kill ghost processes button
            col_kill1, col_kill2 = st.columns([1, 4])
            with col_kill1:
                if st.button("🔧 Kill Ghost Processes", type="secondary", use_container_width=True, key="kill_ghost_btn", help="Kill any stuck browser processes"):
                    try:
                        kill_ghost_processes()
                        st.success("✅ Ghost processes killed (if any were found)")
                        st.info("💡 If issues persist, run: chmod +x kill_ghost_processes.sh && ./kill_ghost_processes.sh")
                    except Exception as e:
                        st.error(f"❌ Failed to kill processes: {str(e)}")
            
            recording_url = st.text_input(
                "Enter URL to record:",
                value=existing_recording.get('url', '') if has_recording else st.session_state.recording_url,
                placeholder="https://example.com",
                key="recording_url_input",
                help="URL you will record in Playwright codegen"
            )
            
            # Manual codegen approach - user copies code from codegen
            st.markdown("#### 📋 Step 1: Generate Code with Playwright Codegen")
            st.info("""
            **Instructions:**
            1. Open terminal and run: `npx playwright codegen <your-url>`
            2. Interact with the browser to record your flow
            3. Copy the generated Python code from the codegen window
            4. Paste it in the text area below
            """)
            
            col_launch1, col_launch2 = st.columns([1, 4])
            with col_launch1:
                if st.button("🚀 Launch Codegen", type="secondary", use_container_width=True, key="launch_codegen_btn"):
                    if recording_url and recording_url.strip():
                        try:
                            import subprocess
                            import platform
                            cmd = ["npx", "playwright", "codegen", recording_url.strip()]
                            
                            if platform.system() == "Windows":
                                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
                            else:
                                subprocess.Popen(cmd, stdout=None, stderr=None, start_new_session=True)
                            
                            st.success(f"✅ Codegen launched! Browser should open shortly.")
                            st.info("💡 Record your flow, then copy the generated code and paste it below.")
                        except Exception as e:
                            st.error(f"❌ Failed to launch codegen: {str(e)}")
                            st.info("💡 You can also run manually: `npx playwright codegen <url>`")
                    else:
                        st.warning("⚠️ Please enter a URL first.")
            
            st.markdown("#### 📝 Step 2: Paste Generated Code")
            pasted_code = st.text_area(
                "Paste Playwright codegen output here (Python code):",
                value=st.session_state.get("pasted_codegen_code", ""),
                height=200,
                key="pasted_codegen_input",
                help="Paste the Python code generated by Playwright codegen"
            )
            
            if pasted_code and pasted_code.strip():
                st.session_state.pasted_codegen_code = pasted_code.strip()
                
                col_save1, col_save2 = st.columns([1, 4])
                with col_save1:
                    if st.button("💾 Save & Process Code", type="primary", use_container_width=True, key="save_codegen_btn"):
                        try:
                            # Process the pasted code
                            from features.recording import save_recorded_flow
                            
                            # Extract actions from code
                            actions = []
                            test_steps = []
                            
                            lines = pasted_code.strip().split('\n')
                            for line in lines:
                                line = line.strip()
                                if 'page.goto(' in line:
                                    # Extract URL
                                    for quote in ['"', "'"]:
                                        pattern = f'page.goto({quote}'
                                        if pattern in line:
                                            start = line.find(pattern) + len(pattern)
                                            end = line.find(quote, start)
                                            if end > start:
                                                url = line[start:end]
                                                actions.append({
                                                    "type": "navigate",
                                                    "url": url,
                                                    "timestamp": datetime.now().isoformat()
                                                })
                                                test_steps.append(f"Navigate to {url}")
                                                break
                                elif '.click()' in line:
                                    # Extract click action
                                    if 'get_by_test_id(' in line:
                                        start = line.find('get_by_test_id("') + len('get_by_test_id("')
                                        if start < len('get_by_test_id("'):
                                            start = line.find("get_by_test_id('") + len("get_by_test_id('")
                                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                                        if end > start:
                                            selector = line[start:end]
                                            actions.append({
                                                "type": "click",
                                                "selector": {"type": "testid", "value": selector},
                                                "timestamp": datetime.now().isoformat()
                                            })
                                            test_steps.append(f"Click element with test-id: {selector}")
                            
                            if actions:
                                # Save to JSON
                                recording_id = f"REC-{int(time.time())}"
                                ticket_id = st.session_state.get("current_ticket_id", "")
                                
                                recorded_flow_json_path = save_recorded_flow(
                                    recording_id,
                                    recording_url.strip() if recording_url else "",
                                    actions,
                                    test_steps,
                                    f"Recorded Flow - {recording_url.strip() if recording_url else 'Manual'}",
                                    ticket_id=ticket_id,
                                    generated_code={"python": pasted_code.strip(), "javascript": ""},
                                    test_case_id=test_case_id
                                )
                                
                                st.session_state.recorded_flow_json_path = recorded_flow_json_path
                                st.session_state.recorded_actions = actions
                                st.session_state.recorded_test_steps = test_steps
                                
                                st.success(f"✅ Code saved! Found {len(actions)} actions.")
                                st.info("💡 You can now click 'Generate Playwright Code' below to generate POM/DRY code.")
                                st.rerun()
                            else:
                                st.warning("⚠️ No actions found in the code. Please check the format.")
                        except Exception as e:
                            st.error(f"❌ Failed to process code: {str(e)}")
            
            # Old recording buttons (keeping for backward compatibility, but hidden)
            if False:  # Disable old recording
                if not st.session_state.is_recording:
                    if st.button("🎥 Record", type="secondary", use_container_width=True, key="start_record_btn"):
                            try:
                                # Get actions first (before stopping)
                                actions = get_recorded_actions()
                                st.session_state.recorded_actions = actions
                                
                                # Stop the session and get generated code (stop returns the code)
                                generated_code = stop_recording_session()
                                st.session_state.is_recording = False
                                st.session_state.recording_session = None
                                
                                # Convert actions to test steps
                                test_steps = convert_actions_to_test_steps(actions)
                                st.session_state.recorded_test_steps = test_steps
                                
                                # Save recorded flow to JSON file (update if exists)
                                recorded_flow_json_path = None
                                if st.session_state.recording_id and actions:
                                    ticket_id = st.session_state.get("current_ticket_id", "")
                                    test_case_id = selected_test_case.get('id', 'TC-01')
                                    
                                    # Use existing recording ID if updating
                                    recording_id_to_use = st.session_state.recording_id
                                    if has_recording and existing_recording:
                                        recording_id_to_use = existing_recording.get('recording_id', st.session_state.recording_id)
                                    
                                    recorded_flow_json_path = save_recorded_flow(
                                        recording_id_to_use,
                                        st.session_state.recording_url,
                                        actions,
                                        test_steps,
                                        f"Recorded Flow - {st.session_state.recording_url}",
                                        ticket_id=ticket_id,
                                        generated_code=generated_code,
                                        test_case_id=test_case_id
                                    )
                                    st.session_state.recorded_flow_json_path = recorded_flow_json_path
                                
                                st.success("✅ Recording stopped!")
                                
                                # If we have generated code, display it directly in the tabs
                                if generated_code and (generated_code.get("python") or generated_code.get("javascript")):
                                    # Format code for display in existing tab structure
                                    formatted_code = {
                                        "locators_python": generated_code.get("locators_python", ""),
                                        "locators_javascript": generated_code.get("locators_javascript", ""),
                                        "reusable_functions_python": generated_code.get("python", ""),
                                        "reusable_functions_javascript": generated_code.get("javascript", ""),
                                        "test_functions_python": "",  # Will be generated by code generator
                                        "test_functions_javascript": "",  # Will be generated by code generator
                                        "cursor_prompt": ""  # Will be generated by code generator
                                    }
                                    st.session_state.generated_code = formatted_code
                                    st.session_state.selected_test_case_for_code = {
                                        "id": st.session_state.recording_id or "REC-01",
                                        "title": f"Recorded Flow - {st.session_state.recording_url}"
                                    }
                                    st.info("💡 Playwright code generated from recording! Scroll down to see it in the tabs.")
                                    st.rerun()
                                elif test_steps and len(test_steps) > 0:
                                    # Update the selected test case steps with recorded steps
                                    st.session_state.use_recorded_steps = True
                                    # Store recorded flow JSON path for code generation
                                    if recorded_flow_json_path:
                                        st.session_state.recorded_flow_json_path = recorded_flow_json_path
                                    st.info("💡 Recorded flow saved! Click 'Generate Playwright Code' below to generate code using the recorded flow.")
                                    st.rerun()
                                else:
                                    st.warning("⚠️ No actions were recorded. Please try again.")
                                    
                            except Exception as e:
                                st.error(f"❌ Failed to stop recording: {str(e)}")
                                # Force cleanup on error
                                try:
                                    kill_ghost_processes()
                                    stop_recording_session()
                                except:
                                    pass
                                st.session_state.is_recording = False
                    with col_stop2:
                        if st.button("🔧 Force Kill", type="secondary", use_container_width=True, key="force_kill_btn", help="Force kill browser if stuck"):
                            try:
                                kill_ghost_processes()
                                stop_recording_session()
                                st.session_state.is_recording = False
                                st.session_state.recording_session = None
                                st.warning("⚠️ Recording forcefully stopped. Any recorded actions may be lost.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to force kill: {str(e)}")
            
            st.markdown("---")
            
            # Generate button - disabled until recording is saved
            col1, col2 = st.columns([1, 4])
            with col1:
                # Check if recording exists for this test case
                has_saved_recording = has_recorded_flow(test_case_id, ticket_id)
                
                if not has_saved_recording:
                    st.button(
                        "✨ Generate Playwright Code",
                        type="primary",
                        key="generate_code_btn",
                        disabled=True,
                        help="⚠️ Please record a browser flow first before generating code"
                    )
                    st.warning("⚠️ Please record a browser flow first. Click 'Record' above to start recording.")
                else:
                    if st.button("✨ Generate Playwright Code", type="primary", key="generate_code_btn"):
                        # Get test case details
                        test_case_id = selected_test_case.get('id', 'TC-01')
                        test_case_title = selected_test_case.get('title', 'Test Case')
                        
                        # Load recorded flow if available
                        recorded_flow = get_recorded_flow_for_test_case(test_case_id, ticket_id)
                        if recorded_flow:
                            # Use recorded flow data
                            actions = recorded_flow.get('actions', [])
                            test_steps = recorded_flow.get('test_steps', [])
                            steps_list = test_steps if test_steps else []
                            recorded_flow_json = recorded_flow.get('_file_path') or st.session_state.get("recorded_flow_json_path")
                        else:
                            # Extract steps - use recorded steps if available, otherwise use test case steps
                            steps_list = []
                            if st.session_state.get("use_recorded_steps") and st.session_state.get("recorded_test_steps"):
                                # Use recorded steps - they're already in the correct format
                                steps_list = st.session_state.recorded_test_steps
                                st.session_state.use_recorded_steps = False  # Reset flag
                                # Also update the test case title to indicate it's from recording
                                test_case_title = f"{test_case_title} (Recorded Flow)"
                            else:
                                steps = selected_test_case.get('steps', [])
                                if isinstance(steps, list) and len(steps) > 0:
                                    if isinstance(steps[0], dict):
                                        # Steps are in DataFrame format
                                        steps_list = [step_dict.get('Step', '') for step_dict in steps if step_dict.get('Step', '').strip()]
                                    else:
                                        # Steps are in list format
                                        steps_list = [str(step) for step in steps if str(step).strip()]
                            recorded_flow_json = st.session_state.get("recorded_flow_json_path")
                        
                        # Ensure we have steps to generate code
                        if not steps_list or len(steps_list) == 0:
                            st.error("❌ No test steps available. Please record a flow or ensure the test case has steps.")
                            st.stop()
                        
                        # Extract expected results
                        expected_list = selected_test_case.get('expected_results', [])
                        if not expected_list:
                            expected_list = []
                        
                        # Get user info
                        first_name = st.session_state.get("first_name", "")
                        last_name = st.session_state.get("last_name", "")
                        
                        # Get ticket ID if available
                        ticket_id = st.session_state.get("current_ticket_id", "")
                        
                        # Generate code
                        with st.spinner("Generating Playwright code..."):
                            result = handle_generate_code(
                                test_case_id=test_case_id,
                                test_case_title=test_case_title,
                                test_steps=steps_list,
                                expected_results=expected_list,
                                provider=provider,
                                model=model,
                                first_name=first_name,
                                last_name=last_name,
                                ticket_id=ticket_id,
                                recorded_flow_json=recorded_flow_json
                            )
                        
                        if result["success"]:
                            st.session_state.generated_code = result.get("formatted", {})
                            st.session_state.selected_test_case_for_code = {
                                "id": test_case_id,
                                "title": test_case_title
                            }
                            # Refresh code history
                            st.session_state.code_history = get_all_cached_codes()
                            if result.get("cached"):
                                st.success("✅ Code loaded from cache!")
                            else:
                                st.success("✅ Code generated successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Failed to generate code')}")
        else:
            st.warning("⚠️ No test cases available. Please generate test cases first.")
    
    # ============================================================================
    # TICKET HISTORY TABLE
    # ============================================================================
    
    st.divider()
    st.subheader("📋 Generated Tickets History")
    
    # Get ticket history
    ticket_history = st.session_state.get("ticket_history", [])
    
    if ticket_history:
        # Display ticket history table
        history_df = get_ticket_history_table_data(ticket_history)
        
        # Display table with selection
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticket ID": st.column_config.TextColumn("Ticket ID", width="small"),
                "Summary": st.column_config.TextColumn("Summary", width="large"),
                "Test Cases": st.column_config.NumberColumn("Test Cases", width="small"),
                "Generated Date": st.column_config.TextColumn("Generated Date", width="medium")
            }
        )
        
        # Ticket selection
        st.write("**Select a ticket to load its test cases:**")
        selected_ticket_ids = st.multiselect(
            "Select Ticket(s)",
            options=[entry.get("ticket_id", "") for entry in ticket_history],
            key="ticket_selector",
            help="Select one or more tickets to view their test cases"
        )
        
        if selected_ticket_ids:
            # Load selected ticket's test cases
            if st.button("📂 Load Selected Ticket", type="primary"):
                # Load the first selected ticket
                selected_ticket_id = selected_ticket_ids[0]
                ticket_entry = get_ticket_history_entry(ticket_history, selected_ticket_id)
                
                if ticket_entry:
                    st.session_state.test_cases = ticket_entry.get("test_cases", [])
                    st.session_state.current_ticket_id = selected_ticket_id
                    st.session_state.valid_jira_ticket = True
                    st.success(f"✅ Loaded test cases for {selected_ticket_id}")
                    st.rerun()
        
        # Clear history button
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Clear History", type="secondary"):
                st.session_state.ticket_history = clear_ticket_history()
                st.session_state.test_cases = []
                st.session_state.current_ticket_id = ""
                st.session_state.valid_jira_ticket = False
                st.success("✅ Ticket history cleared!")
                st.rerun()
    else:
        st.info("📝 No tickets generated yet. Generate test cases to see them here.")

# ============================================================================
# DISPLAY GENERATED CODE (SHARED FOR BOTH RECORDING AND REGULAR GENERATION)
# ============================================================================

# Display generated code (works for both recording and regular code generation)
if st.session_state.get("generated_code"):
    st.divider()
    st.subheader("📝 Generated Playwright Code")
    
    selected_tc = st.session_state.selected_test_case_for_code
    if selected_tc:
        st.info(f"**Generated for:** {selected_tc.get('id', 'N/A')} - {selected_tc.get('title', 'N/A')}")
    
    code = st.session_state.generated_code
    
    # Use tabs for better organization
    tab1, tab2, tab3 = st.tabs(["📌 Section 1: Locators & Reusable Functions", "🔧 Section 2: Test Functions", "🤖 Section 3: Cursor Prompt"])
    
    with tab1:
        st.markdown("### 📌 Locators and Reusable Functions")
        st.write("Copy the locators and reusable functions below. These should be added to your page class.")
        
        # Python Section
        st.markdown("#### 🐍 Python")
        
        # Python Locators
        if code.get("locators_python"):
            st.markdown("**Locators:**")
            st.code(code["locators_python"], language="python", line_numbers=True)
        else:
            st.info("No Python locators generated.")
        
        st.markdown("---")
        
        # Python Reusable Functions
        if code.get("reusable_functions_python"):
            st.markdown("**Reusable Functions:**")
            st.code(code["reusable_functions_python"], language="python", line_numbers=True)
        else:
            st.info("No Python reusable functions generated.")
        
        st.markdown("---")
        st.markdown("---")
        
        # JavaScript Section
        st.markdown("#### 🟨 JavaScript")
        
        # JavaScript Locators
        if code.get("locators_javascript"):
            st.markdown("**Locators:**")
            st.code(code["locators_javascript"], language="javascript", line_numbers=True)
        else:
            st.info("No JavaScript locators generated.")
        
        st.markdown("---")
        
        # JavaScript Reusable Functions
        if code.get("reusable_functions_javascript"):
            st.markdown("**Reusable Functions:**")
            st.code(code["reusable_functions_javascript"], language="javascript", line_numbers=True)
        else:
            st.info("No JavaScript reusable functions generated.")
    
    with tab2:
        st.markdown("### 🔧 Test-Specific Reusable Functions (POM-based)")
        st.write("Copy the test-specific functions below. These are small, reusable functions for your test case.")
        
        # Python Test Functions
        st.markdown("#### 🐍 Python")
        if code.get("test_functions_python"):
            st.code(code["test_functions_python"], language="python", line_numbers=True)
        else:
            st.info("No Python test functions generated.")
        
        st.markdown("---")
        
        # JavaScript Test Functions
        st.markdown("#### 🟨 JavaScript")
        if code.get("test_functions_javascript"):
            st.code(code["test_functions_javascript"], language="javascript", line_numbers=True)
        else:
            st.info("No JavaScript test functions generated.")
    
    with tab3:
        st.markdown("### 🤖 Cursor AI Prompt")
        st.write("Copy the prompt below and paste it into Cursor AI to integrate the generated code into your page classes:")
        
        if code.get("cursor_prompt"):
            st.code(code["cursor_prompt"], language="text", line_numbers=False)
            st.info("💡 **Tip:** Copy this prompt and paste it into Cursor AI. It will help you integrate the code following POM and DRY principles.")
        else:
            st.info("No Cursor prompt generated.")
    
    # Clear generated code button
    st.markdown("---")
    if st.button("🗑️ Clear Generated Code", type="secondary"):
        st.session_state.generated_code = None
        st.session_state.selected_test_case_for_code = None
        st.rerun()

# ============================================================================
# TUTORIAL & FOOTER
# ============================================================================

# Demo/Tutorial section (placeholder for future GIF/video)
st.divider()
st.markdown("### 🎥 How it Works")
st.markdown(
    """
    <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px;'>
        <p style='color: #666;'>Tutorial video/GIF will be displayed here</p>
        <p style='font-size: 12px; color: #999;'>(Upload your demo GIF or video here in the future)</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px; font-size: 12px;'>
        <p>Your QA Assistant - Test Case Generator and Code Generator</p>
    </div>
    """,
    unsafe_allow_html=True
)