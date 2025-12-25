"""
Jira Validation Task
"""
import os
import yaml

def create_jira_validation_task(agent, jira_email: str):
    """Create task for validating Jira credentials"""
    from crewai import Task
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'task.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['validate_jira_credentials']
    
    description = config['description'].format(jira_email=jira_email)
    
    return Task(
        description=description,
        expected_output=config['expected_output'],
        agent=agent
    )

