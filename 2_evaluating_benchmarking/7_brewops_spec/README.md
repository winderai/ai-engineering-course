# AI Design Document: Brewery Operations Email Processing System

## Overview

The Brewery Operations Email Processing System is an AI-powered application that demonstrates a complete email workflow automation pipeline. The system implements a **classify → decide → act** pattern to process incoming emails and take appropriate business actions based on the content and classification.

## System Architecture

### Core Components

#### 1. Domain Logic Layer (`BreweryDomainLogic`)

- **Location**: `src/brewops/domain_logic.py`
- **Purpose**: Orchestrates the complete email processing workflow
- **Key Responsibilities**:
  - Coordinates AI classification and action execution
  - Manages business rules and decision-making logic
  - Provides workflow result tracking and analytics

#### 2. Classification Engine (`EmailClassifier`)

- **AI Model**: Ollama-based classification using `ollama/qwen3:1.7b`
- **Purpose**: Categorizes incoming emails into business-relevant categories
- **Categories**:
  - `URGENT_ISSUE` - Critical safety or equipment issues
  - `CUSTOMER` - Customer inquiries and service requests
  - `SUPPLY_ORDER` - Supplier orders and purchasing requests
  - `SCHEDULE` - Scheduling changes and coordination
  - `MAINTENANCE` - Equipment maintenance and servicing
  - `OTHER` - General emails requiring manual review

#### 3. Action Execution System

Three primary action types based on classification:

- **`GENERATE_RESPONSE`** - AI-powered email response generation and automatic sending
- **`CREATE_ALERT`** - Critical alert creation for urgent issues
- **`LOG_REVIEW`** - Queue items for manual human review

#### 4. Email Generation Engine (`EmailGenerator`)

- **AI Model**: Ollama-based generation using `ollama/qwen3:1.7b`
- **Purpose**: Creates contextually appropriate business email responses
- **Supported Types**: Customer service, supplier orders, maintenance scheduling, quality alerts

## Workflow Architecture

### The Classify → Decide → Act Pipeline

```mermaid
graph TD
    A[Email Input] --> B[Email Classification]
    B --> C[Gmail Label Application]
    C --> D[Business Rule Lookup]
    D --> E[Action Determination]
    E --> F[Action Execution]
    F --> G[Email Sending (if response action)]
    G --> H[Result Compilation]
    H --> I[Next Steps Planning]
    I --> J[Workflow Result]
```

### Processing Flow Detail

1. **Email Classification** (`BreweryDomainLogic.process_email_workflow:152`)
   - Input: Raw email message with IMAP UID
   - AI Processing: Content analysis using LLM
   - Output: Category + confidence + explanation

2. **Gmail Label Application**
   - Input: Classification category + email IMAP UID
   - Processing: Apply category-based label to email in Gmail using proper UID operations
   - Output: Label application success status

3. **Business Rule Application** (`BreweryDomainLogic._initialize_business_rules:72-109`)
   - Input: Classification category
   - Processing: Rule-based action mapping
   - Output: List of actions to execute

4. **Action Execution** (`BreweryDomainLogic._execute_action:173-211`)
   - Input: Action type + email context + classification
   - Processing: Type-specific action logic
   - Output: Action result with success status

5. **Email Response Sending** (for GENERATE_RESPONSE actions)
   - Input: Generated response email + original sender details
   - Processing: SMTP email delivery to original sender
   - Output: Email sending success status

6. **Result Aggregation** (`WorkflowResult:48-56`)
   - Combines classification, actions, labeling, sending status, timing, and success metrics
   - Determines next steps based on action outcomes
   - Provides complete audit trail

## AI Integration Points

### Classification AI Component

- **Model**: `ollama/qwen3:1.7b` via Ollama
- **Input**: Email subject + body + metadata
- **Processing**: Natural language understanding for business context
- **Output**: Structured classification with confidence scores
- **Error Handling**: Graceful degradation to manual classification

### Response Generation AI Component  

- **Model**: `ollama/qwen3:1.7b` via Ollama
- **Input**: Email context + classification + business rules
- **Processing**: Context-aware email composition
- **Output**: Professional email with subject and body
- **Templates**: Business-specific email types (customer service, supplier, alerts)

