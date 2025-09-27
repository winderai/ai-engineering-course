import os
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from brewops.email_client import EmailClient, EmailMessage
from brewops.classifier import EmailClassifier
from brewops.email_generator import EmailGenerator, EmailGenerationRequest, EmailType
from brewops.domain_logic import BreweryDomainLogic
from brewops.log import setup_logging


# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Brewery Operations Hub",
    description="A demo application for processing brewery operations emails and RAG-powered information services",
    version="0.1.0",
)

# Initialize services at startup
startup_time = time.time()


def create_app():
    return app


def create_email_snippet(body: str, max_length: int = 150) -> str:
    """Create a snippet from email body content.

    Args:
        body: Full email body text
        max_length: Maximum length of snippet

    Returns:
        Truncated snippet with ellipsis if needed
    """
    if not body:
        return ""

    # Remove extra whitespace and newlines
    cleaned = " ".join(body.split())

    # Truncate if too long
    if len(cleaned) <= max_length:
        return cleaned

    # Find last complete word within limit
    truncated = cleaned[:max_length]
    last_space = truncated.rfind(" ")

    if last_space > max_length * 0.8:  # If we have a reasonable break point
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


@app.get("/")
async def root():
    return {"message": "Welcome to the Brewery Operations Hub"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "brewery-ops"}


@app.get("/emails/all")
async def get_all_emails():
    """Get list of all emails with content snippets from the configured email account."""
    # Get email configuration from environment
    server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")

    if not username or not password:
        raise HTTPException(
            status_code=500,
            detail="Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD environment variables.",
        )

    # Create email client and fetch emails
    client = EmailClient(server)

    try:
        if not client.connect(username, password):
            raise HTTPException(
                status_code=500, detail="Failed to connect to email server"
            )

        if not client.select_inbox():
            raise HTTPException(status_code=500, detail="Failed to select inbox")

        emails = client.fetch_all_emails_full()

        # Format response with snippets
        formatted_emails = [
            {
                "sender_name": email.sender_name,
                "sender_email": email.sender_email,
                "subject": email.subject,
                "snippet": create_email_snippet(email.body),
                "timestamp": email.timestamp.isoformat() if email.timestamp else None,
                "message_id": email.message_id,
                "imap_uid": email.imap_uid,
            }
            for email in emails
        ]

        return {"count": len(formatted_emails), "emails": formatted_emails}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching emails: {str(e)}")
    finally:
        client.disconnect()


@app.get("/emails/test")
async def test_email_connection():
    """Test email connection and return connection status."""
    server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")

    if not username or not password:
        return {
            "status": "error",
            "message": "Email credentials not configured",
            "details": "Set EMAIL_USERNAME and EMAIL_PASSWORD environment variables",
        }

    client = EmailClient(server)

    try:
        # Test connection
        if not client.connect(username, password):
            return {
                "status": "error",
                "message": "Authentication failed",
                "server": server,
                "username": username,
            }

        # Test inbox selection
        if not client.select_inbox():
            return {
                "status": "error",
                "message": "Failed to select inbox",
                "server": server,
                "username": username,
            }

        # Get email count
        emails = client.fetch_all_emails_full()

        return {
            "status": "success",
            "message": "Email connection successful",
            "server": server,
            "username": username,
            "email_count": len(emails),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}",
            "server": server,
            "username": username,
        }
    finally:
        client.disconnect()


class EmailInput(BaseModel):
    """Input model for email classification."""

    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    message_id: str


class BatchEmailInput(BaseModel):
    """Input model for batch email classification."""

    emails: List[EmailInput]


class EmailGenerateInput(BaseModel):
    """Input model for email generation."""

    email_type: str
    context: str
    recipient_name: Optional[str] = None
    sender_name: Optional[str] = None
    additional_details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "email_type": "customer_service_response",
                    "context": "Customer complained that their IPA tasted flat and wants a refund. They purchased it last week and seem reasonable and polite.",
                    "recipient_name": "John Smith",
                    "sender_name": "Sarah Wilson",
                },
                {
                    "email_type": "customer_service_response",
                    "context": "Customer complained that their recent beer purchase had an off-taste. They want a refund or replacement. Customer seems reasonable and polite.",
                    "recipient_name": "John Smith",
                    "sender_name": "Emma Wilson",
                },
                {
                    "email_type": "quality_control_alert",
                    "context": "Batch #2024-045 of our Wheat Beer shows signs of contamination during quality testing. Immediate action required to prevent distribution.",
                    "sender_name": "Quality Control Team",
                    "additional_details": {
                        "batch_number": "2024-045",
                        "product": "Wheat Beer",
                        "severity": "critical",
                    },
                },
            ]
        }


