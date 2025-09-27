#!/usr/bin/env python3
"""
Multi-Agent System - Coordinated agents working together
"""

import json
import subprocess
import time
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


class Agent:
    def __init__(self, name: str, role: str, capabilities: List[str]):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.message_history = []
        self.current_task = None

    def can_handle(self, task_type: str) -> bool:
        """Check if agent can handle a specific task type"""
        return task_type in self.capabilities

    def execute_task(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Execute a task within the agent's capabilities using LLM"""
        context = context or {}

        messages = [
            {
                "role": "system",
                "content": f"""You are {self.name}, a {self.role} agent with these capabilities: {", ".join(self.capabilities)}.

Execute the given task according to your role and provide a realistic result summary.""",
            },
            {
                "role": "user",
                "content": f"Execute this task: {task}\n\nContext: {context.get('previous_results', 'No previous context')}",
            },
        ]

        response = call_qwen_api(messages)
        result_content = response.get("content", f"Completed {self.role} task: {task}")

        return {
            "success": True,
            "result": f"{self.role.title()} work completed: {result_content[:100]}...",
            "agent": self.name,
            "role": self.role,
        }


class MultiAgentSystem:
    def __init__(self):
        self.agents = {}
        self.message_queue = []
        self.workflow_results = []

        # Initialize specialized agents
        self.setup_agents()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "assign_task",
                    "description": "Assign a task to the most suitable agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "The task to assign",
                            },
                            "task_type": {
                                "type": "string",
                                "description": "Type of task (research, analysis, writing, coordination)",
                            },
                        },
                        "required": ["task", "task_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "coordinate_workflow",
                    "description": "Coordinate workflow between multiple agents",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of workflow steps",
                            }
                        },
                        "required": ["workflow_steps"],
                    },
                },
            },
        ]

        self.tool_functions = {
            "assign_task": self.assign_task,
            "coordinate_workflow": self.coordinate_workflow,
        }

    def setup_agents(self):
        """Initialize the multi-agent team"""
        agents_config = [
            {
                "name": "Alice",
                "role": "researcher",
                "capabilities": ["research", "data_collection", "fact_checking"],
            },
            {
                "name": "Bob",
                "role": "analyst",
                "capabilities": ["analysis", "pattern_recognition", "statistics"],
            },
            {
                "name": "Carol",
                "role": "writer",
                "capabilities": ["writing", "documentation", "summarization"],
            },
            {
                "name": "Dave",
                "role": "coordinator",
                "capabilities": ["coordination", "planning", "quality_assurance"],
            },
        ]

        for config in agents_config:
            agent = Agent(config["name"], config["role"], config["capabilities"])
            self.agents[agent.name] = agent

    def determine_task_type(self, step: str) -> str:
        """Determine task type using LLM"""
        messages = [
            {
                "role": "system",
                "content": """Analyze the task and determine which type of agent should handle it.

Available agent types:
- research: Information gathering, fact-finding, data collection
- analysis: Data analysis, pattern recognition, evaluation
- writing: Documentation, reports, content creation
- coordination: Planning, organizing, quality assurance

Respond with only the agent type name.""",
            },
            {
                "role": "user",
                "content": f"What type of agent should handle this task: {step}",
            },
        ]

        response = call_qwen_api(messages)
        task_type = response.get("content", "coordination").strip().lower()

        # Validate the response is one of our known types
        valid_types = ["research", "analysis", "writing", "coordination"]
        if task_type not in valid_types:
            task_type = "coordination"  # Default fallback

        return task_type

    def find_suitable_agent(self, task_type: str) -> Agent:
        """Find the most suitable agent for a task type"""
        for agent in self.agents.values():
            if agent.can_handle(task_type):
                return agent

        # Fallback to coordinator if no specific match
        return self.agents["Dave"]

    def assign_task(self, task: str, task_type: str) -> Dict[str, Any]:
        """Assign a task to the most suitable agent"""
        agent = self.find_suitable_agent(task_type)
        print(f"  📋 Assigning to {agent.name} ({agent.role}): {task}")

        result = agent.execute_task(task)
        self.workflow_results.append(result)

        return result

    def coordinate_workflow(self, workflow_steps: List[str]) -> Dict[str, Any]:
        """Coordinate a multi-step workflow across agents"""
        print(f"🎯 Coordinating {len(workflow_steps)}-step workflow")

        coordination_results = []
        context = {}

        for i, step in enumerate(workflow_steps, 1):
            print(f"\n--- Step {i}: {step} ---")

            # Determine task type using LLM
            task_type = self.determine_task_type(step)

            result = self.assign_task(step, task_type)
            coordination_results.append(result)

            # Update context for next step
            context[f"step_{i}"] = result

            # Brief pause to simulate agent work
            time.sleep(0.3)

        return {
            "workflow_completed": True,
            "steps_executed": len(workflow_steps),
            "results": coordination_results,
        }

    def execute_tool_call(self, tool_call):
        """Execute a tool call"""
        function_name = tool_call.get("function", {}).get("name")
        arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

        if function_name in self.tool_functions:
            return self.tool_functions[function_name](**arguments)
        else:
            return f"Unknown tool: {function_name}"

    def demonstrate_collaboration(self, project: str):
        """Demonstrate multi-agent collaboration"""
        print("🤝 Multi-Agent Collaboration Demo")
        print(f"Project: {project}")
        print("=" * 50)

        # Show team composition
        print("\n👥 Agent Team:")
        for agent in self.agents.values():
            capabilities = ", ".join(agent.capabilities)
            print(f"  • {agent.name} ({agent.role}): {capabilities}")

        # Define workflow for the project
        if "market research" in project.lower():
            workflow = [
                "Research target market and competitors",
                "Analyze market trends and opportunities",
                "Create comprehensive market analysis report",
                "Coordinate final review and recommendations",
            ]
        elif "product launch" in project.lower():
            workflow = [
                "Research customer needs and preferences",
                "Analyze competitive landscape",
                "Create product launch strategy document",
                "Coordinate launch timeline and milestones",
            ]
        else:
            workflow = [
                f"Research background information for {project}",
                f"Analyze key factors affecting {project}",
                f"Create documentation for {project} findings",
                f"Coordinate final deliverables for {project}",
            ]

        print("\n📋 Workflow Plan:")
        for i, step in enumerate(workflow, 1):
            print(f"  {i}. {step}")

        # Execute the workflow
        print("\n⚡ Execution:")
        result = self.coordinate_workflow(workflow)

        # Summary
        print("\n✨ Collaboration Complete!")
        print(f"Steps completed: {result['steps_executed']}")
        print(f"Agents involved: {len(set(r['agent'] for r in result['results']))}")
        for r in result["results"]:
            print(f"  👥 {r['agent']}: {r['result']}\n")

        return result


if __name__ == "__main__":
    # Create multi-agent system
    mas = MultiAgentSystem()

    # Demonstrate different types of projects
    demo_projects = [
        "Market research for AI-powered productivity tools",
        "Product launch strategy for mobile app",
        "Competitive analysis for SaaS platform",
    ]

    # Run first demo
    result = mas.demonstrate_collaboration(demo_projects[0])

    # Show collaboration metrics
    print("\n📊 Collaboration Metrics:")
    print(f"Total workflow steps: {len(result['results'])}")
    agents_used = set(r["agent"] for r in result["results"])
    print(f"Agents utilized: {', '.join(agents_used)}")
    print(
        f"Success rate: 100% ({sum(1 for r in result['results'] if r['success'])}/{len(result['results'])})"
    )