## Email Integration Features

### Automatic Email Sending

The system now includes complete email delivery capabilities for response actions:

- **SMTP Integration**: Uses secure SMTP with TLS encryption for email delivery
- **Response Delivery**: Automatically sends AI-generated responses to original email senders
- **Delivery Tracking**: Monitors email sending success/failure for workflow completion
- **Error Handling**: Graceful degradation when email sending fails

### Gmail Label Management

Classification-based automatic labeling system:

- **Label Creation**: Automatically creates Gmail labels for each classification category
- **Auto-Labeling**: Applies appropriate labels to emails immediately after classification using proper IMAP UIDs
- **Label Hierarchy**: Supports nested labels for detailed organization
- **Bulk Operations**: Efficiently handles label application for batch processing
- **IMAP UID Tracking**: Emails now include both Message-ID and IMAP UID for reliable server operations

**Default Label Mapping**:

- `URGENT_ISSUE` → "BrewOps/Urgent"
- `CUSTOMER` → "BrewOps/Customer"
- `SUPPLY_ORDER` → "BrewOps/Supply"
- `SCHEDULE` → "BrewOps/Schedule"
- `MAINTENANCE` → "BrewOps/Maintenance"
- `OTHER` → "BrewOps/Review"

## API Design

### Core Endpoint: `/emails/process-all`

**Purpose**: End-to-end email processing demonstration

**Flow**:

1. **Email Retrieval** (`main.py:702`) - Fetch all emails from configured inbox with proper IMAP UID tracking
2. **Batch Processing** (`main.py:738-817`) - Process each email through domain logic workflow
3. **Result Aggregation** (`main.py:818-843`) - Compile statistics and outcomes
4. **Response Formation** - Return comprehensive processing report

**Response Structure**:

```json
{
  "total_emails": 15,
  "successful_workflows": 12,
  "failed_workflows": 3,
  "total_processing_time": 45.6,
  "average_time_per_email": 3.04,
  "success_rate": 80.0,
  "actions_summary": {
    "generate_response": 8,
    "create_alert": 2,
    "log_review": 2
  },
  "classification_summary": {
    "CUSTOMER": 8,
    "URGENT_ISSUE": 2,
    "MAINTENANCE": 3,
    "OTHER": 2
  },
  "email_integration_summary": {
    "emails_sent": 8,
    "emails_failed_to_send": 0,
    "labels_applied": 15,
    "labels_failed": 0,
    "new_labels_created": 6
  },
  "processed_emails": [...]
}
```

## Business Logic Rules

### Rule-Based Action Mapping

Defined in `BreweryDomainLogic._initialize_business_rules()`:

| Classification | Actions | Business Rationale | Email Integration |
|---------------|---------|-------------------|------------------|
| `URGENT_ISSUE` | `CREATE_ALERT` | Safety-critical issues require immediate escalation | Label: "BrewOps/Urgent" |
| `CUSTOMER` | `GENERATE_RESPONSE` | Customer satisfaction requires timely, personalized responses | Label: "BrewOps/Customer" + Auto-send response |
| `SUPPLY_ORDER` | `GENERATE_RESPONSE` | Business continuity depends on supplier communication | Label: "BrewOps/Supply" + Auto-send response |
| `SCHEDULE` | `LOG_REVIEW` | Coordination changes need human oversight | Label: "BrewOps/Schedule" |
| `MAINTENANCE` | `LOG_REVIEW` | Technical decisions require expert evaluation | Label: "BrewOps/Maintenance" |
| `OTHER` | `LOG_REVIEW` | Unknown categories default to manual review | Label: "BrewOps/Review" |

## Data Structures

### Key Models

#### `ActionResult` (domain_logic.py:30-37)

```python
@dataclass
class ActionResult:
    action_type: ActionType
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
```

#### `WorkflowResult` (domain_logic.py:48-56)

```python
@dataclass
class WorkflowResult:
    email_id: str
    classification: Dict[str, Any]
    actions_taken: List[ActionResult]
    total_processing_time: float
    workflow_success: bool
    next_steps: List[str]
```

#### `ProcessingRule` (domain_logic.py:40-45)

