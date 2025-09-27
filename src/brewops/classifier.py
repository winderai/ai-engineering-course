"""Email classification module using Ollama via litellm."""

import time
from typing import Dict, Any, Tuple
import logging
from litellm import completion
from brewops.email_client import EmailMessage

logger = logging.getLogger(__name__)


class EmailClassifier:
    """Classifies brewery operation emails using local Ollama models."""

    def __init__(self, model: str = "ollama/qwen3:1.7b", timeout: int = 30):
        """Initialize the email classifier.

        Args:
            model: Ollama model to use (default: ollama/qwen3:1.7b)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.timeout = timeout
        self.prompt_template = self._create_prompt_template()

    def _create_prompt_template(self) -> str:
        """Create the classification prompt template.

        Returns:
            Formatted prompt template string
        """
        return """Email: "{subject}" - {body}

Choose one:
URGENT_ISSUE - equipment failure/safety issue requiring immediate attention
SUPPLY_ORDER - purchasing requests from suppliers, inventory orders
SCHEDULE - meetings/shifts/calendar changes
CUSTOMER - customer inquiries, recommendations, orders, complaints, tours, feedback, product questions
MAINTENANCE - routine equipment servicing and repairs
OTHER - everything else

Answer:"""

    def classify_email(self, email: EmailMessage) -> Dict[str, Any]:
        """Classify an email using Ollama.

        Args:
            email: EmailMessage object to classify

        Returns:
            Dictionary containing classification results and metadata
        """
        start_time = time.time()

        try:
            # Format the prompt with email content
            prompt = self.prompt_template.format(
                subject=email.subject or "No Subject",
                body=email.body[:500]
                if email.body
                else "No content",  # Limit body length
            )

            # Call Ollama via litellm
            response = completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that classifies emails. Respond directly without thinking out loud.",
                    },
                    {"role": "user", "content": prompt},
                ],
                timeout=self.timeout,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=20,  # Keep very short for just category
            )

            # Extract response text
            response_content = response.choices[0].message.content  # type: ignore
            response_text = response_content.strip() if response_content else ""

            # Debug: log the raw response
            logger.info(f"Raw model response: {repr(response_text)}")

            # Parse the response
            category, explanation = self._parse_response(response_text)

            end_time = time.time()
            response_time = end_time - start_time

            logger.info(f"Email classified as {category} in {response_time:.2f}s")

            return {
                "category": category,
                "explanation": explanation,
                "confidence": "high" if category != "OTHER" else "medium",
                "response_time": response_time,
                "model_used": self.model,
                "success": True,
            }

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time

            logger.error(f"Classification failed after {response_time:.2f}s: {e}")

            return {
                "category": "ERROR",
                "explanation": f"Classification failed: {str(e)}",
                "confidence": "none",
                "response_time": response_time,
                "model_used": self.model,
                "success": False,
                "error": str(e),
            }

    def _parse_response(self, response_text: str) -> Tuple[str, str]:
        """Parse the model response to extract category and explanation.

        Args:
            response_text: Raw response from the model

        Returns:
            Tuple of (category, explanation)
        """
        # Clean the response and handle thinking tokens
        cleaned_response = response_text.strip()

        # Remove thinking tokens if present
        if "<think>" in cleaned_response:
            if "</think>" in cleaned_response:
                # Extract content after </think>
                cleaned_response = cleaned_response.split("</think>", 1)[1].strip()
            else:
                # If no closing tag, remove everything from <think> onwards
                cleaned_response = cleaned_response.split("<think>", 1)[0].strip()

        # Valid categories
        valid_categories = {
            "URGENT_ISSUE",
            "SUPPLY_ORDER",
            "SCHEDULE",
            "CUSTOMER",
            "MAINTENANCE",
            "OTHER",
        }

        # Look for any valid category in the response
        found_category = None
        for category in valid_categories:
            if category in cleaned_response.upper():
                found_category = category
                break

        if found_category:
            # Extract explanation after the category
            category_pos = cleaned_response.upper().find(found_category)
            explanation_part = cleaned_response[
                category_pos + len(found_category) :
            ].strip()

            # Clean up explanation
            if explanation_part.startswith(":") or explanation_part.startswith("-"):
                explanation_part = explanation_part[1:].strip()

            explanation = (
                explanation_part
                if explanation_part
                else f"Classified as {found_category.lower().replace('_', ' ')}"
            )
            return found_category, explanation

        # Final fallback
        return (
            "OTHER",
            f"Unable to parse classification from: {cleaned_response[:100]}...",
        )

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server.

        Returns:
            Dictionary with connection test results
        """
        start_time = time.time()

        try:
            # Simple test prompt
            test_prompt = "Hello"

            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": test_prompt}],
                timeout=10,  # Shorter timeout for connection test
                max_tokens=10,
            )

            response_content = response.choices[0].message.content  # type: ignore
            response_text = response_content.strip() if response_content else ""
            end_time = time.time()
            response_time = end_time - start_time

            # If we get any response, consider it successful
            success = len(response_text) > 0

            return {
                "success": success,
                "response_time": response_time,
                "model": self.model,
                "response": response_text,
                "message": "Ollama connection successful"
                if success
                else "No response from Ollama",
            }

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time

            return {
                "success": False,
                "response_time": response_time,
                "model": self.model,
                "error": str(e),
                "message": self._get_error_message(str(e)),
            }

    def _get_error_message(self, error_str: str) -> str:
        """Convert technical error to user-friendly message.

        Args:
            error_str: Technical error string

        Returns:
            User-friendly error message
        """
        error_lower = error_str.lower()

        if "connection" in error_lower or "refused" in error_lower:
            return "Cannot connect to Ollama. Is Ollama running? Try: ollama serve"
        elif "timeout" in error_lower:
            return "Ollama request timed out. The model might be loading or server is slow."
        elif "model" in error_lower and (
            "not found" in error_lower or "pull" in error_lower
        ):
            return f"Model {self.model} not found. Try: ollama pull qwen3:1.7b"
        elif "unauthorized" in error_lower or "auth" in error_lower:
            return "Authentication failed with Ollama server"
        else:
            return f"Ollama error: {error_str}"


