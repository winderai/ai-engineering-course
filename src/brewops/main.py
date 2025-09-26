import os
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from brewops.email_client import EmailClient, EmailMessage
from brewops.classifier import EmailClassifier
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

    """Reload and reindex all products."""
    try:
        success = product_service.reindex_products()
        if success:
            return {
                "status": "success",
                "message": "Products reindexed successfully",
                "count": len(product_service.products),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reindex products")
    except Exception as e:
        logger.error(f"Error reindexing products: {e}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("brewops.main:app", host="0.0.0.0", port=8000, reload=True)
