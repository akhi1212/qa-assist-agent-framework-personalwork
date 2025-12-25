"""
LLM Key Validation Task
"""
import os
import yaml

def create_key_validation_task(agent, provider: str):
    """Create task for validating API keys"""
    from crewai import Task
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'task.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['validate_api_key']
    
    description = config['description'].format(provider=provider)
    
    return Task(
        description=description,
        expected_output=config['expected_output'],
        agent=agent
    )

