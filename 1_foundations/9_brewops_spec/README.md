## Requirements Documentation: Brewery Operations Email Classifier

### Business Objectives

**Primary Goals and Success Metrics**

- Automatically classify incoming brewery operations emails into predefined categories to enable priority-based routing and response
- Achieve consistent classification with response times under 30 seconds per email
- Success metrics: Classification accuracy, response time per email, system uptime

**User Personas and Use Cases**

- **Brewery Operations Manager**: Needs to quickly identify and respond to urgent equipment failures or safety issues
- **Supply Chain Coordinator**: Must track and process purchasing requests and supply orders
- **Shift Supervisor**: Requires visibility into scheduling changes and meeting requests
- **Customer Service Team**: Needs to identify and route customer inquiries appropriately
- **Maintenance Team**: Must track routine servicing requests

**Business Constraints and Limitations**

- Must run locally without external API dependencies for data privacy
- Response time should not exceed 30 seconds per email
- Must handle partial or malformed email content gracefully
- Email body analysis limited to first 500 characters for performance

### Technical Specifications

**Input Data Formats and Sources**

- Email messages with the following structure:
  - `sender_name`: String (sender's display name)
  - `sender_email`: String (sender's email address)
  - `subject`: String or None (email subject line)
  - `body`: String or None (email body content)
  - `message_id`: String (unique identifier)

**Expected Output Formats**

- Classification result dictionary containing:
  - `category`: One of: URGENT_ISSUE, SUPPLY_ORDER, SCHEDULE, CUSTOMER, MAINTENANCE, OTHER, ERROR
  - `explanation`: String describing the classification reasoning
  - `confidence`: "high", "medium", or "none"
  - `response_time`: Float (seconds taken for classification)
  - `model_used`: String (model identifier)
  - `success`: Boolean (true if classification succeeded)
  - `error`: String (only present if success is false)

**Email Categories and Definitions**

- **URGENT_ISSUE**: Equipment failure, safety issues, critical operational problems
- **SUPPLY_ORDER**: Purchasing requests, inventory orders, supplier communications
- **SCHEDULE**: Meeting requests, shift changes, scheduling updates
- **CUSTOMER**: Customer inquiries, feedback, complaints, product questions
- **MAINTENANCE**: Routine servicing, preventive maintenance, non-urgent repairs
- **OTHER**: All emails not fitting above categories
- **ERROR**: Classification failure state

**Integration Points and APIs**

- **LiteLLM**: Python package for unified LLM API interface
- **Ollama**: Local LLM runtime (must be running as service)
  - Default model: `ollama/qwen3:1.7b`
  - Connection via local HTTP API
  - Disable thinking
- **API**: Present all classification information via the REST API.

### Quality Assurance

**Testing Strategies**

- **Connection Testing**: Verify Ollama server availability before classification
  - Test with simple "Hello" prompt
  - 10-second timeout for connection tests
  - Provide diagnostic messages for common connection failures
- **Classification Testing**: None.

**Validation Approaches**

- Response parsing with fallback mechanisms:
  - Primary: Look for exact category match in model response
  - Secondary: Remove any "thinking" tokens (`<think>...</think>`) and try again.
  - Fallback: Default to "OTHER" category with explanation if parsing fails
- Model response cleaning and normalization (uppercase matching, whitespace trimming)
- Graceful degradation with detailed error messages

**Performance Benchmarks**

- Default timeout: 30 seconds per classification
- Connection test timeout: 10 seconds
- Model parameters for consistency:
  - Temperature: 0.1 (low for consistent classification)
  - Max tokens: 20 (keep responses concise)
- Track and report response times for all operations

**Acceptance Criteria**

- Successfully connects to Ollama server
- Classifies emails into correct categories based on content
- Handles missing or malformed email fields without crashing
- Provides clear error messages with troubleshooting steps
- Completes classification within timeout period
- Returns structured response with all required fields
- Logs all operations with appropriate detail levels
- Provides summary statistics (success rate, average processing time)

**Error Handling Requirements**

- Detect and report connection failures with actionable messages
- Handle model timeout scenarios
- Manage missing model errors with pull instructions
- Process malformed responses gracefully
- Provide user-friendly error translations for technical failures
- Include detailed logging for debugging purposes
