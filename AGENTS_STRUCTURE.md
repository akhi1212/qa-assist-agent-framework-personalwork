# Agents and Tasks Structure

## Overview
Clean, organized structure for all AI agents and their tasks using YAML configuration files.

**Note**: The Key Validator Agent is kept for future use. Currently, API key validation uses direct API calls to avoid Python 3.14 compatibility issues during startup validation.

## Folder Structure
```
├── agents/
│   ├── __init__.py
│   ├── key_validator_agent.py       # Agent implementation (for future use)
│   └── key_validator_agent.yaml     # Agent configuration
└── tasks/
    ├── __init__.py
    ├── key_validation_task.py       # Task implementation (for future use)
    └── key_validation_task.yaml     # Task configuration
```

## Current Implementation

### API Key Validation
Currently, API key validation is done via **direct API calls** in `app.py` to avoid Python 3.14 compatibility issues:
- **OpenAI**: Makes a simple completion request
- **Anthropic**: Makes a simple message request  
- **OpenRouter**: Makes a simple API request

This approach is faster and more reliable for simple validation.

### Agent-Based Validation (Available for Future Use)
The Key Validator Agent and Task are available for more complex validation scenarios where AI reasoning is needed.

## Why YAML Configuration Files?

YAML files provide several benefits:
- ✅ **Separation of concerns**: Configuration separate from code
- ✅ **Easy to modify**: Change agent behavior without touching Python code
- ✅ **Version control friendly**: Clear diffs when configs change
- ✅ **Standard practice**: Follows CrewAI best practices
- ✅ **Maintainable**: Non-developers can update agent prompts

## Current Agents

### 1. Key Validator Agent
**Implementation**: `agents/key_validator_agent.py`
**Configuration**: `agents/key_validator_agent.yaml`

**Purpose**: Validates that API keys are working correctly

**YAML Configuration**:
```yaml
key_validator:
  role: "API Key Validator"
  goal: "Validate that the provided API key is working correctly"
  backstory: |
    You are an expert system administrator who validates API credentials 
    and ensures proper authentication.
  verbose: true
  allow_delegation: false
```

**Python Usage**:
```python
from agents.key_validator_agent import create_key_validator_agent
agent = create_key_validator_agent(model="gpt-4o-mini")
```

## Current Tasks

### 1. Key Validation Task
**Implementation**: `tasks/key_validation_task.py`
**Configuration**: `tasks/key_validation_task.yaml`

**Purpose**: Creates validation task for API keys

**YAML Configuration**:
```yaml
validate_api_key:
  description: |
    Validate that the {provider} API key is working correctly.
    
    You should respond with ONLY one of these exact messages:
    - "VALID" if the key is working
    - "INVALID" if the key is not working
    
    Keep your response to just that one word.
  expected_output: "A single word: VALID or INVALID"
```

**Python Usage**:
```python
from tasks.key_validation_task import create_key_validation_task
task = create_key_validation_task(agent, provider="OpenAI")
```

## How to Add New Agents

### Step 1: Create YAML Configuration
Create `agents/your_agent_name.yaml`:
```yaml
your_agent:
  role: "Your Agent Role"
  goal: "What the agent should achieve"
  backstory: |
    Detailed background about the agent and its expertise.
  verbose: true
  allow_delegation: false
```

### Step 2: Create Python Implementation
Create `agents/your_agent_name.py`:
```python
"""
Your Agent Name
---------------
Brief description of what this agent does.

Configuration is loaded from your_agent_name.yaml
"""

import os
import yaml

def create_your_agent(model: str):
    """
    Creates your agent.
    
    Args:
        model (str): The LLM model to use
        
    Returns:
        Agent: Your agent instance
    """
    from crewai import Agent
    
    # Load configuration from YAML
    yaml_path = os.path.join(os.path.dirname(__file__), 'your_agent_name.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)
    
    agent_config = config['your_agent']
    
    return Agent(
        role=agent_config['role'],
        goal=agent_config['goal'],
        backstory=agent_config['backstory'],
        llm=model,
        verbose=agent_config.get('verbose', True),
        allow_delegation=agent_config.get('allow_delegation', False)
    )
```

## How to Add New Tasks

### Step 1: Create YAML Configuration
Create `tasks/your_task_name.yaml`:
```yaml
your_task:
  description: |
    Detailed description of what the task should do.
    You can use {variables} for dynamic content.
  expected_output: "Description of expected output format"
```

### Step 2: Create Python Implementation
Create `tasks/your_task_name.py`:
```python
"""
Your Task Name
--------------
Brief description of what this task does.

Configuration is loaded from your_task_name.yaml
"""

import os
import yaml

def create_your_task(agent, **kwargs):
    """
    Creates your task.
    
    Args:
        agent: The agent to assign this task to
        **kwargs: Variables to format in the description
        
    Returns:
        Task: Your task instance
    """
    from crewai import Task
    
    # Load configuration from YAML
    yaml_path = os.path.join(os.path.dirname(__file__), 'your_task_name.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)
    
    task_config = config['your_task']
    
    # Format description with variables
    description = task_config['description'].format(**kwargs)
    
    return Task(
        description=description,
        expected_output=task_config['expected_output'],
        agent=agent
    )
```

## Integration in app.py

All agents and tasks are loaded dynamically from YAML:
```python
from agents.key_validator_agent import create_key_validator_agent
from tasks.key_validation_task import create_key_validation_task

# Creates agent with YAML config
agent = create_key_validator_agent(model)

# Creates task with YAML config
task = create_key_validation_task(agent, provider="OpenAI")
```

## Benefits of This Structure

1. **Configuration separate from code**: Easy to update prompts without touching Python
2. **Type safety**: Python functions provide type hints and validation
3. **Lazy loading**: CrewAI imported only when needed (Python 3.14 compatibility)
4. **Scalable**: Easy to add new agents/tasks
5. **Maintainable**: Clear separation of concerns
6. **Standard practice**: Follows CrewAI documentation recommendations

