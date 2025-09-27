#!/usr/bin/env python3
"""
Self-Correcting Agent - Detects and recovers from failures
"""

import json
import re
import subprocess
import time
from typing import Dict, Any


def call_qwen_api(messages, tools=None):
    """Call Qwen via API with tool support"""
    payload = {"model": "qwen3:1.7b", "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools

    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "http://localhost:11434/api/chat",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(payload),
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout:
            response = json.loads(result.stdout)
            return response.get("message", {})
        return {"content": "No response from API"}
    except Exception as e:
        return {"content": f"API Error: {e}"}


class SelfCorrectingAgent:
    def __init__(self):
        self.max_retries = 3
        self.failure_history = []
        self.success_patterns = []

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_task",
                    "description": "Execute a task that might fail",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "The task to execute",
                            },
                            "approach": {
                                "type": "string",
                                "description": "The approach or method to use",
                            },
                        },
                        "required": ["task", "approach"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_failure",
                    "description": "Analyze a failure and suggest corrections",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "description": "The error that occurred",
                            },
                            "context": {
                                "type": "string",
                                "description": "Context of when the error occurred",
                            },
                        },
                        "required": ["error", "context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_correction",
                    "description": "Apply a correction strategy",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "correction": {
                                "type": "string",
                                "description": "The correction to apply",
                            },
                            "original_task": {
                                "type": "string",
                                "description": "The original task that failed",
                            },
                        },
                        "required": ["correction", "original_task"],
                    },
                },
            },
        ]

        self.tool_functions = {
            "execute_task": self.execute_task,
            "analyze_failure": self.analyze_failure,
            "apply_correction": self.apply_correction,
        }

    def execute_task(self, task: str, approach: str) -> Dict[str, Any]:
        """Execute a task with potential for failure"""
        # Simulate different failure scenarios based on approach
        failure_scenarios = {
            "direct": {"success_rate": 0.1, "error": "Connection timeout"},
            "retry_once": {"success_rate": 0.6, "error": "Rate limit exceeded"},
            "with_backoff": {"success_rate": 0.8, "error": "Resource unavailable"},
            "robust": {"success_rate": 0.9, "error": "Temporary failure"},
        }

        scenario = failure_scenarios.get(approach, failure_scenarios["direct"])

        # Simulate execution
        import random

        if random.random() < scenario["success_rate"]:
            return {
                "success": True,
                "result": f"Successfully completed: {task} using {approach}",
                "approach_used": approach,
            }
        else:
            return {
                "success": False,
                "error": scenario["error"],
                "task": task,
                "approach_used": approach,
            }

    def analyze_failure(self, error: str, context: str) -> Dict[str, Any]:
        """Analyze failure and suggest corrections using LLM"""
        messages = [
            {
                "role": "system",
                "content": """You are a failure analysis expert. Analyze errors and suggest correction strategies.

Available correction approaches:
- direct: Basic approach, no special handling
- retry_once: Simple retry mechanism
- with_backoff: Exponential backoff for rate limiting/network issues
- robust: Comprehensive error handling with fallbacks

Respond with JSON:
{
  "recommended_correction": "approach_name",
  "reasoning": "explanation of why this approach is best",
  "error_type": "categorized error type"
}""",
            },
            {
                "role": "user",
                "content": f"Analyze this failure and suggest a correction approach:\n\nError: {error}\nContext: {context}\n\nWhat correction strategy should be used?",
            },
        ]

        response = call_qwen_api(messages)
        content = response.get("content", "")

        # Try to parse JSON from response
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                # Validate the response has required fields
                if "recommended_correction" in analysis:
                    return analysis
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback analysis based on error patterns
        if "timeout" in error.lower() or "connection" in error.lower():
            correction = "with_backoff"
            reasoning = "Network issues detected, use exponential backoff"
        elif "rate limit" in error.lower():
            correction = "retry_once"
            reasoning = "Rate limiting detected, wait and retry"
        elif "unavailable" in error.lower() or "resource" in error.lower():
            correction = "robust"
            reasoning = "Resource issues detected, use robust error handling"
        else:
            correction = "robust"
            reasoning = "General failure, apply comprehensive error handling"

        return {
            "recommended_correction": correction,
            "reasoning": reasoning,
            "error_type": error,
        }

    def apply_correction(self, correction: str, original_task: str) -> str:
        """Apply the suggested correction using LLM"""
        messages = [
            {
                "role": "system",
                "content": "You are a correction implementation expert. Explain how to apply the suggested correction strategy to the task.",
            },
            {
                "role": "user",
                "content": f"Apply correction strategy '{correction}' to this task: {original_task}\n\nExplain what specific changes or adjustments should be made.",
            },
        ]

        response = call_qwen_api(messages)
        result = response.get(
            "content", f"Applied correction '{correction}' to task '{original_task}'"
        )

        return f"Applied correction '{correction}': {result}"

    def execute_tool_call(self, tool_call):
        """Execute a tool call"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def execute_with_self_correction(self, task: str):
        """Execute a task with self-correction capabilities"""
        print(f"🔧 Self-Correcting Execution: {task}")
        print("=" * 50)

        current_approach = "direct"
        attempt = 1

        while attempt <= self.max_retries:
            print(f"\n--- Attempt {attempt} ---")
            print(f"Approach: {current_approach}")

            # Execute the task
            result = self.execute_task(task, current_approach)

            if result["success"]:
                print(f"✅ Success: {result['result']}")
                self.success_patterns.append(current_approach)
                return {
                    "success": True,
                    "result": result["result"],
                    "attempts": attempt,
                    "final_approach": current_approach,
                }
            else:
                print(f"❌ Failure: {result['error']}")
                self.failure_history.append(
                    {
                        "attempt": attempt,
                        "error": result["error"],
                        "approach": current_approach,
                    }
                )

                if attempt < self.max_retries:
                    # Analyze the failure
                    print("🧠 Analyzing failure...")
                    analysis = self.analyze_failure(
                        result["error"], f"attempt {attempt}"
                    )
                    print(f"Analysis: {analysis['reasoning']}")

                    # Apply correction
                    current_approach = analysis["recommended_correction"]
                    print(f"🔄 Correcting approach to: {current_approach}")

                    # Brief pause to simulate correction application
                    time.sleep(0.5)

                attempt += 1

        # All attempts failed
        print(f"\n💥 All {self.max_retries} attempts failed")
        return {
            "success": False,
            "final_error": "Max retries exceeded",
            "attempts": attempt - 1,
            "failure_history": self.failure_history,
        }

    def demonstrate_self_correction(self):
        """Demonstrate self-correction with multiple tasks"""
        demo_tasks = [
            "Download large dataset from API",
            "Process complex data transformation",
            "Upload results to cloud storage",
        ]

        print("🤖 Self-Correcting Agent Demo")
        print("=" * 40)

        for task in demo_tasks:
            result = self.execute_with_self_correction(task)

            if result["success"]:
                print(f"✨ Task completed in {result['attempts']} attempts")
            else:
                print(f"🚫 Task failed after {result['attempts']} attempts")

            print("-" * 30)

        # Show learning summary
        print("\n📊 Learning Summary:")
        print(f"Successful approaches: {set(self.success_patterns)}")
        print(f"Total failures encountered: {len(self.failure_history)}")


if __name__ == "__main__":
    agent = SelfCorrectingAgent()
    agent.demonstrate_self_correction()
