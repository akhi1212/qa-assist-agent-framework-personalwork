"""
Jira Validator Agent
"""
import os
import yaml

def create_jira_validator_agent(model: str):
    """Create agent that validates Jira credentials"""
    from crewai import Agent
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'agent.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['jira_validator']
    
    return Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        llm=model,
        verbose=config.get('verbose', True)
    )

