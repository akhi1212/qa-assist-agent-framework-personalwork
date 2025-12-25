# QA Assist - Architecture & Technical Overview

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Agents & Tasks](#agents--tasks)
4. [Technology Stack](#technology-stack)
5. [Data Flow](#data-flow)
6. [Key Features](#key-features)
7. [Code Structure](#code-structure)

---

## System Overview

**QA Assist** is an AI-powered test automation platform that:
- Generates test cases from Jira tickets using LLMs
- Records browser interactions using Playwright
- Generates production-ready Playwright automation code
- Follows Page Object Model (POM) and DRY principles

### Core Philosophy
- **Agent-Based Architecture**: Uses CrewAI framework for orchestrated AI agents
- **YAML Configuration**: Separates prompts/config from code for easy updates
- **Modular Design**: Feature-based organization for scalability
- **Production-Ready Code**: Generates maintainable, reusable automation code

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                       │
│  (User Interface - app.py)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Feature Modules                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Test Case    │  │ Code         │  │ Recording    │     │
│  │ Generation   │  │ Generator    │  │ Module       │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
└─────────┼─────────────────┼──────────────────┼──────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              CrewAI Agent Framework                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Validator    │  │ Generator    │  │ Code Gen     │     │
│  │ Agent        │  │ Agent        │  │ Agent        │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         ▼                 ▼                  ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Validation   │  │ Test Case    │  │ Code Gen     │     │
│  │ Task         │  │ Task         │  │ Task         │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Providers (OpenAI/Anthropic/OpenRouter)   │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│  • Jira API (Test Case Source)                              │
│  • Playwright (Browser Automation)                           │
│  • ChromaDB (Vector Storage)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Agents & Tasks

### Overview
The system uses **CrewAI** framework with **5 specialized agents** and **5 corresponding tasks**.

### 1. Test Case Generation Module

#### Agents (2)

**1.1 Test Case Validator Agent**
- **Role**: Jira QA Story Validator
- **Goal**: Determine if a Jira ticket is valid for test case generation
- **Backstory**: Senior QA lead with strict requirements for clear acceptance criteria
- **File**: `features/testCaseGeneration/agent.yaml` → `test_case_validator`
- **Configuration**: YAML-based, allows easy prompt updates

**1.2 Test Case Generator Agent**
- **Role**: QA Test Case Designer
- **Goal**: Generate high-quality manual test cases with steps and expected results
- **Backstory**: Senior QA engineer with 10+ years experience
- **File**: `features/testCaseGeneration/agent.yaml` → `test_case_generator`
- **Output**: JSON with test cases (TC-01, TC-02, etc.)

#### Tasks (2)

**1.1 Validate Jira Story Task**
- **Agent**: `test_case_validator`
- **Purpose**: Validate Jira ticket before generating test cases
- **Output**: JSON with status (`invalid`, `needs_more_info`, `ready`)
- **File**: `features/testCaseGeneration/task.yaml` → `validate_jira_story`
- **Key Logic**:
  - Checks if ticket is QA/testing related
  - Validates if enough information exists
  - Returns structured JSON with questions if needed

**1.2 Generate Test Cases Task**
- **Agent**: `test_case_generator`
- **Context**: Depends on validation task output
- **Purpose**: Generate 6-15 test cases covering:
  - Happy-path scenarios
  - Negative scenarios
  - Boundary/edge cases
  - Error handling
- **File**: `features/testCaseGeneration/task.yaml` → `generate_test_cases`
- **Output**: JSON with test cases array

---

### 2. Code Generator Module

#### Agent (1)

**2.1 Code Generator Agent**
- **Role**: Playwright Code Generator
- **Goal**: Generate production-ready Playwright code in Python & JavaScript
- **Backstory**: Senior automation engineer with 10+ years Playwright experience
- **File**: `features/codeGenerator/agent.yaml` → `code_generator`
- **Specialization**: POM pattern, DRY principles, best practices

#### Task (1)

**2.1 Generate Playwright Code Task**
- **Agent**: `code_generator`
- **Purpose**: Convert test cases to Playwright automation code
- **File**: `features/codeGenerator/task.yaml` → `generate_playwright_code`
- **Key Features**:
  - Accepts recorded browser flows (from Playwright codegen)
  - Extracts locators from actual codegen output
  - Generates both Python and JavaScript
  - Follows strict formatting requirements:
    - Async functions with type hints
    - Comprehensive docstrings
    - Try-except blocks
    - Logger statements
- **Output**: JSON with:
  - Locators (Python & JavaScript)
  - Reusable functions
  - Test-specific functions
  - Cursor AI prompt

---

### 3. Jira Validation Module

#### Agent (1)

**3.1 Jira Validator Agent**
- **Role**: Jira Ticket Validator
- **Purpose**: Validate Jira credentials and ticket accessibility
- **File**: `features/jiraValidation/agent.yaml`
- **Note**: Currently uses direct API calls, agent available for future use

#### Task (1)

**3.1 Jira Validation Task**
- **Agent**: `jira_validator`
- **Purpose**: Validate Jira connection and ticket retrieval
- **File**: `features/jiraValidation/task.yaml`

---

### 4. LLM Key Validation Module

#### Agent (1)

**4.1 LLM Key Validator Agent**
- **Role**: API Key Validator
- **Purpose**: Validate LLM provider API keys
- **File**: `features/llmKeyValidation/agent.yaml`
- **Note**: Currently uses direct API calls for faster validation

#### Task (1)

**4.1 Key Validation Task**
- **Agent**: `llm_key_validator`
- **Purpose**: Validate API keys for OpenAI, Anthropic, OpenRouter
- **File**: `features/llmKeyValidation/task.yaml`

---

### 5. Recording Module (No Agents)

**Purpose**: Browser interaction recording using Playwright
- **File**: `features/recording/playwright_codegen.py`
- **Functionality**:
  - Launches Playwright codegen
  - Captures user interactions
  - Saves to JSON format
  - Converts to Playwright code
- **Integration**: Output used by Code Generator Agent

---

## Technology Stack

### Core Framework
- **CrewAI**: Agent orchestration framework
- **Streamlit**: Web UI framework
- **Playwright**: Browser automation
- **ChromaDB**: Vector storage (for future RAG capabilities)

### LLM Providers
- **OpenAI**: GPT-4o, GPT-4o-mini
- **Anthropic**: Claude 3.5 Sonnet
- **OpenRouter**: Multi-provider access

### Languages & Tools
- **Python 3.13**: Main language
- **YAML**: Configuration files
- **JSON**: Data exchange format
- **uv**: Python package manager

### External Services
- **Jira API**: Ticket retrieval
- **ngrok**: Network tunneling (for sharing)

---

## Data Flow

### Test Case Generation Flow

```
1. User Input (Jira Ticket ID)
   │
   ▼
2. Jira API → Fetch Ticket Details
   │
   ▼
3. Validator Agent → Validate Ticket
   │
   ├─→ Invalid → Return Error
   ├─→ Needs More Info → Return Questions
   └─→ Ready → Continue
       │
       ▼
4. Generator Agent → Generate Test Cases
   │
   ▼
5. Save to JSON → Display in UI
```

### Code Generation Flow

```
1. User Selects Test Case
   │
   ├─→ Option A: Has Recorded Flow
   │   │
   │   ▼
   │   2. Load Recorded Flow JSON
   │   │
   │   ▼
   │   3. Extract Codegen Output
   │   │
   │   ▼
   │   4. Code Generator Agent
   │      • Extract locators from codegen
   │      • Generate POM-based code
   │
   └─→ Option B: No Recorded Flow
       │
       ▼
       2. Use Test Case Steps
       │
       ▼
       3. Code Generator Agent
          • Generate from test steps
          • Create locators and functions
   │
   ▼
4. Generate Code (Python + JavaScript)
   │
   ▼
5. Display in Tabs (Locators, Functions, Test Code)
```

### Recording Flow

```
1. User Clicks "Record"
   │
   ▼
2. Launch Playwright Codegen
   │
   ▼
3. User Interacts with Browser
   │
   ▼
4. Capture Interactions
   │
   ▼
5. Save to JSON (with codegen output)
   │
   ▼
6. Available for Code Generation
```

---

## Key Features

### 1. Agent-Based Architecture
- **5 Specialized Agents**: Each with specific role and expertise
- **Task Orchestration**: CrewAI manages agent workflow
- **Context Passing**: Tasks can depend on previous task outputs

### 2. YAML Configuration
- **Separation of Concerns**: Prompts/config separate from code
- **Easy Updates**: Non-developers can modify agent behavior
- **Version Control**: Clear diffs when configs change

### 3. Multi-Provider LLM Support
- **OpenAI**: GPT-4o, GPT-4o-mini
- **Anthropic**: Claude 3.5 Sonnet
- **OpenRouter**: Multi-provider access
- **Automatic Fallback**: Can switch providers easily

### 4. Browser Recording Integration
- **Playwright Codegen**: Uses official Playwright recording
- **Locator Extraction**: Extracts actual working selectors
- **Code Quality**: Uses real browser interactions for accuracy

### 5. Production-Ready Code Generation
- **POM Pattern**: Page Object Model implementation
- **DRY Principles**: Reusable functions and locators
- **Best Practices**: Async/await, error handling, logging
- **Dual Language**: Python and JavaScript support

### 6. Caching & Persistence
- **Test Cases**: Saved to `testcaseGenerated/`
- **Code**: Saved to `codeGenerated/`
- **Recordings**: Saved with test case association
- **History**: Track all generated artifacts

---

## Code Structure

```
jiraTCGeneratorAndPlaywrightCodeGenerator/
├── app.py                          # Main Streamlit UI
├── features/
│   ├── testCaseGeneration/
│   │   ├── agent.py                # Agent creation
│   │   ├── agent.yaml              # Agent config (2 agents)
│   │   ├── task.py                 # Task creation
│   │   ├── task.yaml               # Task config (2 tasks)
│   │   └── generator.py            # Orchestration logic
│   │
│   ├── codeGenerator/
│   │   ├── agent.py                # Agent creation
│   │   ├── agent.yaml              # Agent config (1 agent)
│   │   ├── task.py                 # Task creation
│   │   ├── task.yaml               # Task config (1 task)
│   │   └── generator.py            # Orchestration logic
│   │
│   ├── jiraValidation/
│   │   ├── agent.py                # Agent creation
│   │   ├── agent.yaml              # Agent config
│   │   ├── task.py                 # Task creation
│   │   └── task.yaml               # Task config
│   │
│   ├── llmKeyValidation/
│   │   ├── agent.py                # Agent creation
│   │   ├── agent.yaml              # Agent config
│   │   ├── task.py                 # Task creation
│   │   └── task.yaml               # Task config
│   │
│   └── recording/
│       ├── recorder.py              # Browser recording
│       └── playwright_codegen.py   # Playwright integration
│
├── testcaseGenerated/              # Generated test cases
├── codeGenerated/                  # Generated code
├── utils.py                        # Utility functions
└── auth_store.py                   # User authentication
```

---

## Agent Communication Pattern

### Sequential Task Execution

```
Task 1 (Validator) → Output → Task 2 (Generator)
```

**Example**: Test Case Generation
1. Validator Agent validates Jira ticket
2. Output (JSON) passed to Generator Agent
3. Generator Agent uses validation result to generate test cases

### Context Dependency

Tasks can reference previous task outputs:
```yaml
generate_test_cases:
  context: [validate_jira_story]  # Depends on validation task
  description: |
    Use validation result: {validate_jira_story.output}
```

---

## Configuration Management

### YAML Structure

Each agent/task has:
- **agent.yaml**: Agent role, goal, backstory
- **task.yaml**: Task description, expected output

### Benefits
- ✅ Non-developers can update prompts
- ✅ Version control friendly
- ✅ Easy A/B testing of prompts
- ✅ Separation of concerns

---

## Error Handling & Validation

### Multi-Level Validation
1. **Input Validation**: Jira ticket format, API keys
2. **Agent Validation**: LLM validates ticket suitability
3. **Output Validation**: JSON schema validation
4. **Code Validation**: Syntax checking (future)

### Error Recovery
- Invalid tickets → Return clear error messages
- Missing info → Ask specific questions
- API failures → Graceful degradation

---

## Performance Considerations

### Caching Strategy
- **Test Cases**: Cached by Jira ticket ID
- **Code**: Cached by test case ID
- **Recordings**: Cached by test case + recording ID

### LLM Optimization
- **Lazy Loading**: CrewAI imported only when needed
- **Model Selection**: User can choose model per task
- **Provider Switching**: Easy fallback between providers

---

## Security

### API Key Management
- **Encrypted Storage**: User credentials encrypted
- **Environment Variables**: `.env` file (gitignored)
- **Session State**: Keys stored in Streamlit session

### Data Privacy
- **Local Storage**: All data stored locally
- **No External Sharing**: API keys never sent to third parties
- **User Isolation**: Each user has separate credentials

---

## Future Enhancements

### Planned Features
1. **RAG Integration**: Use ChromaDB for context-aware generation
2. **Self-Healing Tests**: Auto-update locators when they break
3. **Test Execution**: Run generated tests directly
4. **CI/CD Integration**: Export to test runners
5. **Multi-Language Support**: More programming languages

---

## Summary

**QA Assist** is a sophisticated AI-powered platform that:
- Uses **5 specialized agents** for different tasks
- Follows **agent-based architecture** with CrewAI
- Generates **production-ready code** following best practices
- Provides **flexible configuration** via YAML
- Supports **multiple LLM providers** for reliability
- Integrates **browser recording** for accurate locators

The architecture is designed for:
- **Scalability**: Easy to add new agents/tasks
- **Maintainability**: Clear separation of concerns
- **Flexibility**: YAML-based configuration
- **Quality**: Production-ready code generation

