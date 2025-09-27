# OpenLIT Tracing Integration for Brewery Operations Hub

## Overview

This document outlines how to add OpenLIT tracing to the Brewery Operations Hub to provide visibility into the AI-powered email processing pipeline.

## Application Structure

The Brewery Operations Hub processes brewery emails through these components:

- **Email Processing**: IMAP/SMTP operations (`email_client.py`)
- **AI Classification**: LLM-powered email categorization (`classifier.py`)
- **Business Logic**: Rule-based decision making (`domain_logic.py`)
- **AI Generation**: Automated response generation (`email_generator.py`)
- **Information Services**: RAG-powered product search (`information.py`)
- **Agent System**: Multi-step autonomous processing (`agent.py`)

## What to Trace

- Email processing end-to-end latency
- LLM response times and token usage
- RAG pipeline performance
- Classification accuracy
- Email send/receive operations

## Span Design

### Top-Level Workflow Spans

```
email_processing_workflow        # Complete email processing
├── email_fetch_operation       # Getting emails from IMAP
├── email_classification        # AI categorization
├── business_rule_processing    # Decision making
├── response_generation         # AI email generation
└── email_send_operation        # Sending via SMTP
```

### AI Operation Spans

```
email_classification
├── llm_call                    # LiteLLM API call
└── result_parsing              # Processing response

response_generation
├── prompt_building             # Template preparation
├── llm_call                    # AI generation
└── email_formatting            # Final email assembly

rag_search
├── embedding_generation        # Vector creation
├── similarity_search          # Vector lookup
└── context_assembly           # Result preparation
```

## Detailed Span Attributes

### Email Processing Spans

**`email_processing_workflow`**

- `email.id`: Unique email identifier
- `email.sender`: Sender email address
- `email.subject`: Email subject (truncated)
- `email.category`: AI classification result
- `processing_time_ms`: Total processing time

**`email_fetch_operation`**

- `email.server`: IMAP server hostname
- `email.count_fetched`: Number of emails retrieved
- `imap_connection_time_ms`: Connection establishment time
- `fetch_latency_ms`: Email retrieval time

**`email_send_operation`**

- `email.recipient`: Recipient email (hashed)
- `smtp.server`: SMTP server used
- `send_time_ms`: Time to send email
- `delivery_success`: Whether email was delivered

### AI Classification Spans

**`email_classification`**

- `classification.model`: Model used (e.g., qwen3:1.7b)
- `email.content_length`: Length of content processed
- `classification_time_ms`: Total classification time
- `confidence_score`: Model confidence (0-1)

**`llm_call`**

- `llm.model`: Specific model version
- `llm.provider`: Provider (ollama/openai)
- `llm.temperature`: Temperature setting
- `llm_latency_ms`: Model response time
- `tokens_input`: Input tokens consumed
- `tokens_output`: Output tokens generated

### Response Generation Spans

**`response_generation`**

- `generation.email_type`: Type of email being generated
- `generation.context_length`: Length of context provided
- `generation_time_ms`: Time to generate response
- `content_length_generated`: Length of generated content

**`prompt_building`**

- `prompt.template`: Template used
- `prompt.variables`: Number of template variables
- `prompt_length`: Final prompt length

### RAG Search Spans

**`rag_search`**

- `rag.query`: Search query (sanitized)
- `rag.max_results`: Maximum results requested
- `rag_total_time_ms`: Complete RAG pipeline time
- `results_returned`: Number of results returned

**`embedding_generation`**

- `embedding.model`: Embedding model used
- `embedding.dimensions`: Vector dimensions
- `embedding_time_ms`: Time to generate embeddings

**`similarity_search`**

- `search.index_size`: Number of vectors searched
- `search_time_ms`: Time to perform search
- `candidates_evaluated`: Number of candidates considered

## 🚨 CRITICAL IMPLEMENTATION CONSTRAINT

**SELF-CONTAINED REQUIREMENT**: This implementation must be **completely self-contained** and **non-invasive**:

- ✅ **CAN modify**: `main.py` only
- ✅ **CAN create**: New files for tracing infrastructure
- ❌ **CANNOT modify**: Any existing brewery operation files (`classifier.py`, `email_generator.py`, `email_client.py`, `domain_logic.py`, `information.py`, `agent.py`)

This constraint requires using **monkey patching**, **dynamic wrapping**, and **introspection** techniques to inject tracing without touching existing code.

## Implementation Strategy

### Self-Contained Approach

The implementation will use a **tracing wrapper system** that:

1. **Imports and wraps existing classes/functions** at runtime
2. **Uses monkey patching** to inject OpenTelemetry spans
3. **Preserves original functionality** completely
4. **Adds tracing as a transparent layer**

### Phase 1: Infrastructure Setup

1. Create `src/brewops/tracing/` directory structure
2. Initialize OpenLIT in `main.py`
3. Create base tracing wrapper classes
4. Set up automatic instrumentation system

### Phase 2: Dynamic Instrumentation

1. Create wrapper for `EmailClassifier` with LLM span injection
2. Create wrapper for `EmailGenerator` with response generation tracing
3. Create wrapper for `ProductInformationService` with RAG tracing
4. Create wrapper for `EmailClient` with IMAP/SMTP tracing

### Phase 3: Integration

1. Replace imports in `main.py` with wrapped versions
2. Ensure all existing endpoints work unchanged
3. Add top-level workflow spans to main endpoints
4. Test complete tracing pipeline

## Self-Contained Implementation Example

```python
# src/brewops/tracing/wrappers.py
import openlit
from opentelemetry import trace
from typing import Any, Dict
import functools

# Initialize OpenLIT
openlit.init()
tracer = trace.get_tracer(__name__)

class TracingClassifierWrapper:
    """Self-contained wrapper for EmailClassifier"""

    def __init__(self, original_classifier_class):
        self.original_class = original_classifier_class

    def __call__(self, *args, **kwargs):
        # Create original instance
        instance = self.original_class(*args, **kwargs)

        # Wrap the classify_email method
        original_classify = instance.classify_email

        def traced_classify_email(email):
            with tracer.start_as_current_span("email_classification") as span:
                span.set_attribute("classification.model", instance.model)
                span.set_attribute("email.content_length", len(email.body))

                with tracer.start_as_current_span("llm_call") as llm_span:
                    llm_span.set_attribute("llm.model", instance.model)

                    # Call original method
                    result = original_classify(email)

                    if result.get("success"):
                        span.set_attribute("confidence_score", result.get("confidence", 0))

                    return result

        # Replace method with traced version
        instance.classify_email = traced_classify_email
        return instance

# Usage in main.py:
from brewops.classifier import EmailClassifier as _OriginalClassifier
from brewops.tracing.wrappers import TracingClassifierWrapper

# Replace the class with wrapped version
EmailClassifier = TracingClassifierWrapper(_OriginalClassifier)
```

## Expected Benefits

- **Performance Visibility**: See exactly where time is spent in email processing
- **Cost Tracking**: Monitor token usage and API costs across different operations
- **Error Detection**: Quickly identify LLM failures and integration issues
- **Quality Monitoring**: Track classification accuracy and response quality over time
- **Optimization Opportunities**: Identify bottlenecks and expensive operations
