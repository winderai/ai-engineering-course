# Agent-Based Email Processing System Design Specification

## Overview

Design specification for a prototype-level agentic email processing system that follows a reactive `classify → decide → act` pattern. The entire implementation should be contained in a single file called `agent.py` within the `src/brewops/` directory.

**IMPORTANT**: The agent API endpoints must be integrated with the existing FastAPI server in `src/brewops/main.py`. You can create a sub-router in `agent.py` that gets included in the main application, but the agent endpoints must be part of the unified Brewery Operations Hub API.

## Core Architecture

The agent implements a reactive loop that processes emails through three distinct phases:

1. **Classify**: Categorize incoming emails using AI classification
2. **Decide**: Apply business rules to determine appropriate actions
3. **Act**: Execute actions using available tools

## Data Models

### Agent Configuration

```python
@dataclass
class AgentConfig:
    """Configuration for the agent system."""
    model: str = "ollama/qwen3:1.7b"
    timeout: int = 30
    max_retries: int = 3
    auto_send_emails: bool = True
    auto_apply_labels: bool = True
    batch_size: int = 10
    auto_mode_enabled: bool = False
    auto_mode_interval: int = 10  # seconds between inbox checks
    auto_mode_max_emails: int = 50  # max emails to process per cycle
```

### Tool Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Tool(ABC):
    """Abstract base class for agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for agent decision-making."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters.

        Returns:
            Dict containing 'success' bool and 'result' or 'error'
        """
        pass
```

### Email Processing Models

```python
@dataclass
class EmailItem:
    """Email item for agent processing."""
    message_id: str
    sender_email: str
    sender_name: str
    subject: str
    body: str
    timestamp: Optional[datetime]
    imap_uid: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassificationResult:
    """Result of email classification."""
    category: str
    confidence: float
    explanation: str
    processing_time: float
    success: bool
    error: Optional[str] = None

@dataclass
class ActionPlan:
    """Plan of actions to take based on classification."""
    email_id: str
    classification: ClassificationResult
    actions: List[str]  # Tool names to execute
    priority: int  # 1=urgent, 2=high, 3=normal, 4=low
    reasoning: str

@dataclass
class ExecutionResult:
    """Result of executing an action plan."""
    plan_id: str
    email_id: str
    tool_results: Dict[str, Dict[str, Any]]  # tool_name -> result
    success: bool
    total_time: float
    errors: List[str]
```

### Agent State

```python
@dataclass
class AgentState:
    """Current state of the agent."""
    is_running: bool = False
    processed_count: int = 0
    error_count: int = 0
    last_activity: Optional[datetime] = None
    current_batch: List[EmailItem] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    auto_mode_active: bool = False
    auto_mode_next_check: Optional[datetime] = None
    auto_mode_cycles: int = 0
```

## Core Agent Class

### Primary Agent Interface

```python
class EmailProcessingAgent:
    """Reactive email processing agent following classify → decide → act pattern."""

    def __init__(self, tools: List[Tool], config: AgentConfig = AgentConfig()):
        """Initialize agent with available tools and configuration.

        Args:
            tools: List of Tool instances available to the agent
            config: Agent configuration settings
        """

    def process_emails(self, emails: List[EmailItem]) -> List[ExecutionResult]:
        """Process a batch of emails through the complete workflow.

        Args:
            emails: List of EmailItem objects to process

        Returns:
            List of ExecutionResult objects with processing outcomes
        """

    def classify_email(self, email: EmailItem) -> ClassificationResult:
        """Classify a single email (Step 1: Classify).

        Args:
            email: EmailItem to classify

        Returns:
            ClassificationResult with category and metadata
        """

    def decide_actions(self, email: EmailItem,
                      classification: ClassificationResult) -> ActionPlan:
        """Determine actions to take based on classification (Step 2: Decide).

        Args:
            email: Original email item
            classification: Classification result from step 1

        Returns:
            ActionPlan with tools to execute and reasoning
        """

    def execute_plan(self, plan: ActionPlan, email: EmailItem) -> ExecutionResult:
        """Execute the action plan using available tools (Step 3: Act).

        Args:
            plan: ActionPlan from decision step
            email: Original email item

        Returns:
            ExecutionResult with tool execution outcomes
        """

    def start_auto_mode(self, email_credentials: Dict[str, str]) -> Dict[str, Any]:
        """Start continuous auto mode email processing.

        Args:
            email_credentials: Email server connection details

        Returns:
            Dict with auto mode startup status and configuration
        """

    def stop_auto_mode(self) -> Dict[str, Any]:
        """Stop continuous auto mode email processing.

        Returns:
            Dict with auto mode shutdown status and final metrics
        """

    def auto_mode_cycle(self, email_credentials: Dict[str, str]) -> Dict[str, Any]:
        """Execute one cycle of auto mode processing.

        Args:
            email_credentials: Email server connection details

        Returns:
            Dict with cycle results and next check time
        """
