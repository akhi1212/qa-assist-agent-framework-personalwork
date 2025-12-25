"""
Test Case Generation Feature
-----------------------------
Agent and task for generating test cases from feature descriptions.
"""
from .agent import (
    create_test_case_validator_agent,
    create_test_case_generator_agent
)
from .task import (
    create_validate_jira_story_task,
    create_generate_test_cases_task
)
from .generator import (
    generate_test_cases,
    generate_test_cases_with_additional_info,
    regenerate_test_cases_with_feedback,
    handle_generate_test_cases,
    handle_regenerate_test_cases,
    prepare_regeneration_prompt,
    export_test_cases_to_csv,
    export_test_cases_to_excel,
    save_ticket_to_history,
    get_ticket_history_entry,
    update_ticket_in_history,
    clear_ticket_history,
    get_ticket_history_table_data
)

__all__ = [
    # Agent creation functions
    'create_test_case_validator_agent',
    'create_test_case_generator_agent',
    # Task creation functions
    'create_validate_jira_story_task',
    'create_generate_test_cases_task',
    # Core generation functions
    'generate_test_cases',
    'generate_test_cases_with_additional_info',
    'regenerate_test_cases_with_feedback',
    'handle_generate_test_cases',
    'handle_regenerate_test_cases',
    'prepare_regeneration_prompt',
    # Export functions
    'export_test_cases_to_csv',
    'export_test_cases_to_excel',
    # Ticket history management
    'save_ticket_to_history',
    'get_ticket_history_entry',
    'update_ticket_in_history',
    'clear_ticket_history',
    'get_ticket_history_table_data',
]

