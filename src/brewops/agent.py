import os
import time
import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from brewops.email_client import EmailClient, EmailMessage
from brewops.classifier import EmailClassifier
from brewops.email_generator import EmailGenerator, EmailGenerationRequest, EmailType
from brewops.information import ProductInformationService, OrderQueryService

logger = logging.getLogger(__name__)

# Data Models


@dataclass
class AgentConfig:
    """Configuration for the agent system."""

    model: str = "ollama/qwen3:1.7b"
    timeout: int = 30
    max_retries: int = 3
    auto_send_emails: bool = True
    auto_apply_labels: bool = True
    batch_size: int = 10
    # Auto mode configuration
    auto_mode_enabled: bool = False
    auto_mode_interval: int = 10  # seconds between processing cycles
    auto_mode_batch_size: int = 10  # max emails per batch in auto mode


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


@dataclass
class AgentState:
    """Current state of the agent."""

    is_running: bool = False
    processed_count: int = 0
    error_count: int = 0
    last_activity: Optional[datetime] = None
    current_batch: List[EmailItem] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    # Auto mode state
    auto_mode_running: bool = False
    auto_mode_task: Optional[Any] = None  # asyncio.Task
    auto_cycles_completed: int = 0
    last_auto_cycle: Optional[datetime] = None


# Tool Interface


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


# Tool Manager


class ToolManager:
    """Manages available tools and tool execution."""

    def __init__(self, tools: List[Tool]):
        """Initialize with list of available tools."""
        self.tools = {tool.name: tool for tool in tools}

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool safely with error handling."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        try:
            start_time = time.time()
            result = tool.execute(**kwargs)
            execution_time = time.time() - start_time

            if isinstance(result, dict):
                result["execution_time"] = execution_time
                return result
            else:
                return {
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                }
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }


# Decision Rules

DECISION_RULES = {
    "URGENT_ISSUE": {
        "tools": ["alert_creator", "label_applier"],
        "priority": 1,
        "reasoning": "Safety issues require immediate escalation and tracking",
    },
    "CUSTOMER": {
        "tools": [
            "product_search",
            "response_generator",
            "label_applier",
            "email_sender",
            "email_archiver",
        ],
        "priority": 2,
        "reasoning": "Customer satisfaction requires prompt, personalized responses with accurate product information. Archive after completion.",
    },
    "SUPPLY_ORDER": {
        "tools": [
            "order_query",
            "response_generator",
            "label_applier",
            "email_sender",
            "email_archiver",
        ],
        "priority": 2,
        "reasoning": "Supply chain continuity depends on timely supplier communication with accurate order information. Archive after completion.",
    },
    "SCHEDULE": {
        "tools": ["label_applier", "review_logger"],
        "priority": 3,
        "reasoning": "Schedule changes need human coordination and approval",
    },
    "MAINTENANCE": {
        "tools": ["label_applier", "review_logger"],
        "priority": 3,
        "reasoning": "Technical decisions require expert evaluation",
    },
    "OTHER": {
        "tools": ["label_applier", "review_logger"],
        "priority": 4,
        "reasoning": "Unknown categories default to manual review queue",
    },
}


# Core Agent Class


