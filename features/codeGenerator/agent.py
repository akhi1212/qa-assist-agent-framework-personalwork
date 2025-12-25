"""
Code Generation Agents
"""
import os
import yaml

def _create_llm_instance(model: str, provider: str = None):
    """Create LLM instance from model string"""
    # Normalize provider name
    if provider:
        provider = provider.lower()
    
    # Determine provider from parameter, environment variables, or model name
    if not provider:
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("OPENROUTER_API_KEY"):
            provider = "openrouter"
        elif "gpt" in model.lower() or "openai" in model.lower():
            provider = "openai"
        elif "claude" in model.lower() or "anthropic" in model.lower():
            provider = "anthropic"
        elif "openrouter" in model.lower():
            provider = "openrouter"
    
    try:
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model, temperature=0)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model, temperature=0)
        elif provider == "openrouter":
            from langchain_openai import ChatOpenAI
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment")
            return ChatOpenAI(
                model=model,
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                temperature=0
            )
    except ImportError as e:
        raise ImportError(f"Required langchain package not installed: {e}")
    
    # Fallback: try OpenAI as default
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0)
    except Exception as e:
        raise ValueError(f"Could not create LLM instance for model: {model}, provider: {provider}. Error: {e}")

def create_code_generator_agent(model: str, provider: str = None):
    """Create agent that generates Playwright code"""
    from crewai import Agent
    
    yaml_path = os.path.join(os.path.dirname(__file__), 'agent.yaml')
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)['code_generator']
    
    # Create LLM instance (required for .bind() method)
    llm = _create_llm_instance(model, provider)
    
    # Create agent with memory=False to disable ConversationSummaryMemory
    return Agent(
        role=config['role'],
        goal=config['goal'],
        backstory=config['backstory'],
        llm=llm,
        allow_delegation=config.get('allow_delegation', False),
        verbose=config.get('verbose', True),
        memory=False  # Must be False (boolean) to disable memory
    )

