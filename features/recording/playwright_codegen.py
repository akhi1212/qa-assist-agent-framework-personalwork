"""
Playwright Codegen Integration
Uses Playwright's actual codegen command via subprocess
"""
import json
import os
import subprocess
import tempfile
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class PlaywrightCodegenRecorder:
    """Records browser interactions using Playwright's actual codegen command"""
    
    def __init__(self):
        self.codegen_process: Optional[subprocess.Popen] = None
        self.is_recording = False
        self.start_url = ""
        self.generated_python_code: str = ""
        self.generated_javascript_code: str = ""
        self.recorded_actions: List[Dict] = []
        self.output_dir: Optional[str] = None
        self.python_output_file: Optional[str] = None
        self.js_output_file: Optional[str] = None
    
    def start(self, url: str, headless: bool = False):
        """Start recording session using Playwright's codegen command"""
        if self.is_recording:
            return
        
        self.start_url = url
        self.is_recording = True
        self.generated_python_code = ""
        self.generated_javascript_code = ""
        self.recorded_actions = []
        
        # Create temporary directory for output files
        self.output_dir = tempfile.mkdtemp(prefix="playwright_codegen_")
        self.python_output_file = os.path.join(self.output_dir, "recordedflow.py")
        self.js_output_file = os.path.join(self.output_dir, "recordedflow.js")
        
        # Build codegen command
        # Playwright codegen opens a browser and records interactions
        # Use --target python to generate Python code
        cmd = [
            "npx", 
            "playwright", 
            "codegen",
            url,
            "--target", "python",
            "--output", self.python_output_file
        ]
        
        try:
            # Start codegen process
            # IMPORTANT: Don't capture stdout/stderr - let it run in foreground so browser can open
            # Use shell=True on Windows/Mac to ensure proper process handling
            import sys
            import platform
            
            if platform.system() == "Windows":
                # Windows: use CREATE_NEW_CONSOLE to allow browser to open
                self.codegen_process = subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
            else:
                # Mac/Linux: Run directly without capturing output
                # This allows the browser window to open properly
                # Don't use both preexec_fn and start_new_session - they conflict
                self.codegen_process = subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    stdout=None,  # Don't capture - allows browser to open
                    stderr=None,  # Don't capture - allows browser to open
                    start_new_session=True  # Create new session (don't use preexec_fn with this)
                )
            
            # Give it a moment to start and open browser
            time.sleep(3)
            
            # Check if process is still running
            if self.codegen_process.poll() is not None:
                # Process ended immediately (error)
                raise Exception("Codegen process exited immediately. Check if Playwright is installed: npx playwright install")
            
        except FileNotFoundError:
            raise Exception("Playwright not found. Please install: npm install -g playwright && npx playwright install")
        except Exception as e:
            raise Exception(f"Failed to start codegen: {str(e)}")
    
    def stop(self) -> Dict[str, str]:
        """Stop recording and read generated code"""
        self.is_recording = False
        
        # Terminate codegen process
        # When codegen's browser is closed, it automatically saves the code and exits
        if self.codegen_process:
            try:
                # Try graceful termination first
                if os.name == 'nt':
                    # Windows: use taskkill to close the browser
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.codegen_process.pid)], 
                                     timeout=3, capture_output=True)
                    except:
                        self.codegen_process.terminate()
                else:
                    # Unix/Mac: send SIGTERM
                    self.codegen_process.terminate()
                
                # Wait for process to finish (codegen saves code when browser closes)
                try:
                    self.codegen_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop
                    self.codegen_process.kill()
                    self.codegen_process.wait()
                
            except Exception as e:
                print(f"Warning: Error stopping codegen process: {e}")
                try:
                    self.codegen_process.kill()
                except:
                    pass
        
        # Wait for codegen to save the file (it saves when browser closes)
        # Check multiple times as the file might be written asynchronously
        max_attempts = 10
        file_found = False
        for attempt in range(max_attempts):
            if self.python_output_file and os.path.exists(self.python_output_file):
                # Check if file has content (not just created empty)
                try:
                    with open(self.python_output_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # File has content
                            self.generated_python_code = content
                            file_found = True
                            break
                except:
                    pass
            time.sleep(0.5)  # Wait 0.5 seconds between checks
        
        if not file_found:
            # File might not exist or is empty - check if codegen saved it elsewhere
            # Codegen might save to current directory if output path fails
            possible_paths = [
                self.python_output_file,
                os.path.join(os.getcwd(), "recordedflow.py"),
                os.path.join(self.output_dir, "recordedflow.py") if self.output_dir else None
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                self.generated_python_code = content
                                file_found = True
                                break
                    except:
                        continue
            
            if not file_found:
                # Generate basic code with just navigation
                self.generated_python_code = f"""from playwright.sync_api import Page, expect

def test(page: Page):
    page.goto("{self.start_url}")
"""
                print(f"Warning: Codegen output file not found. Expected at: {self.python_output_file}")
        
        # Generate JavaScript version from Python code (or read if exists)
        if self.js_output_file and os.path.exists(self.js_output_file):
            try:
                with open(self.js_output_file, 'r', encoding='utf-8') as f:
                    self.generated_javascript_code = f.read()
            except Exception as e:
                print(f"Warning: Could not read JavaScript output: {e}")
        else:
            # Convert Python to JavaScript if needed
            self.generated_javascript_code = self._convert_python_to_javascript(self.generated_python_code)
        
        # Extract actions from generated code for JSON storage
        self._extract_actions_from_code()
        
        return {
            "python": self.generated_python_code,
            "javascript": self.generated_javascript_code,
            "actions": self.recorded_actions
        }
    
    def _convert_python_to_javascript(self, python_code: str) -> str:
        """Convert Python Playwright code to JavaScript"""
        if not python_code:
            return "const { test, expect } = require('@playwright/test');\n\ntest('test', async ({ page }) => {\n});"
        
        # Simple conversion (basic patterns)
        js_code = python_code
        
        # Replace Python imports
        js_code = js_code.replace("from playwright.sync_api import Page, expect", 
                                  "const { test, expect } = require('@playwright/test');")
        
        # Replace function definition
        js_code = js_code.replace("def test(page: Page):", "test('test', async ({ page }) => {")
        
        # Replace Python syntax with JavaScript
        js_code = js_code.replace("page.goto(", "await page.goto(")
        js_code = js_code.replace(".click()", ".click();")
        js_code = js_code.replace(".fill(", ".fill(")
        js_code = js_code.replace(".press(", ".press(")
        
        # Add await to async operations
        lines = js_code.split('\n')
        js_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('page.') and not stripped.startswith('await'):
                # Add await
                indent = len(line) - len(line.lstrip())
                js_lines.append(' ' * indent + 'await ' + stripped + ';')
            else:
                js_lines.append(line)
        
        # Close the test function
        if not js_code.strip().endswith('});'):
            js_lines.append("});")
        
        return '\n'.join(js_lines)
    
    def _extract_actions_from_code(self):
        """Extract actions from generated code for JSON storage"""
        if not self.generated_python_code:
            # At least record the initial navigation
            self.recorded_actions.append({
                "type": "navigate",
                "url": self.start_url,
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Parse the generated code to extract actions
        lines = self.generated_python_code.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract navigation
            if 'page.goto(' in line or 'page.goto(' in line:
                try:
                    # Extract URL from goto - handle both single and double quotes
                    for quote in ['"', "'"]:
                        pattern = f'page.goto({quote}'
                        if pattern in line:
                            start = line.find(pattern) + len(pattern)
                            end = line.find(quote, start)
                            if end > start:
                                url = line[start:end]
                                self.recorded_actions.append({
                                    "type": "navigate",
                                    "url": url,
                                    "timestamp": datetime.now().isoformat()
                                })
                                break
                except Exception as e:
                    print(f"Warning: Could not extract navigation: {e}")
            
            # Extract clicks
            elif '.click()' in line:
                try:
                    selector_info = None
                    # Check for different selector types
                    if 'get_by_test_id(' in line:
                        start = line.find('get_by_test_id("') + len('get_by_test_id("')
                        if start < len('get_by_test_id("'):
                            start = line.find("get_by_test_id('") + len("get_by_test_id('")
                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                        if end > start:
                            selector = line[start:end]
                            selector_info = {"type": "testid", "value": selector}
                    elif 'get_by_role(' in line:
                        # Extract role
                        start = line.find('get_by_role("') + len('get_by_role("')
                        if start < len('get_by_role("'):
                            start = line.find("get_by_role('") + len("get_by_role('")
                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                        if end > start:
                            role = line[start:end]
                            selector_info = {"type": "role", "value": role}
                    elif 'locator(' in line:
                        start = line.find('locator("') + len('locator("')
                        if start < len('locator("'):
                            start = line.find("locator('") + len("locator('")
                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                        if end > start:
                            selector = line[start:end]
                            selector_info = {"type": "css", "value": selector}
                    
                    if selector_info:
                        self.recorded_actions.append({
                            "type": "click",
                            "selector": selector_info,
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    print(f"Warning: Could not extract click: {e}")
            
            # Extract fills
            elif '.fill(' in line:
                try:
                    selector_info = None
                    value = ""
                    
                    # Extract selector
                    if 'get_by_test_id(' in line:
                        start = line.find('get_by_test_id("') + len('get_by_test_id("')
                        if start < len('get_by_test_id("'):
                            start = line.find("get_by_test_id('") + len("get_by_test_id('")
                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                        if end > start:
                            selector = line[start:end]
                            selector_info = {"type": "testid", "value": selector}
                    elif 'locator(' in line:
                        start = line.find('locator("') + len('locator("')
                        if start < len('locator("'):
                            start = line.find("locator('") + len("locator('")
                        end = line.find('"', start) if '"' in line[start:] else line.find("'", start)
                        if end > start:
                            selector = line[start:end]
                            selector_info = {"type": "css", "value": selector}
                    
                    # Extract value
                    fill_patterns = ['.fill("', ".fill('"]
                    for pattern in fill_patterns:
                        if pattern in line:
                            value_start = line.find(pattern) + len(pattern)
                            quote = pattern[-1]
                            value_end = line.find(quote, value_start)
                            if value_end > value_start:
                                value = line[value_start:value_end]
                                break
                    
                    if selector_info:
                        self.recorded_actions.append({
                            "type": "fill",
                            "selector": selector_info,
                            "value": value,
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    print(f"Warning: Could not extract fill: {e}")
        
        # If no actions found, at least record the initial navigation
        if not self.recorded_actions:
            self.recorded_actions.append({
                "type": "navigate",
                "url": self.start_url,
                "timestamp": datetime.now().isoformat()
            })
    
    def close(self):
        """Close browser and cleanup"""
        # Stop the process if still running
        if self.codegen_process:
            try:
                self.codegen_process.terminate()
                try:
                    self.codegen_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.codegen_process.kill()
            except:
                pass
            self.codegen_process = None
        
        # Cleanup output directory (optional - you might want to keep the files)
        # if self.output_dir and os.path.exists(self.output_dir):
        #     try:
        #         import shutil
        #         shutil.rmtree(self.output_dir)
        #     except:
        #         pass
