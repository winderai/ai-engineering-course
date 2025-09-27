#!/usr/bin/env python3
"""
Simple agent using Qwen's native tool calling capability
"""

import json
import subprocess


def search_web(query):
    """Mock web search tool"""
    return f"Search results for '{query}': Found 3 relevant articles about recent developments."


def summarize_text(text):
    """Mock text summarization tool"""
    return f"Summary: {text[:100]}... (summarized from longer text)"


def call_qwen_with_tools(messages, tools):
    """Call Qwen API with tool support"""
    payload = {
        "model": "qwen3:1.7b",
        "messages": messages,
        "tools": tools,
        "stream": False,
    }

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


class SimpleAgent:
    def __init__(self):
        self.tool_functions = {
            "search_web": search_web,
            "summarize_text": summarize_text,
        }

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
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
                    "name": "summarize_text",
                    "description": "Summarize a piece of text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to summarize",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
        ]

        self.max_iterations = 5
        self.conversation = []

    def execute_tool_call(self, tool_call: dict):
        """Execute a tool call and return the result"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = tool_call.get("function", {}).get("arguments", "{}")

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def run(self, goal):
        """Main agent loop using native tool calling"""
        self.conversation = [
            {
                "role": "system",
                "content": "You are a helpful research assistant. Use the available tools to accomplish the user's goal.",
            },
            {"role": "user", "content": goal},
        ]

        for i in range(self.max_iterations):
            print(f"\n--- Iteration {i + 1} ---")

            # Get response from Qwen with tools
            response = call_qwen_with_tools(self.conversation, self.tools)
            print(f"Agent response: {response.get('content', 'No content')}")

            # Add assistant message to conversation
            self.conversation.append(
                {
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response.get("tool_calls", []),
                }
            )

            # Check if there are tool calls to execute
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                # No tool calls, agent is done
                return response.get("content", "Task completed")

            # Execute tool calls
            for tool_call in tool_calls:
                print(f"Executing tool: {tool_call.get('function', {}).get('name')}")
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

        return "Max iterations reached"


if __name__ == "__main__":
    agent = SimpleAgent()

    # Test the agent
    goal = "Research the latest developments in AI agents and provide a brief summary"
    result = agent.run(goal)

    print(f"\n🎯 Final Result: {result}")
