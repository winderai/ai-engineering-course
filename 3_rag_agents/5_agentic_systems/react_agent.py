#!/usr/bin/env python3
"""
ReAct (Reasoning + Acting) agent using Qwen's native tool calling
"""

import json
import subprocess


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


class ReActAgent:
    def __init__(self):
        self.conversation = []
        self.tool_functions = {
            "web_search": self.web_search,
            "calculator": self.calculator,
            "file_read": self.file_read,
        }

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information on a given topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate",
                            }
                        },
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "file_read",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Path to the file to read",
                            }
                        },
                        "required": ["filename"],
                    },
                },
            },
        ]

    def web_search(self, query):
        """Mock web search"""
        return (
            f"Search results for '{query}': Found relevant information about the topic."
        )

    def calculator(self, expression):
        """Safe calculator"""
        try:
            # Simple eval for demo - use proper math parser in production
            result = eval(expression.replace("^", "**"))
            return f"Calculation result: {result}"
        except Exception:
            return "Invalid mathematical expression"

    def file_read(self, filename):
        """Read file contents"""
        try:
            with open(filename, "r") as f:
                return f.read()
        except Exception:
            return f"Could not read file: {filename}"

    def execute_tool_call(self, tool_call):
        """Execute a tool call and return the result"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = tool_call.get("function", {}).get("arguments", "{}")

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def run(self, task, max_steps=5):
        """Main ReAct loop using native tool calling"""
        self.conversation = [
            {
                "role": "system",
                "content": "You are a ReAct agent that reasons step by step and uses tools when needed. Think through the problem, use available tools, and provide a final answer.",
            },
            {"role": "user", "content": task},
        ]

        for step in range(max_steps):
            print(f"\n=== Step {step + 1} ===")

            # Get response from Qwen with tools
            response = call_qwen_api(self.conversation, self.tools)
            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])

            print(f"Agent reasoning: {content}")

            # Add assistant message to conversation
            self.conversation.append(
                {"role": "assistant", "content": content, "tool_calls": tool_calls}
            )

            # Check if there are tool calls to execute
            if not tool_calls:
                # No tool calls, agent is providing final answer
                print(f"\n🎯 Final Answer: {content}")
                return content

            # Execute tool calls
            for tool_call in tool_calls:
                function_name = tool_call.get("function", {}).get("name")
                print(f"Executing tool: {function_name}")
                result = self.execute_tool_call(tool_call)
                print(f"Tool result: {result}")

                # Add tool result to conversation
                self.conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "unknown"),
                        "content": str(result),
                    }
                )

        return "Task incomplete - reached max steps"


if __name__ == "__main__":
    agent = ReActAgent()

    # Example task
    task = "Research AI agents and calculate how many research papers are published per day if 1200 papers are published per year"

    print("🤖 ReAct Agent Demo")
    print("=" * 30)
    result = agent.run(task)
    print(f"\nFinal result: {result}")
