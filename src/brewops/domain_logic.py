"""Domain logic for brewery operations email processing workflow.

This module implements the core classify → decide → act pattern that orchestrates
the complete email processing workflow including AI classification, business rule
application, action execution, and email integration.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from .email_client import EmailClient, EmailMessage
from .classifier import EmailClassifier
from .email_generator import EmailGenerator, EmailGenerationRequest, EmailType

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be taken based on email classification."""
    GENERATE_RESPONSE = "generate_response"
    CREATE_ALERT = "create_alert"
    LOG_REVIEW = "log_review"


@dataclass
class ActionResult:
    """Result of executing an action."""
    action_type: ActionType
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0


@dataclass
class ProcessingRule:
    """Rule that maps email classifications to actions."""
    classification: str
    actions: List[ActionType]
    description: str


@dataclass
class WorkflowResult:
    """Complete result of processing an email through the workflow."""
    email_id: str
    classification: Dict[str, Any]
    actions_taken: List[ActionResult]
    total_processing_time: float
    workflow_success: bool
    next_steps: List[str]
    label_applied: Optional[str] = None
    label_success: bool = False
    email_sent: Optional[Dict[str, Any]] = None
    email_send_success: bool = False


class BreweryDomainLogic:
    """Orchestrates the complete email processing workflow for brewery operations."""

    def __init__(self, 
                 model: str = "ollama/qwen3:1.7b",
                 timeout: int = 30,
                 auto_send_responses: bool = True,
                 auto_label_emails: bool = True):
        """Initialize the domain logic orchestrator.
        
        Args:
            model: AI model to use for classification and generation
            timeout: Request timeout for AI operations
            auto_send_responses: Whether to automatically send generated responses
            auto_label_emails: Whether to automatically apply Gmail labels
        """
        self.model = model
        self.timeout = timeout
        self.auto_send_responses = auto_send_responses
        self.auto_label_emails = auto_label_emails
        
        # Initialize AI components
        self.classifier = EmailClassifier(model=model, timeout=timeout)
        self.generator = EmailGenerator(model=model, timeout=timeout)
        
        # Initialize business rules
        self.business_rules = self._initialize_business_rules()
        
        # Label mapping
        self.label_mapping = {
            "URGENT_ISSUE": "BrewOps/Urgent",
            "CUSTOMER": "BrewOps/Customer", 
            "SUPPLY_ORDER": "BrewOps/Supply",
            "SCHEDULE": "BrewOps/Schedule",
            "MAINTENANCE": "BrewOps/Maintenance",
            "OTHER": "BrewOps/Review"
        }

    def _initialize_business_rules(self) -> Dict[str, ProcessingRule]:
        """Initialize business rules mapping classifications to actions.
        
        Returns:
            Dictionary of classification -> ProcessingRule mappings
        """
        return {
            "URGENT_ISSUE": ProcessingRule(
                classification="URGENT_ISSUE",
                actions=[ActionType.CREATE_ALERT],
                description="Safety-critical issues require immediate escalation"
            ),
            "CUSTOMER": ProcessingRule(
                classification="CUSTOMER", 
                actions=[ActionType.GENERATE_RESPONSE],
                description="Customer satisfaction requires timely, personalized responses"
            ),
            "SUPPLY_ORDER": ProcessingRule(
                classification="SUPPLY_ORDER",
                actions=[ActionType.GENERATE_RESPONSE],
                description="Business continuity depends on supplier communication"
            ),
            "SCHEDULE": ProcessingRule(
                classification="SCHEDULE",
                actions=[ActionType.LOG_REVIEW],
                description="Coordination changes need human oversight"
            ),
            "MAINTENANCE": ProcessingRule(
                classification="MAINTENANCE",
                actions=[ActionType.LOG_REVIEW], 
                description="Technical decisions require expert evaluation"
            ),
            "OTHER": ProcessingRule(
                classification="OTHER",
                actions=[ActionType.LOG_REVIEW],
                description="Unknown categories default to manual review"
            )
        }

    def process_email_workflow(self, email: EmailMessage, 
                             email_client: Optional[EmailClient] = None) -> WorkflowResult:
        """Process a single email through the complete workflow.
        
        Args:
            email: EmailMessage to process
            email_client: Optional EmailClient for labeling and sending
            
        Returns:
            WorkflowResult with complete processing information
        """
        start_time = time.time()
        
        try:
            # Step 1: Classify email
            logger.info(f"Classifying email: {email.message_id}")
            classification = self.classifier.classify_email(email)
            
            if not classification.get("success", False):
                logger.warning(f"Classification failed for {email.message_id}: {classification.get('error', 'Unknown error')}")
                # Fallback to OTHER category
                classification = {
                    "success": True,
                    "category": "OTHER",
                    "confidence": 0.0,
                    "explanation": "Classification failed, defaulting to manual review",
                    "response_time": 0.0
                }
            
            category = classification["category"]
            logger.info(f"Email {email.message_id} classified as: {category}")
            
            # Step 2: Apply Gmail label if enabled and client available
            label_applied = None
            label_success = False
            if self.auto_label_emails and email_client and category in self.label_mapping and email.imap_uid:
                try:
                    label_name = self.label_mapping[category]
                    if email_client.apply_label(email.imap_uid, label_name):
                        label_applied = label_name
                        label_success = True
                        logger.info(f"Applied label '{label_name}' to email {email.message_id} (UID: {email.imap_uid})")
                    else:
                        logger.warning(f"Failed to apply label '{label_name}' to email {email.message_id} (UID: {email.imap_uid})")
                except Exception as e:
                    logger.error(f"Error applying label to email {email.message_id} (UID: {email.imap_uid}): {e}")
            
            # Step 3: Determine and execute actions based on business rules
            actions_taken = []
            if category in self.business_rules:
                rule = self.business_rules[category]
                logger.info(f"Applying rule for {category}: {rule.description}")
                
                for action_type in rule.actions:
                    action_result = self._execute_action(action_type, email, classification, email_client)
                    actions_taken.append(action_result)
            else:
                logger.warning(f"No rule found for category {category}, defaulting to manual review")
                action_result = ActionResult(
                    action_type=ActionType.LOG_REVIEW,
                    success=True,
                    message=f"No rule for category {category}, queued for manual review",
                    execution_time=0.0
                )
                actions_taken.append(action_result)
            
            # Step 4: Determine workflow success and next steps
            workflow_success = all(action.success for action in actions_taken)
            next_steps = self._determine_next_steps(category, actions_taken)
            
            total_time = time.time() - start_time
            
            # Check for email sending details
            email_sent = None
            email_send_success = False
            for action in actions_taken:
                if action.action_type == ActionType.GENERATE_RESPONSE and action.details:
                    email_sent = action.details.get("email_sent")
                    email_send_success = action.details.get("send_success", False)
                    break
            
            return WorkflowResult(
                email_id=email.message_id,
                classification=classification,
                actions_taken=actions_taken,
                total_processing_time=total_time,
                workflow_success=workflow_success,
                next_steps=next_steps,
                label_applied=label_applied,
                label_success=label_success,
                email_sent=email_sent,
                email_send_success=email_send_success
            )
            
        except Exception as e:
            logger.error(f"Workflow processing failed for email {email.message_id}: {e}")
            total_time = time.time() - start_time
            
            return WorkflowResult(
                email_id=email.message_id,
                classification={"success": False, "error": str(e)},
                actions_taken=[],
                total_processing_time=total_time,
                workflow_success=False,
                next_steps=["Manual intervention required due to processing error"],
                label_applied=None,
                label_success=False,
                email_sent=None,
                email_send_success=False
            )

    def _execute_action(self, action_type: ActionType, email: EmailMessage, 
                       classification: Dict[str, Any],
                       email_client: Optional[EmailClient] = None) -> ActionResult:
        """Execute a specific action based on type.
        
        Args:
            action_type: Type of action to execute
            email: Original email message
            classification: Classification result
            email_client: Optional email client for sending responses
            
        Returns:
            ActionResult with execution details
        """
        start_time = time.time()
        
        try:
            if action_type == ActionType.GENERATE_RESPONSE:
                return self._execute_generate_response(email, classification, email_client, start_time)
            elif action_type == ActionType.CREATE_ALERT:
                return self._execute_create_alert(email, classification, start_time)
            elif action_type == ActionType.LOG_REVIEW:
                return self._execute_log_review(email, classification, start_time)
            else:
                return ActionResult(
                    action_type=action_type,
                    success=False,
                    message=f"Unknown action type: {action_type}",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Action execution failed for {action_type}: {e}")
            return ActionResult(
                action_type=action_type,
                success=False,
                message=f"Action execution error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def _execute_generate_response(self, email: EmailMessage, 
                                 classification: Dict[str, Any],
                                 email_client: Optional[EmailClient],
                                 start_time: float) -> ActionResult:
        """Execute response generation and sending."""
        try:
            # Determine appropriate email type based on classification
            category = classification.get("category", "OTHER")
            
            if category == "CUSTOMER":
                email_type = EmailType.CUSTOMER_SERVICE_RESPONSE
            elif category == "SUPPLY_ORDER":
                email_type = EmailType.SUPPLIER_ORDER
            else:
                email_type = EmailType.GENERAL_RESPONSE
            
            # Generate response
            context = f"Original email from {email.sender_name} ({email.sender_email}): Subject: '{email.subject}'. Body: {email.body[:500]}..."
            
            request = EmailGenerationRequest(
                email_type=email_type,
                context=context,
                recipient_name=email.sender_name,
                sender_name="Brewery Operations Team"
            )
            
            generation_result = self.generator.generate_email(request)
            
            if not generation_result.get("success", False):
                return ActionResult(
                    action_type=ActionType.GENERATE_RESPONSE,
                    success=False,
                    message=f"Email generation failed: {generation_result.get('error', 'Unknown error')}",
                    execution_time=time.time() - start_time
                )
            
            # Send email if auto-sending is enabled and email client is available
            email_sent = None
            send_success = False
            
            if self.auto_send_responses and email_client:
                try:
                    subject = generation_result.get("subject", "Re: " + email.subject)
                    body = generation_result.get("body", "")
                    
                    send_success = email_client.send_email(
                        to_email=email.sender_email,
                        subject=subject,
                        body=body
                    )
                    
                    email_sent = {
                        "to": email.sender_email,
                        "subject": subject,
                        "success": send_success,
                        "message": "Email sent successfully" if send_success else "Email sending failed"
                    }
                    
                    logger.info(f"Email response {'sent successfully' if send_success else 'failed to send'} to {email.sender_email}")
                    
                except Exception as e:
                    logger.error(f"Error sending email response: {e}")
                    send_success = False
                    email_sent = {
                        "to": email.sender_email,
                        "subject": generation_result.get("subject", ""),
                        "success": False,
                        "message": f"Send error: {str(e)}"
                    }
            
            return ActionResult(
                action_type=ActionType.GENERATE_RESPONSE,
                success=True,
                message="Email response generated" + (" and sent" if send_success else " (not sent)"),
                details={
                    "generated_email": generation_result,
                    "email_sent": email_sent,
                    "send_success": send_success
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return ActionResult(
                action_type=ActionType.GENERATE_RESPONSE,
                success=False,
                message=f"Response generation error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def _execute_create_alert(self, email: EmailMessage, 
                            classification: Dict[str, Any],
                            start_time: float) -> ActionResult:
        """Execute alert creation for urgent issues."""
        try:
            # In a real implementation, this would integrate with alerting systems
            # like PagerDuty, Slack, etc. For demo purposes, we log the alert
            
            alert_details = {
                "alert_type": "urgent_brewery_issue",
                "email_id": email.message_id,
                "sender": f"{email.sender_name} ({email.sender_email})",
                "subject": email.subject,
                "timestamp": email.timestamp.isoformat() if email.timestamp else None,
                "classification": classification,
                "priority": "high"
            }
            
            logger.critical(f"URGENT ALERT CREATED: {alert_details}")
            
            return ActionResult(
                action_type=ActionType.CREATE_ALERT,
                success=True,
                message=f"Urgent alert created for email from {email.sender_email}",
                details={"alert": alert_details},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Alert creation failed: {e}")
            return ActionResult(
                action_type=ActionType.CREATE_ALERT,
                success=False,
                message=f"Alert creation error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def _execute_log_review(self, email: EmailMessage,
                          classification: Dict[str, Any], 
                          start_time: float) -> ActionResult:
        """Execute logging for manual review."""
        try:
            review_item = {
                "email_id": email.message_id,
                "sender": f"{email.sender_name} ({email.sender_email})",
                "subject": email.subject,
                "classification": classification,
                "timestamp": email.timestamp.isoformat() if email.timestamp else None,
                "review_required": True
            }
            
            logger.info(f"EMAIL QUEUED FOR REVIEW: {review_item}")
            
            return ActionResult(
                action_type=ActionType.LOG_REVIEW,
                success=True,
                message=f"Email from {email.sender_email} queued for manual review",
                details={"review_item": review_item},
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Review logging failed: {e}")
            return ActionResult(
                action_type=ActionType.LOG_REVIEW,
                success=False,
                message=f"Review logging error: {str(e)}",
                execution_time=time.time() - start_time
            )

    def _determine_next_steps(self, category: str, actions: List[ActionResult]) -> List[str]:
        """Determine next steps based on category and action results.
        
        Args:
            category: Email classification category
            actions: List of executed actions
            
        Returns:
            List of next step descriptions
        """
        next_steps = []
        
        # Check for failed actions
        failed_actions = [a for a in actions if not a.success]
        if failed_actions:
            next_steps.append(f"Retry failed actions: {[a.action_type.value for a in failed_actions]}")
        
        # Category-specific next steps
        if category == "URGENT_ISSUE":
            next_steps.append("Monitor alert status and escalate if no response within 30 minutes")
        elif category == "CUSTOMER":
            next_steps.append("Follow up with customer if no reply within 24 hours")
        elif category == "SUPPLY_ORDER":
            next_steps.append("Track supplier response and update procurement team")
        elif category in ["SCHEDULE", "MAINTENANCE", "OTHER"]:
            next_steps.append("Human review required within 4 business hours")
        
        # Email sending follow-up
        for action in actions:
            if (action.action_type == ActionType.GENERATE_RESPONSE and 
                action.details and 
                not action.details.get("send_success", False)):
                next_steps.append("Manually send generated response email")
                break
        
        return next_steps if next_steps else ["No additional steps required"]