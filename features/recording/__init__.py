"""
Browser Recording Feature
-------------------------
Records user flows in the browser and generates Playwright code.
"""
from .recorder import (
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

__all__ = [
    'start_recording_session',
    'stop_recording_session',
    'get_recorded_actions',
    'get_generated_playwright_code',
    'convert_actions_to_test_steps',
    'save_recorded_flow',
    'load_recorded_flow',
    'get_all_recorded_flows',
    'get_recorded_flow_for_test_case',
    'has_recorded_flow',
    'kill_ghost_processes',
]

