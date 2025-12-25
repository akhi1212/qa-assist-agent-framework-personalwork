"""
LLM Key Validator Agent
"""
import os
import yaml

def create_key_validator_agent(model: str):
    """Create agent that validates API keys"""
    from crewai import Agent
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'agent.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['key_validator']
    
    return Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        llm=model,
        verbose=config.get('verbose', True),
        allow_delegation=config.get('allow_delegation', False)
    )