```python
@dataclass
class ProcessingRule:
    classification: str
    actions: List[ActionType]
    description: str
```

## Error Handling and Resilience

### AI Failure Handling

- **Classification Failure** (`domain_logic.py:126-135`): Falls back to "OTHER" category
- **Generation Failure** (`domain_logic.py:258-272`): Returns error details for manual intervention
- **Individual Email Failures** (`main.py:814-824`): Isolates failures to prevent batch processing interruption

### Timeout Management

- Configurable AI model timeouts via environment variables
- Per-action execution time tracking
- Total workflow time monitoring

### Graceful Degradation

- System continues processing even with individual failures
- Manual review queue for failed AI operations
- Comprehensive error reporting for debugging

## Performance Considerations

### Optimization Strategies

- **Batch Processing**: Processes multiple emails in single API call
- **Async Operations**: Uses async/await for I/O-bound operations
- **Model Reuse**: Single classifier and generator instances per workflow
- **Timeout Controls**: Prevents hanging on slow AI responses

### Metrics Tracking

- Processing time per email
- Success rates by category
- Action execution statistics
- AI model response times

## Security and Privacy

### Email Access

- Secure IMAP connection with credentials from environment variables
- Connection cleanup in finally blocks
- No credential logging or storage

### AI Processing

- Local Ollama deployment (no cloud AI service dependencies)
- Email content processed locally
- No external data transmission for AI operations

## Deployment Architecture

### Dependencies

- **Python 3.10+** with FastAPI
- **Ollama** for local AI model serving
- **Email Server** (IMAP) for email retrieval
- **Environment Variables** for configuration

### Configuration

- `OLLAMA_MODEL`: AI model identifier (default: `ollama/qwen3:1.7b`)
- `OLLAMA_TIMEOUT`: AI request timeout (default: 30s)
- `EMAIL_SERVER`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`: Email access (IMAP & SMTP)
- `SMTP_SERVER`: SMTP server for sending emails (auto-detected from IMAP server if not specified)
- `SMTP_PORT`: SMTP server port (default: 587)
- `AUTO_SEND_RESPONSES`: Enable/disable automatic email sending (default: true)
- `AUTO_LABEL_EMAILS`: Enable/disable automatic Gmail labeling (default: true)

## Future Enhancement Opportunities

### AI Improvements

- Multi-model ensemble for better classification accuracy
- Fine-tuned models for brewery domain-specific language
- Confidence threshold tuning for action decisions

### Integration Enhancements

- Real-time email processing with webhooks
- Integration with ticketing systems (Jira, ServiceNow)
- Alert system integration (PagerDuty, Slack)
- Customer relationship management (CRM) connectivity

### Analytics and Monitoring

- Processing pipeline observability
- AI model performance monitoring
- Business metric tracking (response times, customer satisfaction)
- A/B testing framework for AI model improvements

## Recent Improvements

### Email Processing Enhancements

- **Fixed Gmail Labeling**: Resolved IMAP UID command parsing issues by implementing Gmail-compatible UID extraction from standard IMAP operations
- **Consolidated Email Fetching**: Removed duplicate `fetch_all_emails` method, standardized on `fetch_all_emails_full` with complete email data and UID tracking
- **Enhanced Error Handling**: Improved resilience for Gmail IMAP server compatibility issues
- **Unified API Responses**: All email endpoints now return consistent `EmailMessage` objects with both Message-ID and IMAP UID

### Code Quality Improvements

- **Type Safety**: All components pass type checking with proper type annotations
- **Code Consistency**: Eliminated duplicate functionality and consolidated email processing logic
- **Debugging Support**: Added diagnostic endpoints (`/emails/uids`, `/emails/test-labeling`) for troubleshooting

## Conclusion

This system demonstrates practical AI application in business process automation, showcasing how AI classification and generation can be combined with rule-based logic to create intelligent, automated workflows. The modular architecture allows for easy extension and customization while maintaining robust error handling and performance characteristics suitable for production deployment.

The implementation includes comprehensive Gmail integration with proper IMAP UID handling, ensuring reliable email labeling and processing operations across different email providers and IMAP server implementations.
