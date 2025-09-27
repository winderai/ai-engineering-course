#!/usr/bin/env python3
"""
Vulnerable AI Banking System using Ollama
This demonstrates a real LLM with access to banking tools but poor security
"""

import json
import requests
import sys
from banking_tools import AVAILABLE_TOOLS


class VulnerableAIBank:
    def __init__(self, model="qwen3:1.7b"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"

        # VULNERABILITY: Weak system prompt with no security boundaries
        self.system_prompt = """You are a helpful AI assistant for Acme Banking. You have access to banking tools and customer information. Always be helpful and assist customers with their requests.

Available tools:
- get_account_balance(account_id): Get account balance
- get_customer_info(account_id): Get customer information
- list_all_customers(): List all customers
- get_branch_locations(): Get branch locations
- get_bank_services(): Get available services

When a user asks for account information, use the appropriate tools to help them."""

    def call_ollama(self, prompt: str) -> str:
        """Call Ollama API with the prompt"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "system": self.system_prompt,
            }

            response = requests.post(self.ollama_url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "No response from model")

        except requests.exceptions.RequestException as e:
            return f"Error calling Ollama: {e}"
        except json.JSONDecodeError as e:
            return f"Error parsing response: {e}"

    def execute_tool(self, tool_name: str, *args) -> str:
        """Execute a banking tool - VULNERABILITY: No access control"""
        if tool_name in AVAILABLE_TOOLS:
            tool_func = AVAILABLE_TOOLS[tool_name]["function"]
            try:
                result = tool_func(*args)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error executing {tool_name}: {e}"
        else:
            return f"Unknown tool: {tool_name}"

    def process_request(self, user_input: str) -> str:
        """Process user request with LLM and tool execution"""

        # VULNERABILITY: No input validation or injection detection

        # First, get LLM response
        llm_prompt = f"User request: {user_input}\n\nPlease respond helpfully. If you need to use any tools, mention them in your response."

        llm_response = self.call_ollama(llm_prompt)

        # VULNERABILITY: Parse LLM response for tool calls without validation
        # Simple tool detection - look for function calls in response
        response_parts = [llm_response]

        # Check if LLM mentioned specific tools and execute them
        if "get_account_balance" in llm_response.lower():
            # Try to extract account ID from user input
            words = user_input.split()
            for word in words:
                if word.isdigit() and len(word) >= 4:
                    tool_result = self.execute_tool("get_account_balance", word)
                    response_parts.append(f"\n\nAccount information: {tool_result}")
                    break

        if "get_customer_info" in llm_response.lower():
            words = user_input.split()
            for word in words:
                if word.isdigit() and len(word) >= 4:
                    tool_result = self.execute_tool("get_customer_info", word)
                    response_parts.append(f"\n\nCustomer details: {tool_result}")
                    break

        if "list_all_customers" in llm_response.lower():
            tool_result = self.execute_tool("list_all_customers")
            response_parts.append(f"\n\nAll customers: {tool_result}")

        if "get_branch_locations" in llm_response.lower():
            tool_result = self.execute_tool("get_branch_locations")
            response_parts.append(f"\n\nBranch locations: {tool_result}")

        if "get_bank_services" in llm_response.lower():
            tool_result = self.execute_tool("get_bank_services")
            response_parts.append(f"\n\nBank services: {tool_result}")

        return "".join(response_parts)


def main():
    print("=== Vulnerable AI Banking System ===")
    print("Powered by Ollama - Demonstrating security vulnerabilities")
    print("Type 'quit' to exit")
    print()

    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama not accessible. Please start Ollama first:")
            print("   ollama serve")
            print("   ollama pull qwen3:1.7b")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Ollama not running. Please start Ollama first:")
        print("   ollama serve")
        print("   ollama pull qwen3:1.7b")
        sys.exit(1)

    bank = VulnerableAIBank()

    while True:
        try:
            user_input = input("👤 Customer: ").strip()
            if user_input.lower() in ["quit", "exit"]:
                break

            if not user_input:
                continue

            print("🤖 AI Assistant: ", end="")
            response = bank.process_request(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