class EmailProcessingAgent:
    """Reactive email processing agent following classify → decide → act pattern."""

    def __init__(self, tools: List[Tool], config: AgentConfig = AgentConfig()):
        """Initialize agent with available tools and configuration.

        Args:
            tools: List of Tool instances available to the agent
            config: Agent configuration settings
        """
        self.config = config
        self.tool_manager = ToolManager(tools)
        self.state = AgentState()

    def process_emails(
        self, emails: List[EmailItem], email_client: Optional[EmailClient] = None
    ) -> List[ExecutionResult]:
        """Process a batch of emails through the complete workflow.

        Args:
            emails: List of EmailItem objects to process
            email_client: Optional email client for email operations

        Returns:
            List of ExecutionResult objects with processing outcomes
        """
        self.state.is_running = True
        self.state.current_batch = emails
        self.state.last_activity = datetime.now()

        results = []

        for email in emails:
            try:
                # Step 1: Classify
                classification = self.classify_email(email)

                # Step 2: Decide
                action_plan = self.decide_actions(email, classification)

                # Step 3: Act
                execution_result = self.execute_plan(action_plan, email, email_client)
                results.append(execution_result)

                # Update state
                self.state.processed_count += 1
                if not execution_result.success:
                    self.state.error_count += 1

            except Exception as e:
                logger.error(f"Error processing email {email.message_id}: {e}")
                self.state.error_count += 1

                error_result = ExecutionResult(
                    plan_id=f"error_{email.message_id}",
                    email_id=email.message_id,
                    tool_results={},
                    success=False,
                    total_time=0.0,
                    errors=[str(e)],
                )
                results.append(error_result)

        self.state.is_running = False
        self.state.current_batch = []

        return results

    def classify_email(self, email: EmailItem) -> ClassificationResult:
        """Classify a single email (Step 1: Classify).

        Args:
            email: EmailItem to classify

        Returns:
            ClassificationResult with category and metadata
        """
        start_time = time.time()

        try:
            # Use EmailClassifier from existing codebase
            email_message = EmailMessage(
                sender_name=email.sender_name,
                sender_email=email.sender_email,
                subject=email.subject,
                body=email.body,
                message_id=email.message_id,
                timestamp=email.timestamp,
                imap_uid=email.imap_uid,
            )

            model = self.config.model
            timeout = self.config.timeout
            classifier = EmailClassifier(model=model, timeout=timeout)

            result = classifier.classify_email(email_message)
            processing_time = time.time() - start_time

            return ClassificationResult(
                category=result.get("category", "OTHER"),
                confidence=result.get("confidence", 0.0),
                explanation=result.get("explanation", ""),
                processing_time=processing_time,
                success=result.get("success", False),
                error=result.get("error"),
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error classifying email {email.message_id}: {e}")
            return ClassificationResult(
                category="OTHER",
                confidence=0.0,
                explanation="Classification failed",
                processing_time=processing_time,
                success=False,
                error=str(e),
            )

    def decide_actions(
        self, email: EmailItem, classification: ClassificationResult
    ) -> ActionPlan:
        """Determine actions to take based on classification (Step 2: Decide).

        Args:
            email: Original email item
            classification: Classification result from step 1

        Returns:
            ActionPlan with tools to execute and reasoning
        """
        category = classification.category.upper()

        # Get decision rule for category
        rule = DECISION_RULES.get(category, DECISION_RULES["OTHER"])

        # Filter tools based on availability
        available_tools = [
            tool for tool in rule["tools"] if self.tool_manager.get_tool(tool)
        ]

        return ActionPlan(
            email_id=email.message_id,
            classification=classification,
            actions=available_tools,
            priority=rule["priority"],
            reasoning=rule["reasoning"],
        )

    def execute_plan(
        self,
        plan: ActionPlan,
        email: EmailItem,
        email_client: Optional[EmailClient] = None,
    ) -> ExecutionResult:
        """Execute the action plan using available tools (Step 3: Act).

        Args:
            plan: ActionPlan from decision step
            email: Original email item
            email_client: Optional email client for email operations

        Returns:
            ExecutionResult with tool execution outcomes
        """
        start_time = time.time()
        tool_results = {}
        errors = []
        overall_success = True

        # Store results for passing between tools
        generated_response = None
        search_context = None

        # Execute tools in sequence with dependency management
        email_sent_successfully = False

        for tool_name in plan.actions:
            try:
                # Skip archiver if email sending failed (for customer/supplier emails)
                if (
                    tool_name == "email_archiver"
                    and "email_sender" in plan.actions
                    and not email_sent_successfully
                ):
                    logger.info(
                        f"Skipping {tool_name} for email {email.message_id} - email sending failed or not attempted"
                    )
                    tool_results[tool_name] = {
                        "success": False,
                        "error": "Skipped because email sending failed",
                        "skipped": True,
                    }
                    continue

                logger.info(
                    f"Executing {tool_name} for email {email.message_id} ({email.subject})"
                )

                # Prepare tool parameters based on tool type
                kwargs = self._prepare_tool_params(
                    tool_name,
                    email,
                    plan,
                    email_client,
                    generated_response,
                    search_context,
                )

                # Debug: Check if email_client is being passed to response_generator
                if tool_name == "response_generator":
                    logger.info(
                        f"response_generator kwargs contains email_client: {'email_client' in kwargs}"
                    )
                    if "email_client" in kwargs:
                        logger.info(
                            f"email_client type: {type(kwargs['email_client'])}"
                        )

                result = self.tool_manager.execute_tool(tool_name, **kwargs)

                tool_results[tool_name] = result

                # Store information search results for response generator
                if tool_name in ["product_search", "order_query"] and result.get(
                    "success"
                ):
                    search_context = result.get("result")
                    logger.info(
                        f"Information search completed for email {email.message_id}: {tool_name}"
                    )

                # Store generated response for email_sender tool
                if tool_name == "response_generator" and result.get("success"):
                    generated_response = result.get("result")
                    logger.info(f"Generated response for email {email.message_id}")

                # Track email sending success for archiver dependency
                if tool_name == "email_sender" and result.get("success"):
                    email_sent_successfully = True
                    logger.info(f"Reply sent successfully for email {email.message_id}")
                elif tool_name == "email_sender" and not result.get("success"):
                    logger.error(
                        f"Failed to send reply for email {email.message_id}: {result.get('error')}"
                    )

                # Log other successful operations
                if result.get("success"):
                    if tool_name == "label_applier":
                        logger.info(
                            f"Label applied to original email {email.message_id}"
                        )
                    elif tool_name == "email_archiver":
                        logger.info(
                            f"Original email {email.message_id} archived successfully"
                        )

                if not result.get("success", False) and not result.get(
                    "skipped", False
                ):
                    errors.append(
                        f"{tool_name}: {result.get('error', 'Unknown error')}"
                    )
                    # Continue execution for other tools

            except Exception as e:
                error_msg = f"Failed to execute {tool_name} for email {email.message_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                tool_results[tool_name] = {"success": False, "error": str(e)}

        total_time = time.time() - start_time
        overall_success = len(errors) == 0

        return ExecutionResult(
            plan_id=f"plan_{plan.email_id}_{int(start_time)}",
            email_id=plan.email_id,
            tool_results=tool_results,
            success=overall_success,
            total_time=total_time,
            errors=errors,
        )

    def _prepare_tool_params(
        self,
        tool_name: str,
        email: EmailItem,
        plan: ActionPlan,
        email_client: Optional[EmailClient] = None,
        generated_response: Optional[Dict[str, Any]] = None,
        search_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prepare parameters for tool execution based on tool type."""
        base_params = {"email": email, "classification": plan.classification}

        # Add email client for tools that need thread context
        if (
            tool_name
            in [
                "label_applier",
                "email_sender",
                "email_archiver",
                "response_generator",
                "product_search",
                "order_query",
            ]
            and email_client
        ):
            base_params["email_client"] = email_client

        # Tool-specific parameter preparation
        if tool_name == "label_applier":
            base_params["label_name"] = f"Agent/{plan.classification.category}"
        elif tool_name == "response_generator":
            base_params["email_type"] = self._map_category_to_email_type(
                plan.classification.category
            )
            # Add search context if available from information tools
            if search_context:
                base_params["search_context"] = search_context
        elif tool_name == "product_search":
            # Extract search query from email content
            query = f"{email.subject} {email.body[:200]}"
            base_params["query"] = query
            base_params["max_results"] = 5
        elif tool_name == "order_query":
            # Create question from email content
            question = (
                f"Based on this email about '{email.subject}': {email.body[:200]}"
            )
            base_params["question"] = question
        elif tool_name == "email_sender":
            # Email sender needs the original email and the generated response
            base_params["original_email"] = email  # This is the user's original email
            if generated_response and generated_response.get("success"):
                base_params["reply_body"] = generated_response.get("body", "")
            else:
                base_params["reply_body"] = (
                    "Thank you for contacting us. We will review your message and respond shortly."
                )
        elif tool_name == "email_archiver":
            # Archive tool should work on the original user email, not any reply
            base_params["email"] = email  # Ensure we're archiving the original email
        elif tool_name == "alert_creator":
            base_params["alert_type"] = "urgent" if plan.priority == 1 else "normal"
        elif tool_name == "review_logger":
            base_params["priority"] = self._priority_to_string(plan.priority)

        return base_params

    def _map_category_to_email_type(self, category: str) -> str:
        """Map classification category to email generation type."""
        mapping = {
            "CUSTOMER": "customer_service_response",
            "SUPPLY_ORDER": "supplier_order",
            "URGENT_ISSUE": "quality_control_alert",
            "MAINTENANCE": "maintenance_schedule",
            "SCHEDULE": "general_response",
            "OTHER": "general_response",
        }
        return mapping.get(category.upper(), "general_response")

    def _priority_to_string(self, priority: int) -> str:
        """Convert priority number to string."""
        mapping = {1: "urgent", 2: "high", 3: "normal", 4: "low"}
        return mapping.get(priority, "normal")

    # Auto Mode Methods

    async def start_auto_mode(
        self, email_credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Start auto mode background processing."""
        if self.state.auto_mode_running:
            return {"success": False, "error": "Auto mode is already running"}

        try:
            # Create background task for auto processing
            self.state.auto_mode_task = asyncio.create_task(
                self._auto_processing_loop(email_credentials)
            )
            self.state.auto_mode_running = True
            logger.info("Auto mode started")

            return {
                "success": True,
                "message": "Auto mode started successfully",
                "interval": self.config.auto_mode_interval,
            }
        except Exception as e:
            logger.error(f"Failed to start auto mode: {e}")
            return {"success": False, "error": str(e)}

    async def stop_auto_mode(self) -> Dict[str, Any]:
        """Stop auto mode background processing."""
        if not self.state.auto_mode_running:
            return {"success": False, "error": "Auto mode is not running"}

        try:
            if self.state.auto_mode_task:
                self.state.auto_mode_task.cancel()
                try:
                    await self.state.auto_mode_task
                except asyncio.CancelledError:
                    pass
                self.state.auto_mode_task = None

            self.state.auto_mode_running = False
            logger.info("Auto mode stopped")

            return {
                "success": True,
                "message": "Auto mode stopped successfully",
                "cycles_completed": self.state.auto_cycles_completed,
            }
        except Exception as e:
            logger.error(f"Failed to stop auto mode: {e}")
            return {"success": False, "error": str(e)}

    def get_auto_mode_status(self) -> Dict[str, Any]:
        """Get current auto mode status."""
        return {
            "running": self.state.auto_mode_running,
            "cycles_completed": self.state.auto_cycles_completed,
            "last_cycle": self.state.last_auto_cycle.isoformat()
            if self.state.last_auto_cycle
            else None,
            "interval": self.config.auto_mode_interval,
            "batch_size": self.config.auto_mode_batch_size,
            "next_cycle_in": self._get_next_cycle_time()
            if self.state.auto_mode_running
            else None,
        }

    def _get_next_cycle_time(self) -> Optional[int]:
        """Calculate seconds until next auto cycle."""
        if not self.state.last_auto_cycle:
            return 0

        from datetime import timedelta

        next_cycle = self.state.last_auto_cycle + timedelta(
            seconds=self.config.auto_mode_interval
        )
        remaining = (next_cycle - datetime.now()).total_seconds()
        return max(0, int(remaining))

    async def _auto_processing_loop(self, email_credentials: Dict[str, str]) -> None:
        """Background loop for auto processing emails."""
        logger.info("Auto processing loop started")

        while self.state.auto_mode_running:
            try:
                cycle_start = datetime.now()
                logger.info(
                    f"Starting auto processing cycle {self.state.auto_cycles_completed + 1}"
                )

                # Connect to email server
                server = email_credentials.get(
                    "server", os.getenv("EMAIL_SERVER", "imap.gmail.com")
                )
                username = email_credentials.get(
                    "username", os.getenv("EMAIL_USERNAME")
                )
                password = email_credentials.get(
                    "password", os.getenv("EMAIL_PASSWORD")
                )

                if not username or not password:
                    logger.error("Email credentials not available for auto mode")
                    await asyncio.sleep(self.config.auto_mode_interval)
                    continue

                email_client = EmailClient(server)

                try:
                    if not email_client.connect(username, password):
                        logger.error("Failed to connect to email server in auto mode")
                        await asyncio.sleep(self.config.auto_mode_interval)
                        continue

                    if not email_client.select_inbox():
                        logger.error("Failed to select inbox in auto mode")
                        await asyncio.sleep(self.config.auto_mode_interval)
                        continue

                    # Fetch emails
                    emails = email_client.fetch_all_emails_full()

                    # Convert to EmailItem objects
                    email_items = []
                    for email in emails[
                        : self.config.auto_mode_batch_size
                    ]:  # Limit batch size
                        email_item = EmailItem(
                            message_id=email.message_id,
                            sender_email=email.sender_email,
                            sender_name=email.sender_name,
                            subject=email.subject,
                            body=email.body,
                            timestamp=email.timestamp,
                            imap_uid=email.imap_uid,
                            metadata={
                                "references": email.references
                                if hasattr(email, "references")
                                else ""
                            },
                        )
                        email_items.append(email_item)

                    if email_items:
                        logger.info(
                            f"Processing {len(email_items)} emails in auto mode"
                        )

                        # Process emails
                        results = self.process_emails(
                            email_items, email_client=email_client
                        )

                        successful = sum(1 for r in results if r.success)
                        failed = len(results) - successful

                        logger.info(
                            f"Auto cycle completed: {successful} successful, {failed} failed"
                        )
                    else:
                        logger.info("No new emails to process in auto mode")

                finally:
                    email_client.disconnect()

                # Update cycle tracking
                self.state.auto_cycles_completed += 1
                self.state.last_auto_cycle = cycle_start

                # Wait for next cycle
                await asyncio.sleep(self.config.auto_mode_interval)

            except asyncio.CancelledError:
                logger.info("Auto processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto processing loop: {e}")
                await asyncio.sleep(self.config.auto_mode_interval)

        logger.info("Auto processing loop stopped")


# Built-in Tool Implementations


class EmailClassifierTool(Tool):
    """Tool wrapper for email classification."""

    @property
    def name(self) -> str:
        return "email_classifier"

    @property
    def description(self) -> str:
        return "Classify emails using AI into brewery operation categories"

    def execute(self, email: EmailItem, **kwargs) -> Dict[str, Any]:
        try:
            email_message = EmailMessage(
                sender_name=email.sender_name,
                sender_email=email.sender_email,
                subject=email.subject,
                body=email.body,
                message_id=email.message_id,
            )

            model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
            timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
            classifier = EmailClassifier(model=model, timeout=timeout)

            result = classifier.classify_email(email_message)
            return {
                "success": result.get("success", False),
                "result": result,
                "category": result.get("category", "OTHER"),
                "confidence": result.get("confidence", 0.0),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class LabelApplierTool(Tool):
    """Apply Gmail labels based on email classification."""

    @property
    def name(self) -> str:
        return "label_applier"

    @property
    def description(self) -> str:
        return "Apply Gmail labels based on email classification"

    def execute(
        self,
        email: EmailItem,
        label_name: str,
        email_client: Optional[EmailClient] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            if not email_client:
                return {"success": False, "error": "Email client not provided"}

            # Apply label using email client
            success = email_client.apply_label(email.imap_uid, label_name)

            if success:
                return {
                    "success": True,
                    "result": f"Label '{label_name}' applied to email {email.message_id}",
                    "label_applied": label_name,
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to apply label '{label_name}'",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ResponseGeneratorTool(Tool):
    """Generate AI-powered email responses."""

    @property
    def name(self) -> str:
        return "response_generator"

    @property
    def description(self) -> str:
        return "Generate AI-powered email responses"

    def execute(
        self,
        email: EmailItem,
        email_type: str,
        search_context: Optional[Dict[str, Any]] = None,
        email_client: Optional[EmailClient] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"ResponseGeneratorTool executing for email: {email.subject}")
            logger.info(f"  Email client provided: {email_client is not None}")

            # Get full email thread if email client is available
            full_context = ""
            if email_client:
                # Convert EmailItem to EmailMessage for thread fetching
                references = (
                    email.metadata.get("references", "")
                    if hasattr(email, "metadata")
                    else ""
                )
                logger.info(f"  Email references from metadata: {references}")

                email_msg = EmailMessage(
                    sender_name=email.sender_name,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    body=email.body,
                    message_id=email.message_id,
                    timestamp=email.timestamp,
                    imap_uid=email.imap_uid,
                    references=references,
                )

                logger.info("Fetching email thread...")
                # Fetch the full thread
                thread_emails = email_client.fetch_email_thread(email_msg)
                logger.info(f"Thread fetch returned {len(thread_emails)} emails")

                if len(thread_emails) > 1:
                    full_context = "Email Thread History:\n"
                    for i, thread_email in enumerate(thread_emails, 1):
                        full_context += f"\n--- Email {i} ---\n"
                        full_context += f"From: {thread_email.sender_name} <{thread_email.sender_email}>\n"
                        full_context += f"Subject: {thread_email.subject}\n"
                        full_context += f"Date: {thread_email.timestamp}\n"
                        full_context += (
                            f"Body: {thread_email.body[:500]}...\n"
                            if len(thread_email.body) > 500
                            else f"Body: {thread_email.body}\n"
                        )
                    full_context += "\n---\n\n"

            # Create context from current email (or use thread context)
            if full_context:
                context = (
                    full_context
                    + f"Latest inquiry: {email.subject}\n\nDetails: {email.body[:500]}"
                )
            else:
                context = (
                    f"Customer inquiry: {email.subject}\n\nDetails: {email.body[:500]}"
                )

            # Add search context if available from information tools
            if search_context:
                # Check if it's product search results (list of products)
                if isinstance(search_context, list) and search_context:
                    # Product search results - search_context is directly the list
                    context += "\n\nRelevant Product Information:\n"
                    # Take first 3 results safely
                    for i, result in enumerate(search_context):
                        if i >= 3:  # Only show first 3
                            break
                        # Handle both dict format and ProductSearchResult objects
                        try:
                            if hasattr(result, "name") and hasattr(
                                result, "matched_content"
                            ):  # ProductSearchResult object
                                context += (
                                    f"- {result.name}: {result.matched_content}\n"  # type: ignore
                                )
                            elif isinstance(result, dict):  # Dict format
                                context += f"- {result.get('name', '')}: {result.get('matched_content', '')}\n"
                        except AttributeError:
                            # Fallback if object doesn't have expected attributes
                            context += f"- {str(result)}\n"
                elif isinstance(search_context, dict):
                    if "orders" in search_context:
                        # Order query results
                        context += "\n\nRelevant Order Information:\n"
                        orders = search_context.get("orders", [])
                        context += f"Found {len(orders)} matching orders. "
                        context += search_context.get("summary", "")
                    elif "results" in search_context:
                        # Legacy format - product search with results key
                        context += "\n\nRelevant Product Information:\n"
                        for result in search_context.get("results", [])[
                            :3
                        ]:  # Top 3 results
                            context += f"- {result.get('name', '')}: {result.get('matched_content', '')}\n"

            # Map string email type to EmailType enum
            try:
                email_type_enum = EmailType(email_type)
            except ValueError:
                email_type_enum = EmailType.GENERAL_RESPONSE

            request = EmailGenerationRequest(
                email_type=email_type_enum,
                context=context,
                recipient_name=email.sender_name,
                sender_name="Customer Service Team",
            )

            model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
            timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))
            generator = EmailGenerator(model=model, timeout=timeout)

            result = generator.generate_email(request)

            if result.get("success"):
                return {
                    "success": True,
                    "result": result,
                    "generated_subject": result.get("subject", ""),
                    "generated_body": result.get("body", ""),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Email generation failed"),
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


class EmailSenderTool(Tool):
    """Send email responses via SMTP."""

    @property
    def name(self) -> str:
        return "email_sender"

    @property
    def description(self) -> str:
        return "Send email responses via SMTP (replies to original emails when communicating with customers)"

    def execute(
        self,
        original_email: EmailItem,
        reply_body: str,
        email_client: Optional[EmailClient] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            if not email_client:
                return {"success": False, "error": "Email client not provided"}

            # Get generated response from previous tool results
            generated_response = kwargs.get("generated_response")
            if generated_response and generated_response.get("success"):
                reply_body = generated_response.get("body", reply_body)

            # Convert EmailItem back to EmailMessage for the reply
            original_email_message = EmailMessage(
                sender_name=original_email.sender_name,
                sender_email=original_email.sender_email,
                subject=original_email.subject,
                body=original_email.body,
                message_id=original_email.message_id,
                timestamp=original_email.timestamp,
                imap_uid=original_email.imap_uid,
            )

            # Reply to the original email (subject will be automatically "Re: [original subject]")
            success = email_client.reply_to_email(
                original_email=original_email_message, reply_body=reply_body
            )

            if success:
                return {
                    "success": True,
                    "result": f"Reply sent to {original_email.sender_email}",
                    "reply_sent": True,
                }
            else:
                return {"success": False, "error": "Failed to send reply"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class AlertCreatorTool(Tool):
    """Create urgent alerts for critical issues."""

    @property
    def name(self) -> str:
        return "alert_creator"

    @property
    def description(self) -> str:
        return "Create urgent alerts for critical issues"

    def execute(
        self, email: EmailItem, alert_type: str = "urgent", **kwargs
    ) -> Dict[str, Any]:
        try:
            # In production, this would integrate with PagerDuty, Slack, etc.
            alert_message = f"URGENT ALERT: {email.subject} from {email.sender_email}"

            # Log the alert
            logger.critical(f"BREWERY ALERT [{alert_type.upper()}]: {alert_message}")

            return {
                "success": True,
                "result": f"Alert created: {alert_message}",
                "alert_type": alert_type,
                "alert_message": alert_message,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ReviewLoggerTool(Tool):
    """Queue emails for manual review."""

    @property
    def name(self) -> str:
        return "review_logger"

    @property
    def description(self) -> str:
        return "Queue emails for manual review"

    def execute(
        self, email: EmailItem, priority: str = "normal", **kwargs
    ) -> Dict[str, Any]:
        try:
            # In production, this would integrate with a ticket system or database
            review_entry = {
                "email_id": email.message_id,
                "sender": f"{email.sender_name} <{email.sender_email}>",
                "subject": email.subject,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
                "status": "pending_review",
            }

            # Log for manual review
            logger.info(
                f"REVIEW QUEUE [{priority.upper()}]: {email.subject} from {email.sender_email}"
            )

            return {
                "success": True,
                "result": f"Email queued for {priority} priority review",
                "review_entry": review_entry,
                "queue_priority": priority,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class EmailArchiverTool(Tool):
    """Archive emails after successful processing."""

    @property
    def name(self) -> str:
        return "email_archiver"

    @property
    def description(self) -> str:
        return "Archive emails after successful processing"

    def execute(
        self, email: EmailItem, email_client: Optional[EmailClient] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            if not email_client:
                return {"success": False, "error": "Email client not provided"}

            # Archive the email
            success = email_client.archive_email(email.imap_uid)

            if success:
                return {
                    "success": True,
                    "result": f"Email {email.message_id} archived successfully",
                    "archived": True,
                }
            else:
                return {"success": False, "error": "Failed to archive email"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ProductSearchTool(Tool):
    """Search products using RAG pipeline."""

    def __init__(self, product_service: ProductInformationService):
        self.product_service = product_service

    @property
    def name(self) -> str:
        return "product_search"

    @property
    def description(self) -> str:
        return "Search product information using natural language RAG pipeline"

    def execute(
        self,
        query: str,
        max_results: int = 5,
        email_client: Optional[EmailClient] = None,
        email: Optional[EmailItem] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            # Get thread context to understand what products were previously discussed
            enhanced_query = query
            thread_emails = [email] if email else []

            if email_client and email:
                # Convert EmailItem to EmailMessage for thread fetching
                email_msg = EmailMessage(
                    sender_name=email.sender_name,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    body=email.body,
                    message_id=email.message_id,
                    timestamp=email.timestamp,
                    imap_uid=email.imap_uid,
                    references=email.metadata.get("references", "")
                    if hasattr(email, "metadata")
                    else "",
                )

                # Fetch the full thread
                thread_emails = email_client.fetch_email_thread(email_msg)
                logger.info(
                    f"ProductSearchTool: Using thread context with {len(thread_emails)} emails"
                )

                if len(thread_emails) > 1:
                    # Build enhanced query with thread context
                    thread_context = []
                    for thread_email in thread_emails[:-1]:  # Exclude current email
                        thread_context.append(
                            f"Previous: {thread_email.subject} - {thread_email.body[:100]}"
                        )

                    enhanced_query = f"Thread context: {' | '.join(thread_context)} | Current query: {query}"
                    logger.debug(
                        f"Enhanced product search query: {enhanced_query[:200]}..."
                    )

            results = self.product_service.search_products_rag(
                enhanced_query, max_results
            )
            return {
                "success": True,
                "result": results,
                "query": query,
                "enhanced_query": enhanced_query if enhanced_query != query else None,
                "results_count": len(results),
                "thread_context_used": email_client is not None
                and len(thread_emails) > 1
                if email_client and email
                else False,
            }
        except Exception as e:
            logger.error(f"ProductSearchTool error: {e}")
            return {"success": False, "error": str(e)}


class OrderQueryTool(Tool):
    """Query orders using natural language."""

    def __init__(self, order_service: OrderQueryService):
        self.order_service = order_service

    @property
    def name(self) -> str:
        return "order_query"

    @property
    def description(self) -> str:
        return "Query order information using natural language with LLM-powered SQL generation"

    def execute(
        self,
        question: str,
        email_client: Optional[EmailClient] = None,
        email: Optional[EmailItem] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            # Get thread context to understand what orders were previously discussed
            enhanced_question = question
            thread_emails = [email] if email else []

            if email_client and email:
                # Convert EmailItem to EmailMessage for thread fetching
                email_msg = EmailMessage(
                    sender_name=email.sender_name,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    body=email.body,
                    message_id=email.message_id,
                    timestamp=email.timestamp,
                    imap_uid=email.imap_uid,
                    references=email.metadata.get("references", "")
                    if hasattr(email, "metadata")
                    else "",
                )

                # Fetch the full thread
                thread_emails = email_client.fetch_email_thread(email_msg)
                logger.info(
                    f"OrderQueryTool: Using thread context with {len(thread_emails)} emails"
                )

                if len(thread_emails) > 1:
                    # Build enhanced question with thread context
                    thread_context = []
                    for thread_email in thread_emails[:-1]:  # Exclude current email
                        thread_context.append(
                            f"Previous discussion: {thread_email.subject} - {thread_email.body[:100]}"
                        )

                    enhanced_question = f"Previous conversation context: {' | '.join(thread_context)} | Current question: {question}"
                    logger.debug(
                        f"Enhanced order query question: {enhanced_question[:200]}..."
                    )

            schema_context = self.order_service.get_schema_context()
            sql_query = self.order_service.generate_sql_with_llm(
                enhanced_question, schema_context
            )

            if not sql_query:
                return {
                    "success": False,
                    "error": "Could not generate SQL query from question",
                }

            orders = self.order_service.execute_order_query(sql_query)

            # Generate summary
            summary = f"Found {len(orders)} orders matching your query"
            if orders:
                statuses = [order.status for order in orders]
                status_counts = {}
                for status in statuses:
                    status_counts[status] = status_counts.get(status, 0) + 1
                summary += f". Status breakdown: {status_counts}"

            return {
                "success": True,
                "result": {
                    "orders": [order.dict() for order in orders],
                    "sql_query": sql_query,
                    "summary": summary,
                },
                "question": question,
                "enhanced_question": enhanced_question
                if enhanced_question != question
                else None,
                "orders_count": len(orders),
                "thread_context_used": email_client is not None
                and len(thread_emails) > 1
                if email_client and email
                else False,
            }
        except Exception as e:
            logger.error(f"OrderQueryTool error: {e}")
            return {"success": False, "error": str(e)}


# API Models


class ProcessRequest(BaseModel):
    emails: List[Dict[str, Any]]  # EmailItem data as dicts
    config_override: Optional[Dict[str, Any]] = None
    email_credentials: Optional[Dict[str, str]] = None  # server, username, password


class ProcessResponse(BaseModel):
    results: List[Dict[str, Any]]  # ExecutionResult data
    summary: Dict[str, Any]  # counts, timing, success rate
    agent_state: Dict[str, Any]  # AgentState data


class AgentStatusResponse(BaseModel):
    state: Dict[str, Any]  # AgentState data
    available_tools: List[str]
    recent_activity: List[Dict[str, Any]]
    performance_summary: Dict[str, Any]


class ToolRegistration(BaseModel):
    tool_name: str
    tool_class: str  # Importable class name
    tool_config: Dict[str, Any] = {}


class ToolsResponse(BaseModel):
    tools: Dict[str, Dict[str, str]]  # name -> {description, status}
    total_count: int


class ProcessInboxRequest(BaseModel):
    config_override: Optional[Dict[str, Any]] = None
    email_credentials: Optional[Dict[str, str]] = None  # Override env credentials


class AutoModeRequest(BaseModel):
    email_credentials: Optional[Dict[str, str]] = None  # server, username, password
    config_override: Optional[Dict[str, Any]] = None


class AutoModeResponse(BaseModel):
    success: bool
    message: str
    status: Dict[str, Any]
    error: Optional[str] = None


# Global agent instance
agent_instance: Optional[EmailProcessingAgent] = None


def initialize_agent(
    email_client: Optional[EmailClient] = None,
    product_service: Optional[ProductInformationService] = None,
    order_service: Optional[OrderQueryService] = None,
    config: Optional[AgentConfig] = None,
) -> EmailProcessingAgent:
    """Initialize agent with shared services."""
    global agent_instance

    if config is None:
        config = AgentConfig()

    # Create built-in tools
    tools = [
        EmailClassifierTool(),
        LabelApplierTool(),
        ResponseGeneratorTool(),
        EmailSenderTool(),
        AlertCreatorTool(),
        ReviewLoggerTool(),
        EmailArchiverTool(),
    ]

    # Add information service tools if available
    if product_service:
        tools.append(ProductSearchTool(product_service))

    if order_service:
        tools.append(OrderQueryTool(order_service))

    agent_instance = EmailProcessingAgent(tools=tools, config=config)
    return agent_instance


def get_agent() -> EmailProcessingAgent:
    """Get the global agent instance."""
    global agent_instance
    if agent_instance is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent_instance


# FastAPI Router

agent_router = APIRouter(prefix="/agent", tags=["agent"])


@agent_router.post("/process", response_model=ProcessResponse)
async def process_emails(request: ProcessRequest):
    """Process emails through the agent workflow."""
    try:
        agent = get_agent()

        # Convert dict emails to EmailItem objects
        email_items = []
        for email_data in request.emails:
            metadata = email_data.get("metadata", {})
            # Ensure references is in metadata if provided
            if "references" in email_data and "references" not in metadata:
                metadata["references"] = email_data["references"]

            email_item = EmailItem(
                message_id=email_data.get("message_id", ""),
                sender_email=email_data.get("sender_email", ""),
                sender_name=email_data.get("sender_name", ""),
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                timestamp=datetime.fromisoformat(email_data["timestamp"])
                if email_data.get("timestamp")
                else None,
                imap_uid=email_data.get("imap_uid", ""),
                metadata=metadata,
            )
            email_items.append(email_item)

        # Process emails
        results = agent.process_emails(email_items)

        # Convert results to dicts
        result_dicts = []
        for result in results:
            result_dict = {
                "plan_id": result.plan_id,
                "email_id": result.email_id,
                "tool_results": result.tool_results,
                "success": result.success,
                "total_time": result.total_time,
                "errors": result.errors,
            }
            result_dicts.append(result_dict)

        # Create summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.total_time for r in results)

        summary = {
            "total_emails": len(results),
            "successful": successful,
            "failed": failed,
            "total_time": total_time,
            "average_time": total_time / len(results) if results else 0,
            "success_rate": (successful / len(results)) * 100 if results else 0,
        }

        # Get agent state
        agent_state_dict = {
            "is_running": agent.state.is_running,
            "processed_count": agent.state.processed_count,
            "error_count": agent.state.error_count,
            "last_activity": agent.state.last_activity.isoformat()
            if agent.state.last_activity
            else None,
            "performance_metrics": agent.state.performance_metrics,
            "auto_mode": agent.get_auto_mode_status(),
        }

        return ProcessResponse(
            results=result_dicts, summary=summary, agent_state=agent_state_dict
        )

    except Exception as e:
        logger.error(f"Error processing emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """Get current agent status and performance metrics."""
    try:
        agent = get_agent()

        state_dict = {
            "is_running": agent.state.is_running,
            "processed_count": agent.state.processed_count,
            "error_count": agent.state.error_count,
            "last_activity": agent.state.last_activity.isoformat()
            if agent.state.last_activity
            else None,
            "performance_metrics": agent.state.performance_metrics,
            "auto_mode": agent.get_auto_mode_status(),
        }

        available_tools = agent.tool_manager.list_tools()

        # Mock recent activity - in production this would be from a real activity log
        recent_activity = [
            {
                "timestamp": datetime.now().isoformat(),
                "action": "agent_status_check",
                "details": "Status requested via API",
            }
        ]

        performance_summary = {
            "total_processed": agent.state.processed_count,
            "error_rate": (
                agent.state.error_count / max(agent.state.processed_count, 1)
            )
            * 100,
            "available_tools_count": len(available_tools),
        }

        return AgentStatusResponse(
            state=state_dict,
            available_tools=available_tools,
            recent_activity=recent_activity,
            performance_summary=performance_summary,
        )

    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/tools", response_model=ToolsResponse)
async def list_tools():
    """List all available tools and their descriptions."""
    try:
        agent = get_agent()

        tools_info = {}
        for tool_name in agent.tool_manager.list_tools():
            tool = agent.tool_manager.get_tool(tool_name)
            if tool:
                tools_info[tool_name] = {
                    "description": tool.description,
                    "status": "available",
                }

        return ToolsResponse(tools=tools_info, total_count=len(tools_info))

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/tools/register")
async def register_tool(registration: ToolRegistration):
    """Register a new tool with the agent at runtime."""
    try:
        # This is a placeholder for dynamic tool registration
        # In a full implementation, this would use importlib to load the tool class
        return {
            "success": False,
            "message": "Dynamic tool registration not implemented in this demo",
            "tool_name": registration.tool_name,
        }

    except Exception as e:
        logger.error(f"Error registering tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/process-inbox", response_model=ProcessResponse)
async def process_inbox(request: ProcessInboxRequest):
    """Convenience endpoint that fetches all emails from the configured inbox and processes them."""
    try:
        # Get email configuration
        email_creds = request.email_credentials
        server = (
            email_creds.get("server", os.getenv("EMAIL_SERVER", "imap.gmail.com"))
            if email_creds
            else os.getenv("EMAIL_SERVER", "imap.gmail.com")
        )
        username = (
            email_creds.get("username", os.getenv("EMAIL_USERNAME"))
            if email_creds
            else os.getenv("EMAIL_USERNAME")
        )
        password = (
            email_creds.get("password", os.getenv("EMAIL_PASSWORD"))
            if email_creds
            else os.getenv("EMAIL_PASSWORD")
        )

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

            # Convert EmailMessage objects to EmailItem objects
            email_items = []
            for email in emails:
                email_item = EmailItem(
                    message_id=email.message_id,
                    sender_email=email.sender_email,
                    sender_name=email.sender_name,
                    subject=email.subject,
                    body=email.body,
                    timestamp=email.timestamp,
                    imap_uid=email.imap_uid,
                    metadata={
                        "references": email.references
                        if hasattr(email, "references")
                        else ""
                    },
                )
                email_items.append(email_item)

            # Process through agent
            agent = get_agent()

            results = agent.process_emails(email_items, email_client=client)

            # Convert results to response format
            result_dicts = []
            for result in results:
                result_dict = {
                    "plan_id": result.plan_id,
                    "email_id": result.email_id,
                    "tool_results": result.tool_results,
                    "success": result.success,
                    "total_time": result.total_time,
                    "errors": result.errors,
                }
                result_dicts.append(result_dict)

            # Create summary
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            total_time = sum(r.total_time for r in results)

            summary = {
                "total_emails": len(results),
                "successful": successful,
                "failed": failed,
                "total_time": total_time,
                "average_time": total_time / len(results) if results else 0,
                "success_rate": (successful / len(results)) * 100 if results else 0,
            }

            # Get agent state
            agent_state_dict = {
                "is_running": agent.state.is_running,
                "processed_count": agent.state.processed_count,
                "error_count": agent.state.error_count,
                "last_activity": agent.state.last_activity.isoformat()
                if agent.state.last_activity
                else None,
                "performance_metrics": agent.state.performance_metrics,
                "auto_mode": agent.get_auto_mode_status(),
            }

            return ProcessResponse(
                results=result_dicts, summary=summary, agent_state=agent_state_dict
            )

        finally:
            client.disconnect()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing inbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/auto/start", response_model=AutoModeResponse)
async def start_auto_mode(request: AutoModeRequest):
    """Start auto mode for continuous email processing."""
    try:
        agent = get_agent()

        # Get email credentials
        email_credentials = request.email_credentials or {}
        if not email_credentials.get("username"):
            username = os.getenv("EMAIL_USERNAME")
            if username:
                email_credentials["username"] = username
        if not email_credentials.get("password"):
            password = os.getenv("EMAIL_PASSWORD")
            if password:
                email_credentials["password"] = password
        if not email_credentials.get("server"):
            email_credentials["server"] = os.getenv("EMAIL_SERVER", "imap.gmail.com")

        if not email_credentials.get("username") or not email_credentials.get(
            "password"
        ):
            raise HTTPException(
                status_code=400,
                detail="Email credentials required for auto mode. Provide in request or set EMAIL_USERNAME and EMAIL_PASSWORD environment variables.",
            )

        # Apply config overrides if provided
        if request.config_override:
            for key, value in request.config_override.items():
                if hasattr(agent.config, key):
                    setattr(agent.config, key, value)

        result = await agent.start_auto_mode(email_credentials)

        return AutoModeResponse(
            success=result["success"],
            message=result.get("message", ""),
            status=agent.get_auto_mode_status(),
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting auto mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/auto/stop", response_model=AutoModeResponse)
async def stop_auto_mode():
    """Stop auto mode continuous processing."""
    try:
        agent = get_agent()
        result = await agent.stop_auto_mode()

        return AutoModeResponse(
            success=result["success"],
            message=result.get("message", ""),
            status=agent.get_auto_mode_status(),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Error stopping auto mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.get("/auto/status", response_model=Dict[str, Any])
async def get_auto_mode_status():
    """Get current auto mode status."""
    try:
        agent = get_agent()
        return agent.get_auto_mode_status()

    except Exception as e:
        logger.error(f"Error getting auto mode status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