@app.post("/classify/email")
async def classify_single_email(email_input: EmailInput) -> Dict[str, Any]:
    """Classify a single email using Ollama.

    Returns classification result with category, explanation, confidence,
    response time, and model information.
    """
    # Create EmailMessage from input
    email = EmailMessage(
        sender_name=email_input.sender_name or "",
        sender_email=email_input.sender_email or "",
        subject=email_input.subject or "",
        body=email_input.body or "",
        message_id=email_input.message_id,
    )

    # Initialize classifier with default model
    model = os.getenv("OLLAMA_MODEL", "ollama/qwen3:1.7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    classifier = EmailClassifier(model=model, timeout=timeout)

    # Classify the email
    result = classifier.classify_email(email)

    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "Classification failed")
        )

    return result


@app.post("/classify/batch")
async def classify_batch_emails(batch_input: BatchEmailInput) -> Dict[str, Any]:
    """Classify multiple emails in batch.

    Returns a list of classification results along with summary statistics.
    """
    if not batch_input.emails:
        raise HTTPException(status_code=400, detail="No emails provided")

    # Initialize classifier
    model = os.getenv("OLLAMA_MODEL", "ollama/qwen3:1.7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    classifier = EmailClassifier(model=model, timeout=timeout)

    results = []
    total_time = 0.0
    successful = 0

    for email_input in batch_input.emails:
        # Create EmailMessage from input
        email = EmailMessage(
            sender_name=email_input.sender_name or "",
            sender_email=email_input.sender_email or "",
            subject=email_input.subject or "",
            body=email_input.body or "",
            message_id=email_input.message_id,
        )

        # Classify the email
        result = classifier.classify_email(email)
        result["message_id"] = email_input.message_id
        results.append(result)

        total_time += result["response_time"]
        if result["success"]:
            successful += 1

    return {
        "count": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "total_time": total_time,
        "average_time": total_time / len(results) if results else 0,
        "success_rate": (successful / len(results)) * 100 if results else 0,
        "results": results,
    }


@app.get("/classify/test")
async def test_ollama_connection() -> Dict[str, Any]:
    """Test connection to Ollama server.

    Returns connection status and diagnostic information.
    """
    model = os.getenv("OLLAMA_MODEL", "ollama/qwen3:1.7b")
    classifier = EmailClassifier(model=model)

    result = classifier.test_connection()

    if not result["success"]:
        return {
            **result,
            "troubleshooting": [
                "Check if Ollama is running: ollama serve",
                "Check if model is available: ollama list",
                f"Pull the model if needed: ollama pull {model.replace('ollama/', '')}",
                f"Test manually: ollama run {model.replace('ollama/', '')} 'Hello'",
            ],
        }

    return result


@app.get("/emails/classify-all")
async def classify_all_emails() -> Dict[str, Any]:
    """Fetch all emails from inbox and classify them.

    This endpoint combines email fetching and classification.
    """
    # Get email configuration
    server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")

    if not username or not password:
        raise HTTPException(
            status_code=500,
            detail="Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD environment variables.",
        )

    # Create email client and fetch emails
    client = EmailClient(server)

    try:
        if not client.connect(username, password):
            raise HTTPException(
                status_code=500, detail="Failed to connect to email server"
            )

        if not client.select_inbox():
            raise HTTPException(status_code=500, detail="Failed to select inbox")

        emails = client.fetch_all_emails_full()

        if not emails:
            return {"count": 0, "message": "No emails found in inbox", "emails": []}

        # Initialize classifier
        model = os.getenv("OLLAMA_MODEL", "ollama/qwen3:1.7b")
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        classifier = EmailClassifier(model=model, timeout=timeout)

        # Classify each email
        classified_emails = []
        total_time = 0.0
        successful = 0

        for email in emails:
            result = classifier.classify_email(email)

            classified_email = {
                "sender_name": email.sender_name,
                "sender_email": email.sender_email,
                "subject": email.subject,
                "snippet": create_email_snippet(email.body),
                "timestamp": email.timestamp.isoformat() if email.timestamp else None,
                "message_id": email.message_id,
                "classification": {
                    "category": result["category"],
                    "explanation": result["explanation"],
                    "confidence": result["confidence"],
                    "success": result["success"],
                },
            }

            classified_emails.append(classified_email)
            total_time += result["response_time"]
            if result["success"]:
                successful += 1

        return {
            "count": len(classified_emails),
            "successful_classifications": successful,
            "failed_classifications": len(classified_emails) - successful,
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(classified_emails)
            if classified_emails
            else 0,
            "emails": classified_emails,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing emails: {str(e)}"
        )
    finally:
        client.disconnect()


@app.post(
    "/generate/email",
    summary="Generate AI-powered brewery operation emails",
    description="""
    Generate professional emails for various brewery operations using AI.
    
    This endpoint takes a context description and email type, then generates
    a complete email with subject line and body content tailored for brewery
    business communications.
    
    **Available Email Types:**
    - `supplier_order` - Generate orders to suppliers
    - `supplier_quality_issue` - Report quality issues to suppliers
    - `customer_service_response` - Respond to customer inquiries
    - `quality_control_alert` - Internal quality control notifications
    - `inventory_alert` - Inventory level notifications
    - `maintenance_schedule` - Equipment maintenance scheduling
    - `regulatory_compliance` - Regulatory compliance communications
    - `general_response` - General business communications
    
    **Response includes:**
    - Generated subject line
    - Email body content
    - Processing metadata (response time, model used)
    """,
    response_description="Generated email with subject, body, and metadata",
    responses={
        200: {
            "description": "Email generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "subject": "Response to Your IPA Tasting Concern",
                        "body": "Dear John Smith,\n\nWe sincerely apologize for the disappointment you experienced with your recent IPA. We value your feedback and understand how frustrating a flat-tasting beverage can be.\n\nYour purchase was made last week, and we appreciate your patience. We will process a refund for the full amount of your order. If you'd like, you may return the product for a hassle-free refund.\n\nWe're happy to offer a 10% discount on your next purchase as a token of our appreciation. Please contact us if you have any other concerns.\n\nThank you for your understanding and for choosing our brewery.\n\nBest regards,\nSarah Wilson\nCustomer Service Representative",
                        "full_content": "Subject: Response to Your IPA Tasting Concern\n\nDear John Smith,\n\nWe sincerely apologize for the disappointment...",
                        "email_type": "customer_service_response",
                        "response_time": 2.34,
                        "model": "qwen3:1.7b",
                    }
                }
            },
        },
        400: {
            "description": "Invalid email type provided",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email_type. Must be one of: ['supplier_order', 'supplier_quality_issue', 'customer_service_response', 'quality_control_alert', 'inventory_alert', 'maintenance_schedule', 'regulatory_compliance', 'general_response']"
                    }
                }
            },
        },
        500: {
            "description": "AI generation failed or server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not connect to Ollama server"}
                }
            },
        },
    },
)
async def generate_email(email_input: EmailGenerateInput) -> Dict[str, Any]:
    """Generate an email using AI based on the provided context and type."""
    try:
        # Validate email type
        try:
            email_type = EmailType(email_input.email_type)
        except ValueError:
            valid_types = [e.value for e in EmailType]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email_type. Must be one of: {valid_types}",
            )

        # Create generation request
        request = EmailGenerationRequest(
            email_type=email_type,
            context=email_input.context,
            recipient_name=email_input.recipient_name,
            sender_name=email_input.sender_name,
            additional_details=email_input.additional_details,
        )

        # Initialize generator
        model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        generator = EmailGenerator(model=model, timeout=timeout)

        # Generate email
        result = generator.generate_email(request)

        if not result["success"]:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Email generation failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")


