import time
from typing import Dict, Any, Optional
from enum import Enum
import requests
import json
import re


class EmailType(Enum):
    """Types of brewery operation emails that can be generated."""

    SUPPLIER_ORDER = "supplier_order"
    SUPPLIER_QUALITY_ISSUE = "supplier_quality_issue"
    CUSTOMER_SERVICE_RESPONSE = "customer_service_response"
    QUALITY_CONTROL_ALERT = "quality_control_alert"
    INVENTORY_ALERT = "inventory_alert"
    MAINTENANCE_SCHEDULE = "maintenance_schedule"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    GENERAL_RESPONSE = "general_response"


class EmailGenerationRequest:
    """Request object for email generation."""

    def __init__(
        self,
        email_type: EmailType,
        context: str,
        recipient_name: Optional[str] = None,
        sender_name: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None,
    ):
        self.email_type = email_type
        self.context = context
        self.recipient_name = recipient_name
        self.sender_name = sender_name
        self.additional_details = additional_details or {}


class EmailGenerator:
    """Generates brewery operation emails using Ollama."""

    def __init__(self, model: str = "qwen3:1.7b", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.base_url = "http://localhost:11434"

    def _build_prompt(self, request: EmailGenerationRequest) -> str:
        """Build the prompt for email generation based on the request."""

        # Base prompt templates for different email types
        prompts = {
            EmailType.SUPPLIER_ORDER: (
                "Generate a professional email to a brewery supplier regarding an order. "
                "The email should be clear, specific about requirements, and include delivery details."
            ),
            EmailType.SUPPLIER_QUALITY_ISSUE: (
                "Generate a professional email to a brewery supplier regarding a quality issue. "
                "The email should be diplomatic but firm, clearly describe the issue, and request corrective action."
            ),
            EmailType.CUSTOMER_SERVICE_RESPONSE: (
                "Generate a professional customer service email response for a brewery. "
                "The email should be helpful, empathetic, and provide clear next steps."
            ),
            EmailType.QUALITY_CONTROL_ALERT: (
                "Generate a professional internal email regarding a quality control issue. "
                "The email should be urgent, clear about the issue, and outline immediate actions needed."
            ),
            EmailType.INVENTORY_ALERT: (
                "Generate a professional email regarding brewery inventory levels. "
                "The email should be clear about current status and required actions."
            ),
            EmailType.MAINTENANCE_SCHEDULE: (
                "Generate a professional email regarding brewery equipment maintenance. "
                "The email should include schedule details and any required preparations."
            ),
            EmailType.REGULATORY_COMPLIANCE: (
                "Generate a professional email regarding brewery regulatory compliance. "
                "The email should be formal, accurate, and include all required information."
            ),
            EmailType.GENERAL_RESPONSE: (
                "Generate a professional brewery business email response. "
                "The email should be appropriate for the context and maintain a professional tone."
            ),
        }

        base_prompt = prompts.get(
            request.email_type, prompts[EmailType.GENERAL_RESPONSE]
        )

        prompt = f"""You are a professional email writer for a brewery operations team.

{base_prompt}

Context: {request.context}

Additional requirements:
- Use a professional but friendly tone
- Include appropriate greeting and closing
- Be specific and actionable
- Keep the email concise and focused
"""

        if request.recipient_name:
            prompt += f"- Address the email to: {request.recipient_name}\n"

        if request.sender_name:
            prompt += f"- Sign the email from: {request.sender_name}\n"

        if request.additional_details:
            prompt += f"- Additional context: {json.dumps(request.additional_details, indent=2)}\n"

        prompt += "\nGenerate only the email content (subject line and body). Do not include any explanations, think, reasoning, or additional text. Do not use <think> tags."

        return prompt

    def _strip_think_tags(self, text: str) -> str:
        """Strip think tags and content from generated text."""
        # Remove <think>...</think> blocks (including multiline)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove any remaining think tags
        text = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)
        # Clean up extra whitespace
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)  # Multiple newlines to double
        text = text.strip()
        return text

    def generate_email(self, request: EmailGenerationRequest) -> Dict[str, Any]:
        """Generate an email based on the request."""
        start_time = time.time()

        try:
            prompt = self._build_prompt(request)

            # Make request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model.replace("ollama/", ""),
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
                timeout=self.timeout,
            )

            response_time = time.time() - start_time

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": response_time,
                    "model": self.model,
                }

            result = response.json()
            generated_text = result.get("response", "").strip()

            # Strip any think tags that might have made it through
            generated_text = self._strip_think_tags(generated_text)

            if not generated_text:
                return {
                    "success": False,
                    "error": "Empty response from model",
                    "response_time": response_time,
                    "model": self.model,
                }

            # Try to parse subject and body
            subject, body = self._parse_email_content(generated_text)

            return {
                "success": True,
                "subject": subject,
                "body": body,
                "full_content": generated_text,
                "email_type": request.email_type.value,
                "response_time": response_time,
                "model": self.model,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Request timeout after {self.timeout} seconds",
                "response_time": time.time() - start_time,
                "model": self.model,
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Could not connect to Ollama server",
                "response_time": time.time() - start_time,
                "model": self.model,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response_time": time.time() - start_time,
                "model": self.model,
            }

    def _parse_email_content(self, content: str) -> tuple[str, str]:
        """Parse email content to extract subject and body."""
        lines = content.split("\n")

        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            line = line.strip()
            if not line:
                if in_body:
                    body_lines.append("")
                continue

            # Look for subject line patterns
            if not subject and not in_body:
                if line.lower().startswith(("subject:", "subj:", "re:", "fwd:")):
                    subject = line.split(":", 1)[1].strip() if ":" in line else line
                    continue
                elif line and not line.startswith(("dear", "hi", "hello", "greetings")):
                    # If no explicit subject found, use first line as subject
                    subject = line
                    continue

            # Everything else is body
            in_body = True
            body_lines.append(line)

        # If no subject found, generate a generic one
        if not subject:
            subject = "Brewery Operations Communication"

        body = "\n".join(body_lines).strip()

        return subject, body

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]

                return {
                    "success": True,
                    "message": "Successfully connected to Ollama",
                    "available_models": model_names,
                    "configured_model": self.model,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Could not connect to Ollama server at http://localhost:11434",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }

    def get_email_templates(self) -> Dict[str, Any]:
        """Get available email types and their descriptions."""
        templates = {
            EmailType.SUPPLIER_ORDER.value: {
                "name": "Supplier Order",
                "description": "Generate emails for placing orders with suppliers",
                "required_context": "Order details, quantities, delivery requirements",
            },
            EmailType.SUPPLIER_QUALITY_ISSUE.value: {
                "name": "Supplier Quality Issue",
                "description": "Generate emails reporting quality issues to suppliers",
                "required_context": "Description of quality issue, batch/lot numbers, corrective action needed",
            },
            EmailType.CUSTOMER_SERVICE_RESPONSE.value: {
                "name": "Customer Service Response",
                "description": "Generate customer service email responses",
                "required_context": "Customer inquiry or issue, proposed resolution",
            },
            EmailType.QUALITY_CONTROL_ALERT.value: {
                "name": "Quality Control Alert",
                "description": "Generate internal quality control alert emails",
                "required_context": "Quality issue description, affected products, immediate actions",
            },
            EmailType.INVENTORY_ALERT.value: {
                "name": "Inventory Alert",
                "description": "Generate inventory level alert emails",
                "required_context": "Current inventory levels, items affected, restocking requirements",
            },
            EmailType.MAINTENANCE_SCHEDULE.value: {
                "name": "Maintenance Schedule",
                "description": "Generate maintenance scheduling emails",
                "required_context": "Equipment to maintain, schedule, required preparations",
            },
            EmailType.REGULATORY_COMPLIANCE.value: {
                "name": "Regulatory Compliance",
                "description": "Generate regulatory compliance emails",
                "required_context": "Compliance requirement, deadlines, required documentation",
            },
            EmailType.GENERAL_RESPONSE.value: {
                "name": "General Response",
                "description": "Generate general business email responses",
                "required_context": "Context of the communication and desired response",
            },
        }

        return {
            "success": True,
            "templates": templates,
            "total_count": len(templates),
        }
