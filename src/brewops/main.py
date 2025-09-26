import os
import logging
import time
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from brewops.email_client import EmailClient
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("brewops.main:app", host="0.0.0.0", port=8000, reload=True)