@app.get(
    "/generate/templates",
    summary="Get available email templates",
    description="""
    Retrieve a list of all available email templates with descriptions and usage guidance.
    
    This endpoint returns information about each email type, including:
    - Template name and description
    - Required context information
    - Usage examples and best practices
    
    Use this endpoint to understand what types of emails can be generated
    and what information is needed for each type.
    """,
    response_description="List of available email templates with descriptions",
    responses={
        200: {
            "description": "Email templates retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "templates": {
                            "supplier_order": {
                                "name": "Supplier Order",
                                "description": "Generate emails for placing orders with suppliers",
                                "required_context": "Order details, quantities, delivery requirements",
                            },
                            "customer_service_response": {
                                "name": "Customer Service Response",
                                "description": "Generate customer service email responses",
                                "required_context": "Customer inquiry or issue, proposed resolution",
                            },
                        },
                        "total_count": 8,
                    }
                }
            },
        }
    },
)
async def get_email_templates() -> Dict[str, Any]:
    """Get available email templates and their descriptions."""
    generator = EmailGenerator()
    return generator.get_email_templates()


@app.get(
    "/generate/test",
    summary="Test email generation service",
    description="""
    Test the connection to the AI email generation service (Ollama).
    
    This endpoint verifies that:
    - Ollama server is running and accessible
    - The configured AI model is available
    - The service can respond to requests
    
    Use this endpoint to troubleshoot email generation issues or verify
    system setup before attempting to generate emails.
    """,
    response_description="Connection test results with diagnostic information",
    responses={
        200: {
            "description": "Connection test results (success or failure)",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Successful connection",
                            "value": {
                                "success": True,
                                "message": "Successfully connected to Ollama",
                                "available_models": ["qwen3:1.7b", "llama2", "mistral"],
                                "configured_model": "qwen3:1.7b",
                            },
                        },
                        "failure": {
                            "summary": "Connection failed",
                            "value": {
                                "success": False,
                                "error": "Could not connect to Ollama server at http://localhost:11434",
                                "troubleshooting": [
                                    "Check if Ollama is running: ollama serve",
                                    "Check if model is available: ollama list",
                                    "Pull the model if needed: ollama pull qwen3:1.7b",
                                    "Test manually: ollama run qwen3:1.7b 'Hello'",
                                ],
                            },
                        },
                    }
                }
            },
        }
    },
)
async def test_email_generation() -> Dict[str, Any]:
    """Test connection to email generation service (Ollama)."""
    model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
    generator = EmailGenerator(model=model)

    result = generator.test_connection()

    if not result["success"]:
        return {
            **result,
            "troubleshooting": [
                "Check if Ollama is running: ollama serve",
                "Check if model is available: ollama list",
                f"Pull the model if needed: ollama pull {model.replace('ollama/', '')}",
                f"Test manually: ollama run {model.replace('ollama/', '')} 'Hello'",
            ],
        }

    return result