```

### Tool Management

```python
class ToolManager:
    """Manages available tools and tool execution."""

    def __init__(self, tools: List[Tool]):
        """Initialize with list of available tools."""

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""

    def list_tools(self) -> List[str]:
        """List all available tool names."""

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool safely with error handling."""
```

## Business Logic

### Classification Logic

The agent uses AI-powered classification to categorize emails into:

- `URGENT_ISSUE`: Safety/equipment failures requiring immediate attention
- `CUSTOMER`: Customer inquiries, complaints, or requests
- `SUPPLY_ORDER`: Supplier communications and purchase requests
- `SCHEDULE`: Meeting, shift, or event scheduling communications
- `MAINTENANCE`: Equipment maintenance and servicing requests
- `OTHER`: Uncategorized emails requiring manual review

**Classification Process:**

1. Extract email content (subject + body, limited to 500 chars)
2. Send to AI model with structured prompt template
3. Parse response to extract category and confidence
4. Apply fallback logic for parsing errors
5. Record classification metadata and timing

### Decision Engine Rules

Map classifications to tool actions based on business priorities:

```python
DECISION_RULES = {
    "URGENT_ISSUE": {
        "tools": ["alert_creator", "label_applier"],
        "priority": 1,
        "reasoning": "Safety issues require immediate escalation and tracking"
    },
    "CUSTOMER": {
        "tools": ["product_search", "response_generator", "label_applier", "email_sender", "email_archiver"],
        "priority": 2,
        "reasoning": "Customer satisfaction requires prompt, personalized responses with accurate product information. Archive after completion."
    },
    "SUPPLY_ORDER": {
        "tools": ["order_query", "response_generator", "label_applier", "email_sender", "email_archiver"],
        "priority": 2,
        "reasoning": "Supply chain continuity depends on timely supplier communication with accurate order information. Archive after completion."
    },
    "SCHEDULE": {
        "tools": ["label_applier", "review_logger"],
        "priority": 3,
        "reasoning": "Schedule changes need human coordination and approval"
    },
    "MAINTENANCE": {
        "tools": ["label_applier", "review_logger"],
        "priority": 3,
        "reasoning": "Technical decisions require expert evaluation"
    },
    "OTHER": {
        "tools": ["label_applier", "review_logger"],
        "priority": 4,
        "reasoning": "Unknown categories default to manual review queue"
    }
}
```

### Action Execution Logic

Execute tools in sequence with error handling:

1. **Tool Execution Order**: Tools execute sequentially in the order specified in DECISION_RULES
   - For customer communications: product_search → response_generator → label_applier → email_sender → email_archiver
   - For supplier communications: order_query → response_generator → label_applier → email_sender → email_archiver
   - Information tools (product_search, order_query) execute first to gather context for response generation
   - Archive tool should only execute after successful email sending
2. **Reply vs New Email**: When using email_sender tool, always reply to original emails (not create new ones) for customer communications
3. **Error Handling**: Tool failures don't stop the entire workflow - log errors and continue
4. **Retry Logic**: Implement exponential backoff for transient failures (network, AI timeout)
5. **State Management**: Track execution state for monitoring and debugging
6. **Archive Logic**: Only archive emails when all processing is complete and no manual review is required
7. **Context Passing**: Information gathered by product_search and order_query tools should be made available to response_generator for creating informed, personalized replies
8. **Email Thread Context**: All tools that process emails should receive full email thread context by default:
   - Use Gmail's X-GM-THRID extension to find complete conversation threads across folders (INBOX, Sent Mail, All Mail)
   - Fallback to References/Message-ID header search for non-Gmail systems
   - Subject-based search as final fallback for emails without proper threading headers
   - Tools like product_search and order_query use thread context to understand previous conversation history
   - Response generator includes full conversation context for contextually appropriate replies
   - Thread fetching implemented in `EmailClient.fetch_email_thread()` method

## API Integration

### FastAPI Integration Requirements

The agent system must be integrated with the existing FastAPI application in `src/brewops/main.py`. You have two implementation options:

#### Option 1: Sub-router (Recommended)

Create a FastAPI sub-router in `agent.py` and include it in the main application:

```python
# In agent.py
from fastapi import APIRouter

agent_router = APIRouter(prefix="/agent", tags=["agent"])

@agent_router.post("/process")
async def process_emails(request: ProcessRequest):
    # Implementation here
    pass

# In main.py
from brewops.agent import agent_router
app.include_router(agent_router)
```

#### Option 2: Direct Integration

Define the agent endpoints directly in `main.py` and import agent functionality:

```python
# In main.py
from brewops.agent import EmailProcessingAgent, initialize_agent

@app.post("/agent/process")
async def process_emails(request: ProcessRequest):
    agent = get_agent()  # Get initialized agent instance
    # Implementation here
```

### Agent Initialization

The agent must be initialized during application startup and share the same service instances (ProductInformationService, OrderQueryService) as the existing main application. Update the startup event in `main.py`:

```python
@app.on_event("startup")
async def startup_event():
    # Existing initialization code...

    # Initialize agent with shared services
    global agent_instance
    agent_instance = initialize_agent(
        email_client=None,  # Will be created per request
        product_service=product_service,  # Shared instance
        order_service=order_service,  # Shared instance
        config=AgentConfig()
    )
```

## API Endpoints

### Core Agent Endpoints

#### `POST /agent/process`

Process emails through the agent workflow.

**Request Schema:**

```python
class ProcessRequest(BaseModel):
    emails: List[Dict[str, Any]]  # EmailItem data as dicts
    config_override: Optional[Dict[str, Any]] = None
    email_credentials: Optional[Dict[str, str]] = None  # server, username, password
```

**Response Schema:**

```python
class ProcessResponse(BaseModel):
    results: List[Dict[str, Any]]  # ExecutionResult data
    summary: Dict[str, Any]  # counts, timing, success rate
    agent_state: Dict[str, Any]  # AgentState data
```

#### `GET /agent/status`

Get current agent status and performance metrics.

**Response Schema:**

```python
class AgentStatusResponse(BaseModel):
    state: Dict[str, Any]  # AgentState data
    available_tools: List[str]
    recent_activity: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]
```

#### `POST /agent/tools/register`

Register a new tool with the agent at runtime.

**Request Schema:**

```python
class ToolRegistration(BaseModel):
    tool_name: str
    tool_class: str  # Importable class name
    tool_config: Dict[str, Any] = {}
```

#### `GET /agent/tools`

List all available tools and their descriptions.

**Response Schema:**

```python
class ToolsResponse(BaseModel):
    tools: Dict[str, Dict[str, str]]  # name -> {description, status}
    total_count: int
```

#### `POST /agent/process-inbox` (New Endpoint)

Convenience endpoint that fetches all emails from the configured inbox and processes them through the agent workflow. This combines the functionality of `/emails/all` and `/agent/process`.

**Request Schema:**

```python
class ProcessInboxRequest(BaseModel):
    config_override: Optional[Dict[str, Any]] = None
    email_credentials: Optional[Dict[str, str]] = None  # Override env credentials
```

**Response Schema:** Same as `POST /agent/process`

#### `POST /agent/auto/start`

Start auto mode - continuous email processing that runs in a background loop.

**Request Schema:**

```python
class AutoModeStartRequest(BaseModel):
    email_credentials: Dict[str, str]  # server, username, password
    config_override: Optional[Dict[str, Any]] = None  # Override auto mode settings
```

**Response Schema:**

```python
class AutoModeResponse(BaseModel):
    success: bool
    message: str
    auto_mode_config: Dict[str, Any]
    next_check_time: Optional[datetime]
```

#### `POST /agent/auto/stop`

Stop auto mode - halt continuous email processing.

**Response Schema:** Same as `AutoModeResponse`

#### `GET /agent/auto/status`

Get current auto mode status and metrics.

**Response Schema:**

```python
class AutoModeStatusResponse(BaseModel):
    auto_mode_active: bool
    cycles_completed: int
    emails_processed_total: int
    next_check_time: Optional[datetime]
    last_cycle_results: Optional[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
```

## Auto Mode Implementation

### Auto Mode Operation

Auto mode implements continuous email processing with the following behavior:

1. **Background Loop**: Runs as a background task using asyncio
2. **Periodic Checking**: Checks inbox every `auto_mode_interval` seconds (default: 10)
3. **Batch Processing**: Processes up to `auto_mode_max_emails` per cycle (default: 50)
4. **Email Persistence**: Only processes emails that haven't been processed yet
5. **Error Resilience**: Continues running even if individual cycles fail
6. **Graceful Shutdown**: Can be stopped cleanly while preserving state

### Auto Mode Configuration

```python
# Auto mode specific configuration
auto_mode_enabled: bool = False          # Enable/disable auto mode
auto_mode_interval: int = 10             # Seconds between inbox checks
auto_mode_max_emails: int = 50           # Max emails per cycle
```

### Auto Mode Workflow

```
Auto Mode Start
    ↓
Create Background Task
    ↓
┌─► Check Inbox (every interval)
│       ↓
│   Fetch New Emails
│       ↓
│   Process Through Agent
│       ↓
│   Update Metrics
│       ↓
│   Sleep Until Next Interval
│       ↓
└─── Loop Until Stop Signal
    ↓
Clean Shutdown
```

### Auto Mode State Management

- **Persistent State**: Auto mode status persists across agent restarts
- **Cycle Tracking**: Number of completed cycles and total emails processed
- **Performance Metrics**: Response times, success rates, error patterns
- **Next Check Time**: When the next inbox check will occur
- **Last Results**: Results from the most recent processing cycle

## Built-in Tool Implementations

### EmailClassifierTool

```python
class EmailClassifierTool(Tool):
    name = "email_classifier"
    description = "Classify emails using AI into brewery operation categories"

    def execute(self, email: EmailItem) -> Dict[str, Any]:
        # Use existing EmailClassifier implementation
        # Return classification result as dict
```

### LabelApplierTool

```python
class LabelApplierTool(Tool):
    name = "label_applier"
    description = "Apply Gmail labels based on email classification"

    def execute(self, email: EmailItem, label_name: str,
               email_client: EmailClient) -> Dict[str, Any]:
        # Apply label using email_client.apply_label()
        # Return success status and details
```

### ResponseGeneratorTool

```python
class ResponseGeneratorTool(Tool):
    name = "response_generator"
    description = "Generate AI-powered email responses"

    def execute(self, email: EmailItem, email_type: str) -> Dict[str, Any]:
        # Use existing EmailGenerator implementation
        # Return generated email content
```

### EmailSenderTool

```python
class EmailSenderTool(Tool):
    name = "email_sender"
    description = "Send email responses via SMTP (replies to original emails when communicating with customers)"

    def execute(self, original_email: EmailItem, reply_body: str,
               email_client: EmailClient, reply_subject: Optional[str] = None) -> Dict[str, Any]:
        # Use email_client.reply_to_email() for customer communications to maintain threading
        # For new emails (rare), use email_client.send_email()
        # Return send status and details
```

### AlertCreatorTool

```python
class AlertCreatorTool(Tool):
    name = "alert_creator"
    description = "Create urgent alerts for critical issues"

    def execute(self, email: EmailItem, alert_type: str = "urgent") -> Dict[str, Any]:
        # Log critical alert (in production: PagerDuty, Slack, etc.)
        # Return alert details and status
```

### ReviewLoggerTool

```python
class ReviewLoggerTool(Tool):
    name = "review_logger"
    description = "Queue emails for manual review"

    def execute(self, email: EmailItem, priority: str = "normal") -> Dict[str, Any]:
        # Log to review queue (in production: ticket system, database)
        # Return queue status and details
```

### EmailArchiverTool

```python
class EmailArchiverTool(Tool):
    name = "email_archiver"
    description = "Archive emails after successful processing"

    def execute(self, email: EmailItem, email_client: EmailClient) -> Dict[str, Any]:
        # Use email_client.archive_email() to move email from inbox to archive
        # Return archive status and details
```

### ProductSearchTool

```python
class ProductSearchTool(Tool):
    name = "product_search"
    description = "Search product information using natural language RAG pipeline"

    def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        # Use ProductInformationService.search_products_rag()
        # Return search results with product details
```

### OrderQueryTool

```python
class OrderQueryTool(Tool):
    name = "order_query"
    description = "Query order information using natural language with LLM-powered SQL generation"

    def execute(self, question: str) -> Dict[str, Any]:
        # Use OrderQueryService.generate_sql_with_llm() and execute_order_query()
        # Return order information and query details
```

## Data Flow and Processing Steps

### 1. Email Ingestion

```
EmailClient.fetch_all_emails_full()
→ List[EmailMessage]
→ Convert to List[EmailItem]
→ Agent.process_emails()
```

### 2. Classification Phase

```
For each EmailItem:
  → EmailClassifierTool.execute(email)
  → Extract category, confidence, explanation
  → Handle classification errors with fallbacks
  → Record timing and success metrics
```

### 3. Decision Phase

```
Classification + Email → Decision Engine
  → Apply DECISION_RULES mapping
  → Generate ActionPlan with tool list
  → Set priority and reasoning
  → Validate tool availability
```

### 4. Execution Phase

```
ActionPlan → ToolManager.execute_tools()
  → For each tool in plan:
    → Tool.execute(**params)
    → Capture result and timing
    → Handle errors without stopping workflow
  → Aggregate results into ExecutionResult
```

### 5. State Management

```
Each processing cycle:
  → Update AgentState metrics
  → Log performance data
  → Track error rates and patterns
  → Update last_activity timestamp
```

## Integration Points

### Email Client Integration

- EmailClient instances are created per request to avoid connection state issues
- Use the same email credentials and configuration patterns as existing endpoints in `main.py`
- **IMPORTANT**: EmailClient must remain available to all tools throughout execution - ensure client is not closed before tools complete
- Tools use client for email operations (send, label, etc.)
- Client manages IMAP/SMTP connections and authentication
- Tool execution must maintain client connection until all planned actions are complete

### Service Integration

- **ProductInformationService**: Share the same instance initialized at startup in `main.py`
- **OrderQueryService**: Share the same instance initialized at startup in `main.py`
- **EmailClassifier** and **EmailGenerator**: Create new instances per request with configuration from environment variables
- Use the same environment variable patterns as existing endpoints (`OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, etc.)

### Configuration Integration

- Reuse existing environment variables from `main.py`:
  - `EMAIL_SERVER`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` for email operations
  - `OLLAMA_MODEL`, `OLLAMA_TIMEOUT` for AI model configuration
  - `DATA_DIRECTORY` for shared data services
- Agent-specific configuration can be passed via request parameters or additional environment variables

### Logging and Monitoring

- Use the same logging setup as `main.py` (`brewops.log.setup_logging()`)
- Structured logging for all agent activities
- Performance metrics collection (timing, success rates)
- Error aggregation and reporting
- Tool usage statistics

## Performance Specifications

### Throughput Requirements

- Process 100+ emails per minute in batch mode
- Single email processing: <5 seconds end-to-end
- Tool execution: <2 seconds per tool on average
- Classification: <1 second per email

### Resource Management

- Memory efficient batch processing
- Connection pooling for external services
- Graceful degradation on tool failures
- Automatic retry with exponential backoff

### Monitoring Metrics

- Emails processed per hour
- Classification accuracy over time
- Tool success/failure rates
- Average response times by operation
- Error patterns and frequencies

## Implementation Requirements Summary

This specification provides a complete blueprint for implementing the agent-based email processing system with the following key requirements:

### 1. File Structure

- **Single file implementation**: All agent code in `src/brewops/agent.py`
- **Integration**: Agent endpoints must be part of the main FastAPI app in `src/brewops/main.py`

### 2. API Integration Approaches

- **Recommended**: Create FastAPI sub-router in `agent.py`, include in `main.py`
- **Alternative**: Define endpoints directly in `main.py`, import agent classes from `agent.py`

### 3. Service Integration

- **Shared services**: Reuse `product_service` and `order_service` instances from main app
- **Per-request services**: Create new EmailClient, EmailClassifier, EmailGenerator per request
- **Environment variables**: Use same configuration patterns as existing endpoints

### 4. Core Functionality

- **Reactive workflow**: classify → decide → act pattern
- **9 built-in tools**: Including product search and order query tools from existing services
- **Error handling**: Graceful degradation with comprehensive logging
- **Email operations**: Full IMAP/SMTP integration with threading support

### 5. API Endpoints

- `POST /agent/process`: Process provided emails through agent workflow
- `POST /agent/process-inbox`: Fetch inbox emails and process automatically
- `GET /agent/status`: Agent health and performance metrics
- `GET /agent/tools`: List available tools
- `POST /agent/tools/register`: Dynamic tool registration
- `POST /agent/auto/start`: Start continuous auto mode email processing
- `POST /agent/auto/stop`: Stop continuous auto mode email processing
- `GET /agent/auto/status`: Get auto mode status and metrics

This integrated approach ensures the agent system becomes part of the unified Brewery Operations Hub API while maintaining the reactive classify → decide → act pattern and full compatibility with existing services.

## Implementation Notes

### Agent Initialization Fix

**Issue**: If you encounter the error `"Agent not initialized"` when calling agent endpoints, this indicates a problem with the global agent instance not being properly set.

**Root Cause**: The `agent_instance` global variable is declared in `agent.py`, but attempting to set it directly from `main.py` using `global agent_instance` doesn't work across Python modules - each module has its own global scope.

**Solution**: The `initialize_agent()` function in `agent.py` handles setting the global variable internally:

```python
# In agent.py
def initialize_agent(...) -> EmailProcessingAgent:
    global agent_instance
    # ... create agent ...
    agent_instance = EmailProcessingAgent(tools=tools, config=config)
    return agent_instance

# In main.py startup event
initialize_agent(
    product_service=product_service,
    order_service=order_service,
    config=AgentConfig()
)
```

This ensures the global variable is set within the same module where it's declared, resolving the initialization issue.
