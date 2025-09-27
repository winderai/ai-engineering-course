#!/usr/bin/env python3
"""
Hierarchical Planner - Breaks complex tasks into subtasks and manages dependencies
"""

import json
import re
import subprocess
from typing import Dict, List, Any


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


class Task:
    def __init__(
        self, name: str, subtasks: List[str] = None, dependencies: List[str] = None
    ):
        self.name = name
        self.subtasks = subtasks or []
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None


class HierarchicalPlanner:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.execution_order = []

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "decompose_task",
                    "description": "Break a complex task into smaller subtasks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "main_task": {
                                "type": "string",
                                "description": "The main task to decompose",
                            }
                        },
                        "required": ["main_task"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_subtask",
                    "description": "Execute a specific subtask",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subtask": {
                                "type": "string",
                                "description": "The subtask to execute",
                            },
                            "context": {
                                "type": "string",
                                "description": "Context from completed dependencies",
                            },
                        },
                        "required": ["subtask"],
                    },
                },
            },
        ]

        self.tool_functions = {
            "decompose_task": self.decompose_task,
            "execute_subtask": self.execute_subtask,
        }

    def decompose_task(self, main_task: str) -> Dict[str, Any]:
        """Decompose a main task into hierarchical subtasks using LLM"""
        messages = [
            {
                "role": "system",
                "content": """You are a hierarchical task planner. Break down complex tasks into 3-4 main phases with dependencies.

Return a JSON object with this structure:
{
  "main_task": "the task",
  "subtasks": {
    "phase1_id": {
      "name": "Phase 1 Name",
      "subtasks": ["subtask1", "subtask2", "subtask3"],
      "dependencies": []
    },
    "phase2_id": {
      "name": "Phase 2 Name",
      "subtasks": ["subtask4", "subtask5"],
      "dependencies": ["phase1_id"]
    }
  }
}""",
            },
            {
                "role": "user",
                "content": f"Create a hierarchical breakdown for: {main_task}",
            },
        ]

        response = call_qwen_api(messages)
        content = response.get("content", "")

        # Try to parse JSON from response
        try:
            # Look for JSON object in the response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                decomposition = json.loads(json_match.group(0))
                # Ensure it has the right structure
                if "subtasks" in decomposition:
                    return decomposition
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

        # Fallback: create a generic structure
        return {
            "main_task": main_task,
            "subtasks": {
                "planning": {
                    "name": "Planning Phase",
                    "subtasks": [
                        "requirements_analysis",
                        "architecture_design",
                        "resource_planning",
                    ],
                    "dependencies": [],
                },
                "implementation": {
                    "name": "Implementation Phase",
                    "subtasks": ["core_development", "integration_work", "testing"],
                    "dependencies": ["planning"],
                },
                "finalization": {
                    "name": "Finalization Phase",
                    "subtasks": ["quality_assurance", "documentation", "deployment"],
                    "dependencies": ["implementation"],
                },
            },
        }

    def execute_subtask(self, subtask: str, context: str = "") -> str:
        """Execute a single subtask using LLM"""
        messages = [
            {
                "role": "system",
                "content": "You are a subtask executor. Execute the given subtask and provide a brief result summary.",
            },
            {
                "role": "user",
                "content": f"Execute this subtask: {subtask.replace('_', ' ')}\n\nContext from completed phases: {context}",
            },
        ]

        response = call_qwen_api(messages)
        result = response.get("content", f"Completed {subtask}")

        return f"✅ {subtask.replace('_', ' ').title()}: {result[:100]}..."

    def build_task_hierarchy(self, task_decomposition: Dict):
        """Build the task hierarchy from decomposition"""
        self.tasks = {}

        for task_id, task_info in task_decomposition["subtasks"].items():
            task = Task(
                name=task_info["name"],
                subtasks=task_info["subtasks"],
                dependencies=task_info["dependencies"],
            )
            self.tasks[task_id] = task

        # Calculate execution order based on dependencies
        self.execution_order = self.calculate_execution_order()

    def calculate_execution_order(self) -> List[str]:
        """Calculate the order of task execution based on dependencies"""
        completed = set()
        order = []

        while len(completed) < len(self.tasks):
            for task_id, task in self.tasks.items():
                if task_id in completed:
                    continue

                # Check if all dependencies are completed
                if all(dep in completed for dep in task.dependencies):
                    order.append(task_id)
                    completed.add(task_id)
                    break

        return order

    def execute_tool_call(self, tool_call):
        """Execute a tool call"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def plan_and_execute(self, main_task: str):
        """Main hierarchical planning workflow"""
        print(f"🌳 Hierarchical Planning for: {main_task}")
        print("=" * 60)

        # Step 1: Decompose the main task
        print("\n📋 Step 1: Task Decomposition")
        decomposition = self.decompose_task(main_task)
        self.build_task_hierarchy(decomposition)

        # Display the hierarchy
        print("\nTask Hierarchy:")
        for i, task_id in enumerate(self.execution_order, 1):
            task = self.tasks[task_id]
            deps = (
                f" (depends on: {', '.join(task.dependencies)})"
                if task.dependencies
                else ""
            )
            print(f"  {i}. {task.name}{deps}")
            for j, subtask in enumerate(task.subtasks, 1):
                print(f"     {i}.{j} {subtask.replace('_', ' ').title()}")

        # Step 2: Execute tasks in dependency order
        print("\n⚡ Step 2: Executing Tasks")
        context = ""

        for i, task_id in enumerate(self.execution_order, 1):
            task = self.tasks[task_id]
            print(f"\n--- Phase {i}: {task.name} ---")

            # Execute all subtasks for this phase
            subtask_results = []
            for subtask in task.subtasks:
                print(f"  Executing: {subtask.replace('_', ' ').title()}")
                result = self.execute_subtask(subtask, context)
                subtask_results.append(result)
                print(f"  {result}")

            task.status = "completed"
            task.result = subtask_results
            context += f" -> {task.name} completed"

        print("\n✨ Hierarchical Planning Complete!")
        return {
            "decomposition": decomposition,
            "execution_order": self.execution_order,
            "completed_tasks": len(self.tasks),
        }


if __name__ == "__main__":
    planner = HierarchicalPlanner()

    # Demo tasks
    demo_tasks = [
        "Build and deploy a machine learning model for customer churn prediction",
        "Create a comprehensive mobile application",
        "Develop a microservices architecture",
    ]

    # Run the first demo
    result = planner.plan_and_execute(demo_tasks[0])
    print(f"Total phases completed: {result['completed_tasks']}")