def main() -> None:
    """Demo function to test email classification."""

    # Test Ollama connection first
    classifier = EmailClassifier()
    print("🔍 Testing Ollama connection...")
    print(f"Model: {classifier.model}")
    print(f"Timeout: {classifier.timeout}s")
    print("-" * 50)

    connection_test = classifier.test_connection()

    if not connection_test["success"]:
        print(f"❌ Connection failed: {connection_test['message']}")
        print(f"Error details: {connection_test.get('error', 'Unknown error')}")
        print(f"Response time: {connection_test['response_time']:.2f}s")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if Ollama is running: ollama serve")
        print("2. Check if model is available: ollama list")
        print("3. Pull the model if needed: ollama pull qwen3:1.7b")
        print("4. Test manually: ollama run qwen3:1.7b 'Hello'")
        return

    print("✅ Connected to Ollama successfully!")
    print(f"Response time: {connection_test['response_time']:.2f}s")
    print(f"Model response: {connection_test.get('response', 'N/A')}")

    # Test with multiple sample emails to demonstrate different categories
    print("\n📧 Testing classification with sample emails...")
    print("=" * 60)

    sample_emails = [
        EmailMessage(
            sender_name="Emergency Alert",
            sender_email="alerts@brewery.com",
            subject="URGENT: Fermentation tank #3 temperature alarm",
            body="The temperature alarm on fermentation tank #3 is going off. Current reading is 85°F which is way too high. Please check immediately!",
            message_id="urgent-123",
        ),
        EmailMessage(
            sender_name="Supply Manager",
            sender_email="supplies@brewery.com",
            subject="Hops order for next batch",
            body="We need to order 50 lbs of Cascade hops for the next IPA batch. The current supplier has them in stock at $12/lb. Please approve this purchase.",
            message_id="supply-456",
        ),
        EmailMessage(
            sender_name="Shift Supervisor",
            sender_email="supervisor@brewery.com",
            subject="Schedule change for weekend",
            body="Hi team, we need to move the weekend cleaning schedule from Saturday to Sunday due to a special event. Please let me know if this works for everyone.",
            message_id="schedule-789",
        ),
        EmailMessage(
            sender_name="Happy Customer",
            sender_email="customer@example.com",
            subject="Love your new IPA!",
            body="Just wanted to say the new Hoppy IPA is amazing! Where can I buy a case? Also, do you have any brewery tours available?",
            message_id="customer-101",
        ),
        EmailMessage(
            sender_name="Beer Enthusiast",
            sender_email="beerlovr@email.com",
            subject="Recommendation for light beer?",
            body="Hi! I'm new to craft beer and looking for something light and easy to drink. What would you recommend from your selection? Also, do you offer tastings?",
            message_id="customer-102",
        ),
        EmailMessage(
            sender_name="Party Planner",
            sender_email="events@partyco.com",
            subject="Order inquiry for wedding reception",
            body="Hello, I'm planning a wedding reception for 150 guests. Can you provide a quote for beer service? We're looking for a mix of light and dark beers. When is your earliest availability?",
            message_id="customer-103",
        ),
        EmailMessage(
            sender_name="Restaurant Owner",
            sender_email="owner@bistro.com",
            subject="Complaint about last delivery",
            body="The last delivery of your wheat beer was not up to standard - several bottles were flat and tasted off. We need to discuss this issue and potentially get a replacement shipment.",
            message_id="customer-104",
        ),
    ]

    total_time = 0
    successful_classifications = 0

    for i, email in enumerate(sample_emails, 1):
        print(f"\n--- Email {i} ---")
        print(f"From: {email.sender_name} <{email.sender_email}>")
        print(f"Subject: {email.subject}")
        print(
            f"Body: {email.body[:100]}..."
            if len(email.body) > 100
            else f"Body: {email.body}"
        )

        # Classify the email
        result = classifier.classify_email(email)
        total_time += result["response_time"]

        if result["success"]:
            successful_classifications += 1
            print(f"✅ Category: {result['category']}")
            print(f"📝 Explanation: {result['explanation']}")
            print(f"⏱️  Response time: {result['response_time']:.2f}s")
            print(f"🎯 Confidence: {result['confidence']}")
        else:
            print(f"❌ Classification failed: {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 CLASSIFICATION SUMMARY")
    print(f"Total emails processed: {len(sample_emails)}")
    print(f"Successful classifications: {successful_classifications}")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per email: {total_time / len(sample_emails):.2f}s")
    print(
        f"Success rate: {(successful_classifications / len(sample_emails)) * 100:.1f}%"
    )

    if successful_classifications == len(sample_emails):
        print("🎉 All classifications successful!")
    else:
        print("⚠️  Some classifications failed - check Ollama connection")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
