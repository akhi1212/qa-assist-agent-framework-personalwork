"""
Code Generation Feature
-----------------------
Agent and task for generating Playwright code from test cases.
"""
from .agent import (
    create_code_generator_agent
)
from .task import (
    create_generate_playwright_code_task
)
from .generator import (
    generate_playwright_code,
    handle_generate_code,
    format_code_for_display,
    parse_code_json,
    save_code_to_cache,
    load_cached_code,
    get_all_cached_codes,
    get_code_history_table_data
)

__all__ = [
    # Agent creation functions
    'create_code_generator_agent',
    # Task creation functions
    'create_generate_playwright_code_task',
    # Core generation functions
    'generate_playwright_code',
    'handle_generate_code',
    'format_code_for_display',
    'parse_code_json',
    # Cache functions
    'save_code_to_cache',
    'load_cached_code',
    'get_all_cached_codes',
    'get_code_history_table_data',
]

