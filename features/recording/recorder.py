"""
Browser Recording Logic using Playwright's built-in codegen
"""
import json
import os
import time
import re
from typing import Dict, List, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from .playwright_codegen import PlaywrightCodegenRecorder


# Cache directory for recorded flows
RECORDING_CACHE_DIR = "recordings"


def ensure_recording_cache_dir():
    """Ensure the recording cache directory exists"""
    if not os.path.exists(RECORDING_CACHE_DIR):
        os.makedirs(RECORDING_CACHE_DIR, exist_ok=True)


def get_recording_cache_file_path(recording_id: str) -> str:
    """
    Get the cache file path for a recorded flow.
    
    Args:
        recording_id: Unique recording ID
        
    Returns:
        Path to the cache file
    """
    ensure_recording_cache_dir()
    safe_id = recording_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
    filename = f"{safe_id}_recording.json"
    return os.path.join(RECORDING_CACHE_DIR, filename)


def load_recorded_flow(recording_id: str) -> Optional[Dict]:
    """
    Load a recorded flow from cache.
    
    Args:
        recording_id: Recording ID
        
    Returns:
        Recorded flow dict or None if not found
    """
    cache_file = get_recording_cache_file_path(recording_id)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None
    return None


def save_recorded_flow(
    recording_id: str,
    url: str,
    actions: List[Dict],
    test_steps: List[str],
    test_case_title: str = "Recorded Flow",
    ticket_id: str = None,
    generated_code: Dict[str, str] = None,
    test_case_id: str = None
) -> str:
    """
    Save a recorded flow to cache and codeGenerated folder.
    
    Args:
        recording_id: Unique recording ID
        url: Starting URL
        actions: List of recorded actions
        test_steps: Converted test steps
        test_case_title: Title for the test case
        ticket_id: Optional ticket ID for filename
        
    Returns:
        Path to saved JSON file
    """
    try:
        # Save to recordings cache
        ensure_recording_cache_dir()
        cache_file = get_recording_cache_file_path(recording_id)
        
        save_data = {
            "recording_id": recording_id,
            "url": url,
            "test_case_title": test_case_title,
            "actions": actions,
            "test_steps": test_steps,
            "recorded_date": datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        # Also save to codeGenerated folder (like PAN-12776_TC-01_code.json format)
        from features.codeGenerator.generator import ensure_code_cache_dir
        ensure_code_cache_dir()
        
        # Generate filename
        if ticket_id:
            safe_ticket_id = ticket_id.replace("/", "_").replace("\\", "_")
            safe_recording_id = recording_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
            codegen_filename = f"{safe_ticket_id}_{safe_recording_id}_recording.json"
        else:
            safe_recording_id = recording_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
            codegen_filename = f"{safe_recording_id}_recording.json"
        
        codegen_file = os.path.join("codeGenerated", codegen_filename)
        
        # Save full recorded flow with all events and generated code
        codegen_data = {
            "recording_id": recording_id,
            "test_case_id": test_case_id or recording_id,
            "ticket_id": ticket_id or "",
            "test_case_title": test_case_title,
            "url": url,
            "actions": actions,  # Full recorded actions
            "test_steps": test_steps,
            "generated_code": generated_code or {},
            "recorded_date": datetime.now().isoformat()
        }
        
        with open(codegen_file, 'w', encoding='utf-8') as f:
            json.dump(codegen_data, f, indent=2, ensure_ascii=False)
        
        return codegen_file
    except Exception as e:
        print(f"Warning: Could not save recording: {e}")
        return ""


def get_all_recorded_flows() -> List[Dict]:
    """
    Get all recorded flows.
    
    Returns:
        List of recorded flow dictionaries
    """
    ensure_recording_cache_dir()
    flows = []
    
    try:
        for filename in os.listdir(RECORDING_CACHE_DIR):
            if filename.endswith("_recording.json"):
                filepath = os.path.join(RECORDING_CACHE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        flow_data = json.load(f)
                        flows.append(flow_data)
                except Exception as e:
                    continue
    except Exception as e:
        pass
    
    # Sort by recorded date (newest first)
    flows.sort(key=lambda x: x.get("recorded_date", ""), reverse=True)
    return flows


def get_recorded_flow_for_test_case(test_case_id: str, ticket_id: str = None) -> Optional[Dict]:
    """
    Get recorded flow for a specific test case.
    
    Args:
        test_case_id: Test case ID (e.g., "TC-01")
        ticket_id: Optional ticket ID
        
    Returns:
        Recorded flow dict or None if not found
    """
    # Check codeGenerated folder first (where recordings are saved)
    from features.codeGenerator.generator import ensure_code_cache_dir
    ensure_code_cache_dir()
    
    codegen_dir = "codeGenerated"
    if os.path.exists(codegen_dir):
        # Search for recording files matching test case
        for filename in os.listdir(codegen_dir):
            if filename.endswith("_recording.json"):
                filepath = os.path.join(codegen_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        flow_data = json.load(f)
                        # Check if this recording matches the test case
                        if flow_data.get("test_case_id") == test_case_id:
                            if not ticket_id or flow_data.get("ticket_id") == ticket_id:
                                return flow_data
                except Exception:
                    continue
    
    return None


def has_recorded_flow(test_case_id: str, ticket_id: str = None) -> bool:
    """
    Check if a recorded flow exists for a test case.
    
    Args:
        test_case_id: Test case ID
        ticket_id: Optional ticket ID
        
    Returns:
        True if recorded flow exists, False otherwise
    """
    return get_recorded_flow_for_test_case(test_case_id, ticket_id) is not None


class BrowserRecorder:
    """Records browser interactions using Playwright's codegen-style recording"""
    
    def __init__(self):
        self.codegen_recorder: Optional[PlaywrightCodegenRecorder] = None
        self.actions: List[Dict] = []
        self.generated_code_python: str = ""
        self.generated_code_javascript: str = ""
        self.locators_python: str = ""
        self.locators_javascript: str = ""
        self.is_recording = False
        self.start_url = ""
        self.recorded_events: List[Dict] = []
    
    def start(self, url: str, headless: bool = False):
        """
        Start recording session using Playwright's codegen.
        
        Args:
            url: URL to navigate to
            headless: Whether to run browser in headless mode (False for codegen)
        """
        if self.is_recording:
            return
        
        # Use PlaywrightCodegenRecorder for actual codegen-style recording
        self.codegen_recorder = PlaywrightCodegenRecorder()
        self.codegen_recorder.start(url, headless)
        
        self.start_url = url
        self.is_recording = True
        self.actions = []
        self.recorded_events = []
        self.generated_code_python = ""
        self.generated_code_javascript = ""
    
    def _setup_playwright_recording_old(self):
        """Set up Playwright recording using CDP and JavaScript injection"""
        if not self.page:
            return
        
        # Use JavaScript to capture all interactions (similar to codegen)
        self.page.add_init_script("""
            window.__playwrightCodegen = {
                actions: [],
                getSelector: function(element) {
                    // Priority: data-testid > role > text > id > name > aria-label
                    if (element.getAttribute('data-testid')) {
                        return { type: 'testid', value: element.getAttribute('data-testid') };
                    }
                    if (element.getAttribute('role')) {
                        return { type: 'role', value: element.getAttribute('role'), name: element.textContent?.trim().substring(0, 30) };
                    }
                    const text = element.textContent?.trim();
                    if (text && text.length < 50) {
                        return { type: 'text', value: text };
                    }
                    if (element.id) {
                        return { type: 'id', value: element.id };
                    }
                    if (element.name) {
                        return { type: 'name', value: element.name };
                    }
                    if (element.getAttribute('aria-label')) {
                        return { type: 'aria-label', value: element.getAttribute('aria-label') };
                    }
                    return { type: 'tag', value: element.tagName.toLowerCase() };
                },
                recordAction: function(type, element, value) {
                    const selector = this.getSelector(element);
                    this.actions.push({
                        type: type,
                        selector: selector,
                        value: value || '',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            };
            
            // Record clicks
            document.addEventListener('click', function(e) {
                window.__playwrightCodegen.recordAction('click', e.target);
            }, true);
            
            // Record input/fill
            document.addEventListener('input', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                    window.__playwrightCodegen.recordAction('fill', e.target, e.target.value);
                }
            }, true);
            
            // Record form submissions
            document.addEventListener('submit', function(e) {
                window.__playwrightCodegen.recordAction('submit', e.target);
            }, true);
            
            // Record navigation - use multiple methods to catch all navigation
            let lastUrl = window.location.href;
            
            // Method 1: Listen to popstate (back/forward)
            window.addEventListener('popstate', function() {
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            });
            
            // Method 2: Listen to hashchange
            window.addEventListener('hashchange', function() {
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            });
            
            // Method 3: Monitor URL changes via MutationObserver
            const observer = new MutationObserver(function() {
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            
            // Method 4: Override pushState and replaceState to catch SPA navigation
            const originalPushState = history.pushState;
            const originalReplaceState = history.replaceState;
            history.pushState = function() {
                originalPushState.apply(history, arguments);
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            };
            history.replaceState = function() {
                originalReplaceState.apply(history, arguments);
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            };
            
            // Method 5: Periodic check for URL changes (fallback for SPA)
            setInterval(function() {
                if (window.location.href !== lastUrl) {
                    lastUrl = window.location.href;
                    window.__playwrightCodegen.actions.push({
                        type: 'navigate',
                        url: window.location.href,
                        timestamp: Date.now()
                    });
                }
            }, 500);
        """)
    
    
    def _collect_actions(self):
        """Collect recorded events from JavaScript and generate Playwright code"""
        if not self.page:
            return
        
        try:
            # Get recorded actions from JavaScript
            recorded_data = self.page.evaluate("window.__playwrightCodegen || { actions: [] }")
            actions = recorded_data.get("actions", [])
            
            # Convert to our format
            for action in actions:
                self.recorded_events.append(action)
                self.actions.append(action)
            
            # Always generate code, even if no actions (at least show the navigation)
            self._generate_playwright_code()
        except Exception as e:
            print(f"Warning: Could not collect actions: {e}")
            # Still try to generate code with what we have
            try:
                self._generate_playwright_code()
            except:
                pass
    
    def _generate_playwright_code(self):
        """Generate Playwright code from recorded events (similar to codegen)"""
        python_lines = []
        javascript_lines = []
        locators_python = []
        locators_javascript = []
        
        # Always include initial navigation
        if self.start_url:
            python_lines.append("from playwright.sync_api import Page, expect")
            python_lines.append("")
            python_lines.append("")
            python_lines.append("def test_recorded_flow(page: Page):")
            python_lines.append(f'    page.goto("{self.start_url}")')
            
            javascript_lines.append("const { test, expect } = require('@playwright/test');")
            javascript_lines.append("")
            javascript_lines.append("")
            javascript_lines.append("test('recorded flow', async ({ page }) => {")
            javascript_lines.append(f"  await page.goto('{self.start_url}');")
        
        # Extract unique locators
        locator_map = {}
        for event in self.recorded_events:
            selector_info = event.get("selector", {})
            if selector_info and isinstance(selector_info, dict):
                selector_type = selector_info.get("type", "")
                selector_value = selector_info.get("value", "")
                selector_name = selector_info.get("name", "")
                
                # Generate locator name
                if selector_type == "testid":
                    locator_name = selector_value.upper().replace("-", "_")
                    python_locator = f'    {locator_name} = "data-testid={selector_value}"'
                    js_locator = f'  {selector_value.replace("-", "")}: "data-testid={selector_value}",'
                elif selector_type == "id":
                    locator_name = selector_value.upper().replace("-", "_")
                    python_locator = f'    {locator_name} = "#{selector_value}"'
                    js_locator = f'  {selector_value.replace("-", "")}: "#{selector_value}",'
                elif selector_type == "name":
                    locator_name = selector_value.upper().replace("-", "_")
                    python_locator = f'    {locator_name} = "[name=\\"{selector_value}\\"]"'
                    js_locator = f'  {selector_value.replace("-", "")}: "[name=\\"{selector_value}\\"]",'
                else:
                    continue
                
                if locator_name not in locator_map:
                    locator_map[locator_name] = {
                        "python": python_locator,
                        "javascript": js_locator,
                        "selector_info": selector_info
                    }
        
        # Generate locators
        if locator_map:
            locators_python.append("class Locators:")
            for loc in locator_map.values():
                locators_python.append(loc["python"])
            
            locators_javascript.append("const locators = {")
            for loc in locator_map.values():
                locators_javascript.append(loc["javascript"])
            locators_javascript.append("};")
        else:
            # Add empty locators class if no locators found
            locators_python.append("class Locators:")
            locators_python.append("    # No locators recorded")
            locators_javascript.append("const locators = {")
            locators_javascript.append("  // No locators recorded")
            locators_javascript.append("};")
        
        # Process each recorded event
        for event in self.recorded_events:
            event_type = event.get("type", "")
            
            # Handle navigation events (they don't have selector_info)
            if event_type == "navigate":
                url = event.get("url", "")
                if url:  # Always record navigation
                    python_lines.append(f'    page.goto("{url}")')
                    javascript_lines.append(f"  await page.goto('{url}');")
                continue
            
            selector_info = event.get("selector", {})
            value = event.get("value", "")
            
            if not selector_info or not isinstance(selector_info, dict):
                continue
            
            selector_type = selector_info.get("type", "")
            selector_value = selector_info.get("value", "")
            selector_name = selector_info.get("name", "")
            
            # Generate Playwright code based on selector type
            if selector_type == "testid":
                py_selector = f'page.get_by_test_id("{selector_value}")'
                js_selector = f'page.getByTestId("{selector_value}")'
            elif selector_type == "role":
                role_name = f', name="{selector_name}"' if selector_name else ""
                py_selector = f'page.get_by_role("{selector_value}"{role_name})'
                js_selector = f'page.getByRole("{selector_value}"{role_name})'
            elif selector_type == "text":
                py_selector = f'page.get_by_text("{selector_value}")'
                js_selector = f'page.getByText("{selector_value}")'
            elif selector_type == "id":
                py_selector = f'page.locator("#{selector_value}")'
                js_selector = f'page.locator("#{selector_value}")'
            elif selector_type == "name":
                py_selector = f'page.locator("[name=\\"{selector_value}\\"]")'
                js_selector = f'page.locator("[name=\\"{selector_value}\\"]")'
            else:
                continue
            
            if event_type == "click":
                python_lines.append(f"    {py_selector}.click()")
                javascript_lines.append(f"  await {js_selector}.click();")
            elif event_type == "fill":
                escaped_value = value.replace('"', '\\"')
                python_lines.append(f'    {py_selector}.fill("{escaped_value}")')
                javascript_lines.append(f"  await {js_selector}.fill('{value}');")
        
        # Python code footer
        python_lines.append("")
        
        # JavaScript code footer
        javascript_lines.append("});")
        
        self.generated_code_python = "\n".join(python_lines)
        self.generated_code_javascript = "\n".join(javascript_lines)
        
        # Store locators separately
        self.locators_python = "\n".join(locators_python) if locators_python else ""
        self.locators_javascript = "\n".join(locators_javascript) if locators_javascript else ""
    
    def _get_selector(self, element) -> str:
        """
        Generate a robust selector for an element.
        Prioritizes data-testid, then other attributes.
        """
        try:
            # Try data-testid first
            test_id = element.get_attribute("data-testid")
            if test_id:
                return f"data-testid={test_id}"
            
            # Try id
            element_id = element.get_attribute("id")
            if element_id:
                return f"#{element_id}"
            
            # Try name
            name = element.get_attribute("name")
            if name:
                return f"[name='{name}']"
            
            # Try role
            role = element.get_attribute("role")
            if role:
                return f"[role='{role}']"
            
            # Try aria-label
            aria_label = element.get_attribute("aria-label")
            if aria_label:
                return f"[aria-label='{aria_label}']"
            
            # Fallback to text content
            text = element.text_content()
            if text and len(text.strip()) < 50:
                return f"text='{text.strip()}'"
            
            # Last resort: tag name
            tag = element.evaluate("el => el.tagName.toLowerCase()")
            return tag
            
        except Exception:
            return "unknown"
    
    def execute_flow(self, flow_steps: List[Dict]):
        """
        Execute a predefined flow of actions.
        This allows programmatic navigation through test cases.
        
        Args:
            flow_steps: List of action dictionaries with type, selector, and optional value
        """
        if not self.page or not self.is_recording:
            return
        
        for step in flow_steps:
            action_type = step.get("type")
            selector = step.get("selector")
            value = step.get("value", "")
            
            try:
                if action_type == "navigate":
                    self.page.goto(step.get("url", self.start_url), wait_until='networkidle')
                    time.sleep(1)  # Wait for page to settle
                elif action_type == "click":
                    self.page.locator(selector).click(timeout=10000)
                    time.sleep(0.5)  # Small delay between actions
                elif action_type == "fill":
                    self.page.locator(selector).fill(value)
                    time.sleep(0.3)
                elif action_type == "wait":
                    time.sleep(step.get("duration", 1))
                
                # Record the executed action
                action = {
                    "type": action_type,
                    "selector": selector,
                    "value": value,
                    "timestamp": time.time(),
                    "url": self.page.url,
                    "executed": True
                }
                self.actions.append(action)
                
            except Exception as e:
                # Continue with next action if one fails
                print(f"Warning: Failed to execute action: {e}")
                continue
    
    def stop(self):
        """Stop recording and close browser - with proper cleanup to prevent ghost processes"""
        self.is_recording = False
        
        # Stop codegen recorder and get generated code
        if self.codegen_recorder:
            try:
                result = self.codegen_recorder.stop()
                self.generated_code_python = result.get("python", "")
                self.generated_code_javascript = result.get("javascript", "")
                self.actions = result.get("actions", [])
                
                # Generate locators from actions
                self._extract_locators_from_actions()
            except Exception as e:
                print(f"Warning: Could not stop codegen recorder: {e}")
            
            # Close codegen recorder
            try:
                self.codegen_recorder.close()
            except Exception as e:
                print(f"Warning: Could not close codegen recorder: {e}")
            
            self.codegen_recorder = None
        
        # Force cleanup on Mac to prevent ghost processes
        import subprocess
        import platform
        if platform.system() == "Darwin":  # macOS
            try:
                # Kill any remaining Chromium/Chrome processes spawned by Playwright
                subprocess.run(
                    ["pkill", "-f", "chromium.*--remote-debugging"],
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass
    
    def get_actions(self) -> List[Dict]:
        """Get recorded actions"""
        # Collect actions if still recording
        if self.codegen_recorder and self.codegen_recorder.is_recording:
            try:
                # Actions are collected from codegen_recorder
                return self.actions.copy()
            except:
                pass
        return self.actions.copy()
    
    def _extract_locators_from_actions(self):
        """Extract locators from recorded actions and generate locator code"""
        locators_python = []
        locators_javascript = []
        seen_selectors = set()
        
        locators_python.append("class Locators:")
        locators_javascript.append("// Locators")
        
        for action in self.actions:
            selector_info = action.get("selector", {})
            if not isinstance(selector_info, dict):
                continue
            
            sel_type = selector_info.get("type", "")
            sel_value = selector_info.get("value", "")
            sel_name = selector_info.get("name", "")
            
            if not sel_value:
                continue
            
            # Create unique key for locator
            locator_key = f"{sel_type}_{sel_value}"
            if locator_key in seen_selectors:
                continue
            seen_selectors.add(locator_key)
            
            # Generate locator name
            locator_name = sel_value.replace("-", "_").replace(" ", "_").lower()
            if len(locator_name) > 30:
                locator_name = locator_name[:30]
            
            # Python locator
            if sel_type == "testid":
                py_loc = f'    {locator_name} = page.get_by_test_id("{sel_value}")'
                js_loc = f"const {locator_name} = page.getByTestId('{sel_value}');"
            elif sel_type == "role":
                if sel_name:
                    py_loc = f'    {locator_name} = page.get_by_role("{sel_value}", name="{sel_name}")'
                    js_loc = f"const {locator_name} = page.getByRole('{sel_value}', {{ name: '{sel_name}' }});"
                else:
                    py_loc = f'    {locator_name} = page.get_by_role("{sel_value}")'
                    js_loc = f"const {locator_name} = page.getByRole('{sel_value}');"
            elif sel_type == "text":
                py_loc = f'    {locator_name} = page.get_by_text("{sel_value}")'
                js_loc = f"const {locator_name} = page.getByText('{sel_value}');"
            elif sel_type == "id":
                py_loc = f'    {locator_name} = page.locator("#{sel_value}")'
                js_loc = f"const {locator_name} = page.locator('#{sel_value}');"
            elif sel_type == "name":
                py_loc = f'    {locator_name} = page.locator("[name=\\"{sel_value}\\"]")'
                js_loc = f"const {locator_name} = page.locator('[name=\"{sel_value}\"]');"
            else:
                continue
            
            locators_python.append(py_loc)
            locators_javascript.append(js_loc)
        
        if len(locators_python) == 1:
            locators_python.append("    # No locators recorded")
        
        self.locators_python = "\n".join(locators_python)
        self.locators_javascript = "\n".join(locators_javascript)
    
    def get_generated_code(self):
        """Get generated Playwright code"""
        return {
            "python": self.generated_code_python,
            "javascript": self.generated_code_javascript,
            "locators_python": self.locators_python,
            "locators_javascript": self.locators_javascript
        }


# Global recorder instance
_recorder_instance: Optional[BrowserRecorder] = None


def kill_ghost_processes():
    """Kill any ghost Playwright/Chromium processes on Mac"""
    import subprocess
    import platform
    
    if platform.system() == "Darwin":  # macOS
        try:
            # Kill Chromium processes with remote debugging
            subprocess.run(
                ["pkill", "-f", "chromium.*--remote-debugging"],
                capture_output=True,
                timeout=5
            )
            subprocess.run(
                ["pkill", "-f", "chromium.*--user-data-dir"],
                capture_output=True,
                timeout=5
            )
            # Also kill Chrome processes that might be spawned
            subprocess.run(
                ["pkill", "-f", "Google Chrome.*--remote-debugging"],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass


def start_recording_session(url: str, headless: bool = True) -> BrowserRecorder:
    """
    Start a new recording session.
    
    Args:
        url: URL to start recording from
        headless: Whether to run browser in headless mode
        
    Returns:
        BrowserRecorder instance
    """
    global _recorder_instance
    
    # Kill any ghost processes first
    kill_ghost_processes()
    
    # Stop existing session if any
    if _recorder_instance:
        try:
            _recorder_instance.stop()
        except Exception:
            pass
        _recorder_instance = None
    
    _recorder_instance = BrowserRecorder()
    try:
        _recorder_instance.start(url, headless)
    except Exception as e:
        # If start fails, clean up
        if _recorder_instance:
            try:
                _recorder_instance.stop()
            except:
                pass
            _recorder_instance = None
        raise e
    
    return _recorder_instance


def stop_recording_session() -> Optional[Dict[str, str]]:
    """Stop the current recording session and return generated code"""
    global _recorder_instance
    generated_code = None
    if _recorder_instance:
        # Generate code before stopping (stop() calls _collect_actions which generates code)
        # Get generated code before clearing instance
        try:
            generated_code = _recorder_instance.get_generated_code()
        except:
            pass
        _recorder_instance.stop()
        _recorder_instance = None
    return generated_code


def get_recorded_actions() -> List[Dict]:
    """Get actions from current recording session"""
    global _recorder_instance
    if _recorder_instance:
        return _recorder_instance.get_actions()
    return []


def get_generated_playwright_code() -> Dict[str, str]:
    """Get generated Playwright code from current recording session"""
    global _recorder_instance
    if _recorder_instance:
        return _recorder_instance.get_generated_code()
    return {
        "python": "",
        "javascript": "",
        "locators_python": "",
        "locators_javascript": ""
    }


def convert_actions_to_test_steps(actions: List[Dict]) -> List[str]:
    """
    Convert recorded actions to human-readable test steps.
    
    Args:
        actions: List of action dictionaries
        
    Returns:
        List of test step strings
    """
    steps = []
    step_num = 1
    
    for action in actions:
        action_type = action.get("type")
        selector = action.get("selector", "")
        value = action.get("value", "")
        
        if action_type == "navigate":
            url = action.get("url", "")
            steps.append(f"{step_num}. Navigate to {url}")
            step_num += 1
        elif action_type == "click":
            # Try to make selector more readable
            readable_selector = _make_selector_readable(selector)
            steps.append(f"{step_num}. Click on {readable_selector}")
            step_num += 1
        elif action_type == "fill":
            readable_selector = _make_selector_readable(selector)
            steps.append(f"{step_num}. Enter '{value}' in {readable_selector}")
            step_num += 1
        elif action_type == "keypress":
            key = action.get("key", "")
            steps.append(f"{step_num}. Press {key} key")
            step_num += 1
    
    return steps


def _make_selector_readable(selector: str) -> str:
    """Convert selector to more readable format"""
    if not selector:
        return "element"
    
    # Extract meaningful part from selector
    if selector.startswith("data-testid="):
        return selector.replace("data-testid=", "")
    elif selector.startswith("#"):
        return f"element with id '{selector[1:]}'"
    elif selector.startswith("[name='"):
        name = selector.replace("[name='", "").replace("']", "")
        return f"field '{name}'"
    elif selector.startswith("text='"):
        text = selector.replace("text='", "").replace("'", "")
        return f"'{text}'"
    else:
        return selector

