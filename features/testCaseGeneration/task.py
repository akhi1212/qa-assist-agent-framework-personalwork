"""
Test Case Generation Tasks
"""
import os
import yaml

def create_validate_jira_story_task(agent, jira_key: str, jira_project: str, jira_summary: str, jira_description: str):
    """Create task for validating Jira story"""
    from crewai import Task
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'task.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['validate_jira_story']
    
    description = config['description'].format(
        jira_key=jira_key,
        jira_project=jira_project,
        jira_summary=jira_summary,
        jira_description=jira_description
    )
    
    return Task(
        description=description,
        expected_output=config['expected_output'],
        agent=agent,
        output_file=config.get('output_file')
    )


def create_generate_test_cases_task(agent, validation_task):
    """Create task for generating test cases based on validation result"""
    from crewai import Task
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'task.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['generate_test_cases']
    
    # Don't format the description - CrewAI will handle {validate_jira_story.output} template
    # when context is set
    description = config['description']
    
    return Task(
        description=description,
        expected_output=config['expected_output'],
        agent=agent,
        context=[validation_task],
        output_file=config.get('output_file')
    )
