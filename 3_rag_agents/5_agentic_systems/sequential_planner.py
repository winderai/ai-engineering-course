#!/usr/bin/env python3
"""
Sequential Planner - Plans and executes tasks in order
"""

import json
import re
import subprocess


def call_qwen_api(messages, tools=None):
    """Call Qwen via API with tool support"""
    payload = {
        "model": "qwen3:1.7b",
        "messages": messages,
        "stream": False,
        "think": False,
    }
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


class SequentialPlanner:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_plan",
                    "description": "Create a sequential plan for a complex task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "The main task to plan for",
                            }
                        },
                        "required": ["task"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_step",
                    "description": "Execute a single step in the plan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "step": {
                                "type": "string",
                                "description": "The step to execute",
                            },
                            "context": {
                                "type": "string",
                                "description": "Context from previous steps",
                            },
                        },
                        "required": ["step"],
                    },
                },
            },
        ]

        self.tool_functions = {
            "create_plan": self.create_plan,
            "execute_step": self.execute_step,
        }

    def create_plan(self, task):
        """Create a sequential plan using LLM"""
        messages = [
            {
                "role": "system",
                "content": "You are a sequential planner. Break down complex tasks into 5-7 sequential steps. Return only a JSON array of step strings.",
            },
            {"role": "user", "content": f"Create a sequential plan for: {task}"},
        ]

        response = call_qwen_api(messages)
        content = response.get("content", "")

        # Try to parse JSON from response
        try:
            # Look for JSON array in the response
            json_match = re.search(r"\[(.*?)\]", content, re.DOTALL)
            if json_match:
                plan_text = "[" + json_match.group(1) + "]"
                plan = json.loads(plan_text)
                return plan
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: extract steps from text
        lines = content.split("\n")
        steps = []
        for line in lines:
            line = line.strip()
            if line and (
                line[0].isdigit() or line.startswith("-") or line.startswith("•")
            ):
                # Remove numbering/bullets
                step = re.sub(r"^[\d\-•\.\s]+", "", line).strip()
                if step:
                    steps.append(step)

        # Ensure we have at least some steps
        if not steps:
            steps = [
                "Break down the task into components",
                "Research necessary resources",
                "Plan implementation approach",
                "Execute core functionality",
                "Test and validate results",
                "Document and finalize",
            ]

        return steps[:7]  # Limit to 7 steps

    def execute_step(self, step, context=""):
        """Execute a single step using LLM"""
        messages = [
            {
                "role": "system",
                "content": "You are a task executor. Execute the given step and provide a brief result summary.",
            },
            {
                "role": "user",
                "content": f"Execute this step: {step}\n\nContext from previous steps: {context}",
            },
        ]

        response = call_qwen_api(messages)
        result = response.get("content", f"Completed: {step}")

        return f"Executed: {step}\nResult: {result}"

    def execute_tool_call(self, tool_call):
        """Execute a tool call"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def plan_and_execute(self, task):
        """Main sequential planning workflow"""
        print(f"🎯 Sequential Planning for: {task}")
        print("=" * 50)

        # Step 1: Create plan
        print("\n📋 Step 1: Creating Plan")
        plan = self.create_plan(task)

        print("Generated Plan:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step}")

        # Step 2: Execute steps sequentially
        print(f"\n⚡ Step 2: Executing {len(plan)} Steps")
        results = []
        context = ""

        for i, step in enumerate(plan, 1):
            print(f"\n--- Executing Step {i}/{len(plan)} ---")
            print(f"Step: {step}")

            result = self.execute_step(step, context)
            results.append(result)
            context += f" -> {step}"

            print(
                f"✅ {result.split('Result:')[1].strip() if 'Result:' in result else 'Completed'}"
            )

        return {"plan": plan, "results": results, "status": "completed"}


if __name__ == "__main__":
    planner = SequentialPlanner()

    # Demo tasks
    demo_tasks = [
        "Build a responsive e-commerce website",
        "Perform customer satisfaction analysis",
        "Create a mobile app prototype",
    ]

    for task in demo_tasks[:1]:  # Show first task for demo
        result = planner.plan_and_execute(task)
        print("\n✨ Planning Complete!")
        print(f"Total steps executed: {len(result['results'])}")
        break