@app.get("/emails/process-all")
async def process_all_emails() -> Dict[str, Any]:
    """Fetch all emails from inbox and process them through the complete workflow.

    This endpoint demonstrates the full classify → decide → act pipeline by:
    1. Fetching all emails from the configured inbox
    2. Processing each email through the domain logic workflow
    3. Applying Gmail labels based on classification
    4. Taking appropriate business actions (responses, alerts, review queuing)
    5. Sending email responses when applicable
    6. Returning comprehensive processing statistics

    Returns comprehensive processing report with statistics and results.
    """
    # Get email configuration
    server = os.getenv("EMAIL_SERVER", "imap.gmail.com")
    username = os.getenv("EMAIL_USERNAME")
    password = os.getenv("EMAIL_PASSWORD")

    if not username or not password:
        raise HTTPException(
            status_code=500,
            detail="Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD environment variables.",
        )

    # Get configuration settings
    model = os.getenv("OLLAMA_MODEL", "ollama/qwen3:1.7b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    auto_send_responses = os.getenv("AUTO_SEND_RESPONSES", "true").lower() == "true"
    auto_label_emails = os.getenv("AUTO_LABEL_EMAILS", "true").lower() == "true"

    # Initialize domain logic
    domain_logic = BreweryDomainLogic(
        model=model,
        timeout=timeout,
        auto_send_responses=auto_send_responses,
        auto_label_emails=auto_label_emails,
    )

    # Create email client and fetch emails
    client = EmailClient(server)

    try:
        if not client.connect(username, password):
            raise HTTPException(
                status_code=500, detail="Failed to connect to email server"
            )

        if not client.select_inbox():
            raise HTTPException(status_code=500, detail="Failed to select inbox")

        emails = client.fetch_all_emails_full()

        if not emails:
            return {
                "total_emails": 0,
                "message": "No emails found in inbox",
                "successful_workflows": 0,
                "failed_workflows": 0,
                "total_processing_time": 0.0,
                "average_time_per_email": 0.0,
                "success_rate": 0.0,
                "actions_summary": {},
                "classification_summary": {},
                "email_integration_summary": {
                    "emails_sent": 0,
                    "emails_failed_to_send": 0,
                    "labels_applied": 0,
                    "labels_failed": 0,
                    "new_labels_created": 0,
                },
                "processed_emails": [],
            }

        # Process each email through workflow
        processed_emails = []
        successful_workflows = 0
        failed_workflows = 0
        total_processing_time = 0.0

        actions_summary = {}
        classification_summary = {}
        emails_sent = 0
        emails_failed_to_send = 0
        labels_applied = 0
        labels_failed = 0

        for email in emails:
            try:
                workflow_result = domain_logic.process_email_workflow(email, client)

                # Update counters
                if workflow_result.workflow_success:
                    successful_workflows += 1
                else:
                    failed_workflows += 1

                total_processing_time += workflow_result.total_processing_time

                # Update classification summary
                category = workflow_result.classification.get("category", "UNKNOWN")
                classification_summary[category] = (
                    classification_summary.get(category, 0) + 1
                )

                # Update actions summary
                for action in workflow_result.actions_taken:
                    action_type = action.action_type.value
                    actions_summary[action_type] = (
                        actions_summary.get(action_type, 0) + 1
                    )

                # Update email integration summary
                if workflow_result.label_success:
                    labels_applied += 1
                elif workflow_result.label_applied is not None:
                    labels_failed += 1

                if workflow_result.email_send_success:
                    emails_sent += 1
                elif workflow_result.email_sent is not None:
                    emails_failed_to_send += 1

                # Add to processed emails list with summary info
                processed_emails.append(
                    {
                        "email_id": workflow_result.email_id,
                        "sender": f"{email.sender_name} ({email.sender_email})",
                        "subject": email.subject,
                        "snippet": create_email_snippet(email.body),
                        "timestamp": email.timestamp.isoformat()
                        if email.timestamp
                        else None,
                        "classification": {
                            "category": category,
                            "confidence": workflow_result.classification.get(
                                "confidence", 0.0
                            ),
                            "explanation": workflow_result.classification.get(
                                "explanation", ""
                            ),
                            "success": workflow_result.classification.get(
                                "success", False
                            ),
                        },
                        "actions_taken": [
                            {
                                "action_type": action.action_type.value,
                                "success": action.success,
                                "message": action.message,
                                "execution_time": action.execution_time,
                            }
                            for action in workflow_result.actions_taken
                        ],
                        "workflow_success": workflow_result.workflow_success,
                        "processing_time": workflow_result.total_processing_time,
                        "next_steps": workflow_result.next_steps,
                        "label_applied": workflow_result.label_applied,
                        "email_sent": workflow_result.email_sent,
                    }
                )

            except Exception as e:
                failed_workflows += 1
                logger.error(f"Failed to process email {email.message_id}: {e}")

                processed_emails.append(
                    {
                        "email_id": email.message_id,
                        "sender": f"{email.sender_name} ({email.sender_email})",
                        "subject": email.subject,
                        "snippet": create_email_snippet(email.body),
                        "timestamp": email.timestamp.isoformat()
                        if email.timestamp
                        else None,
                        "classification": {"success": False, "error": str(e)},
                        "actions_taken": [],
                        "workflow_success": False,
                        "processing_time": 0.0,
                        "next_steps": ["Manual intervention required"],
                        "label_applied": None,
                        "email_sent": None,
                    }
                )

        # Calculate final statistics
        total_emails = len(processed_emails)
        success_rate = (
            (successful_workflows / total_emails * 100) if total_emails > 0 else 0.0
        )
        average_time_per_email = (
            total_processing_time / total_emails if total_emails > 0 else 0.0
        )

        # Estimate new labels created (simplified - in reality would track label creation)
        unique_labels = len(
            set(
                result.get("label_applied")
                for result in processed_emails
                if result.get("label_applied")
            )
        )

        return {
            "total_emails": total_emails,
            "successful_workflows": successful_workflows,
            "failed_workflows": failed_workflows,
            "total_processing_time": round(total_processing_time, 2),
            "average_time_per_email": round(average_time_per_email, 2),
            "success_rate": round(success_rate, 1),
            "actions_summary": actions_summary,
            "classification_summary": classification_summary,
            "email_integration_summary": {
                "emails_sent": emails_sent,
                "emails_failed_to_send": emails_failed_to_send,
                "labels_applied": labels_applied,
                "labels_failed": labels_failed,
                "new_labels_created": unique_labels,
            },
            "processed_emails": processed_emails,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing emails: {str(e)}"
        )
    finally:
        client.disconnect()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("brewops.main:app", host="0.0.0.0", port=8000, reload=True)
